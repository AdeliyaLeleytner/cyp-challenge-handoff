"""Conditional E7: generic CheMeleon foundation, two-head binary fine-tuning.

Draft only; no implicit label derivation and no inherited ADME checkpoint.
Uses frozen outer identities/inner folds and saves the best validation checkpoint.
"""
from __future__ import annotations

from pathlib import Path
import gc
import hashlib
import importlib.metadata
import json
import os
import time

import numpy as np
import pandas as pd

TARGETS = ['CYP2D6_is_TDI', 'CYP3A4_is_TDI']
FOUNDATION_SHA256 = 'c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651'
RECIPE = {'initialization': 'generic CheMeleon foundation only', 'targets': TARGETS,
          'aggregation': 'MeanAggregation', 'ffn_hidden': 512, 'ffn_layers': 2, 'ffn_dropout': .1,
          'batch_norm': False, 'max_epochs': 50, 'early_stopping_patience': 8,
          'batch_size': 128, 'optimizer': 'Chemprop native Adam', 'init_lr': 1e-5,
          'max_lr': 1e-4, 'final_lr': 1e-5, 'warmup_epochs': 2,
          'primary_weight': 'inverse finite-label counts within fitting fold, mean-normalized',
          'proposal_revision': 'Two provided binary endpoints only; tentative four-head design withdrawn because 1A2/2C9 labels are not provided', 'checkpoint_monitor': 'val_loss', 'checkpoint_mode': 'min',
          'query_prediction': 'equal mean of five best-checkpoint fold probabilities',
          'full_query_alias': 'query_full is an alias of query_bag; no sixth full-data fit'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    os.replace(temporary, path)


def read_labels(frame):
    missing = [name for name in TARGETS if name not in frame]
    if missing:
        raise ValueError('Two-head GNN requires provided official binary labels; missing columns: ' + str(missing))
    accepted = {'true': 1., 'false': 0., '1': 1., '0': 0., '1.0': 1., '0.0': 0.}
    result = np.full((len(frame), 2), np.nan, dtype=np.float32)
    for j, col in enumerate(TARGETS):
        for i, value in enumerate(frame[col]):
            if pd.isna(value):
                continue
            key = str(value).strip().lower()
            if key not in accepted:
                raise ValueError(f'Invalid binary {col} label at row {i}: {value!r}')
            result[i, j] = accepted[key]
    return result


def model_from_foundation(checkpoint, task_weights):
    import torch
    from chemprop import nn, models
    state = torch.load(checkpoint, map_location='cpu', weights_only=False)
    if set(state) != {'hyper_parameters', 'state_dict'}:
        raise ValueError('Expected generic encoder-only foundation checkpoint')
    mp = nn.BondMessagePassing(**state['hyper_parameters'])
    mp.load_state_dict(state['state_dict'], strict=True)
    criterion = nn.metrics.BCELoss(task_weights=task_weights)
    predictor = nn.BinaryClassificationFFN(input_dim=mp.output_dim, hidden_dim=512,
                                          n_layers=2, n_tasks=2, dropout=.1, criterion=criterion)
    # Default metric is AUROC; val_loss is computed by native masked-logit BCE.
    model = models.MPNN(mp, nn.MeanAggregation(), predictor, batch_norm=False,
                        warmup_epochs=2, init_lr=1e-5, max_lr=1e-4, final_lr=1e-5)
    return model


def make_loader(smiles, labels=None, *, shuffle=False, seed=42):
    import torch
    from chemprop import data, featurizers
    from chemprop.data.collate import collate_batch
    if labels is None:
        labels = np.zeros((len(smiles), 2), dtype=np.float32)
    points = [data.MoleculeDatapoint.from_smi(s, y) for s, y in zip(smiles, labels)]
    dataset = data.MoleculeDataset(points, featurizers.SimpleMoleculeMolGraphFeaturizer())
    dataset.cache = True
    # Native Chemprop2.2.1 build_dataloader can drop a final size-one batch.
    # Explicit DataLoader preserves all rows, with the native molecular collator.
    return torch.utils.data.DataLoader(dataset, batch_size=128, shuffle=shuffle,
                                       num_workers=0, collate_fn=collate_batch, drop_last=False,
                                       generator=torch.Generator().manual_seed(int(seed)))


def predict(model, smiles, device):
    import torch
    model.to(device).eval()
    chunks = []
    with torch.inference_mode():
        for batch in make_loader(smiles):
            bmg, V_d, X_d, *_ = batch
            bmg.to(device)
            V_d = None if V_d is None else V_d.to(device)
            X_d = None if X_d is None else X_d.to(device)
            chunks.append(model(bmg, V_d, X_d).cpu().numpy())
    result = np.concatenate(chunks).astype(np.float32)
    if result.shape != (len(smiles), 2) or not np.isfinite(result).all():
        raise ValueError('GNN predictions lost rows or contain nonfinite values')
    if np.any(result < 0) or np.any(result > 1):
        raise ValueError('Binary predictor must return probabilities')
    return result


def _indices(prepared, cohort, seed):
    folder = prepared / 'cohorts' / cohort
    dev = np.load(folder / 'train_indices.npy')
    query = np.load(folder / ('query_indices.npy' if cohort == 'full' else 'holdout_indices.npy'))
    folds = np.load(prepared / f'folds_native_seed{seed}.npy') if cohort == 'full' else np.load(folder / f'folds_seed{seed}.npy')
    if folds.shape != (len(dev),) or set(folds.tolist()) != set(range(5)):
        raise ValueError('Expected five frozen folds aligned to development indices')
    return dev, query, folds


def run_gnn(prepared_dir, output_dir, checkpoint, cohort, seed, device='cuda', max_folds=5):
    import torch
    from lightning import pytorch as pl
    from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
    prepared, out, checkpoint = Path(prepared_dir).resolve(), Path(output_dir).resolve(), Path(checkpoint).resolve()
    if cohort not in ['own750', 'briford529', 'full'] or int(seed) not in [42, 142]:
        raise ValueError('Use frozen campaign cohorts and seeds42/142')
    if sha(checkpoint) != FOUNDATION_SHA256:
        raise ValueError('E7 is restricted to the frozen generic CheMeleon foundation checkpoint')
    if importlib.metadata.version('chemprop') != '2.2.1':
        raise ValueError('E7 implementation is inspected and pinned to Chemprop2.2.1')
    if str(device).startswith('cuda') and not torch.cuda.is_available():
        raise RuntimeError('Requested CUDA is unavailable; do not silently change compute')
    torch.set_num_threads(4)
    out.mkdir(parents=True, exist_ok=True)
    train, test = pd.read_csv(prepared / 'train.csv'), pd.read_csv(prepared / 'test.csv')
    dev, query, folds = _indices(prepared, cohort, int(seed))
    if len(np.unique(dev)) != len(dev) or len(np.unique(query)) != len(query):
        raise ValueError('Repeated global indices')
    dev_frame = train.iloc[dev].reset_index(drop=True)
    query_frame = (test if cohort == 'full' else train).iloc[query].reset_index(drop=True)
    # Only development-label values enter parsing, loss weights or optimization.
    labels = read_labels(dev_frame)
    for key in ['Molecule_Name', 'parent_key', 'canonical_parent']:
        if key not in dev_frame or key not in query_frame:
            raise ValueError(f'Missing identity audit column {key}')
        if set(dev_frame[key]) & set(query_frame[key]):
            raise ValueError(f'Outer development/query overlap: {key}')
    signature = {'recipe': RECIPE, 'cohort': cohort, 'seed': int(seed), 'device': str(device),
                 'foundation_sha256': sha(checkpoint), 'implementation_sha256': sha(__file__),
                 'train_csv_sha256': sha(prepared / 'train.csv'), 'test_csv_sha256': sha(prepared / 'test.csv'),
                 'dev_indices_sha256': hashlib.sha256(dev.tobytes()).hexdigest(),
                 'query_indices_sha256': hashlib.sha256(query.tobytes()).hexdigest(),
                 'folds_sha256': hashlib.sha256(folds.tobytes()).hexdigest(),
                 'packages': {p: importlib.metadata.version(p) for p in ['torch', 'chemprop', 'lightning', 'numpy', 'rdkit']}}
    complete = out / 'complete.json'
    if complete.exists():
        record = json.loads(complete.read_text())
        if record['signature'] != signature:
            raise ValueError('Completed E7 source/data/recipe signature changed')
        for filename, digest in record['output_sha256'].items():
            if sha(out / filename) != digest:
                raise ValueError(f'Completed E7 output modified: {filename}')
        return record
    dev_frame[['Molecule_Name', 'SMILES']].to_csv(out / 'oof_ids.csv', index=False)
    query_frame[['Molecule_Name', 'SMILES']].to_csv(out / 'query_ids.csv', index=False)
    write_json(out / 'recipe.json', signature)
    oof = np.full((len(dev), 2), np.nan, dtype=np.float32)
    fold_queries, fold_metadata = [], []
    start = time.time()
    if not 1 <= int(max_folds) <= 5:raise ValueError('max_folds must be1..5')
    for fold in range(int(max_folds)):
        folder = out / f'fold{fold}'
        folder.mkdir(exist_ok=True)
        marker = folder / 'complete.json'
        valid = np.flatnonzero(folds == fold)
        fitting = np.flatnonzero(folds != fold)
        # Label-free rows cannot contribute a masked BCE denominator.
        fitting_labeled = fitting[np.isfinite(labels[fitting]).any(axis=1)]
        valid_labeled = valid[np.isfinite(labels[valid]).any(axis=1)]
        if not len(fitting_labeled) or not len(valid_labeled):
            raise ValueError('No observed tasks in training or validation fold')
        identity_overlap = {}
        for key in ['parent_key', 'canonical_parent']:
            overlap = set(dev_frame.iloc[fitting][key]) & set(dev_frame.iloc[valid][key])
            identity_overlap[key] = len(overlap)
            if overlap:
                raise ValueError(f'Frozen inner fold crosses an identity group ({cohort},fold{fold},{key})')
        counts = np.isfinite(labels[fitting_labeled]).sum(axis=0)
        if np.any(counts[:2] == 0):
            raise ValueError('Missing primary task in fitting fold')
        inv = 1. / counts[:2]
        weights = (inv / inv.mean()).tolist()
        if marker.exists():
            metadata = json.loads(marker.read_text())
            if metadata['signature'] != signature:
                raise ValueError('Partial fold from another E7 run')
            for filename, digest in metadata['output_sha256'].items():
                if sha(folder / filename) != digest:
                    raise ValueError('Partial E7 output hash mismatch')
        else:
            pl.seed_everything(int(seed) + fold, workers=True)
            model = model_from_foundation(checkpoint, weights)
            best = ModelCheckpoint(dirpath=folder / 'checkpoint', filename='best', monitor='val_loss',
                                   mode='min', save_top_k=1, save_last=False, save_weights_only=True,
                                   auto_insert_metric_name=False)
            stopping = EarlyStopping(monitor='val_loss', mode='min', patience=8, check_finite=True)
            accelerator = 'gpu' if str(device).startswith('cuda') else 'cpu'
            gpu_index = int(str(device).split(':')[1]) if ':' in str(device) else 0
            trainer = pl.Trainer(accelerator=accelerator, devices=[gpu_index] if accelerator == 'gpu' else 1,
                                 max_epochs=50, logger=False, callbacks=[best, stopping],
                                 enable_checkpointing=True, enable_progress_bar=False, enable_model_summary=False,
                                 num_sanity_val_steps=0, log_every_n_steps=10, precision='32-true')
            train_loader = make_loader(dev_frame.SMILES.iloc[fitting_labeled].tolist(), labels[fitting_labeled],
                                       shuffle=True, seed=int(seed) + fold)
            val_loader = make_loader(dev_frame.SMILES.iloc[valid_labeled].tolist(), labels[valid_labeled])
            trainer.fit(model, train_loader, val_loader)
            if not best.best_model_path or not Path(best.best_model_path).is_file():
                raise RuntimeError('No best validation checkpoint saved')
            saved = torch.load(best.best_model_path, map_location='cpu', weights_only=False)
            if 'optimizer_states' in saved:
                raise ValueError('Expected weights-only checkpoint, got optimizer state')
            # Explicitly reload the selected best epoch, never predict with final-epoch weights.
            model.load_state_dict(saved['state_dict'], strict=True)
            valid_proba = predict(model, dev_frame.SMILES.iloc[valid].tolist(), device)[:, :2]
            query_proba = predict(model, query_frame.SMILES.tolist(), device)[:, :2]
            np.savez_compressed(folder / 'predictions.npz', valid_positions=valid, valid_proba=valid_proba,
                                query_proba=query_proba)
            checkpoint_relative = str(Path(best.best_model_path).relative_to(folder))
            metadata = {'signature': signature, 'fold': fold, 'fit_seed': int(seed) + fold,
                        'fitting_rows': len(fitting_labeled), 'validation_labeled_rows': len(valid_labeled),
                        'validation_all_rows': len(valid), 'finite_task_counts': counts.tolist(), 'task_weights': weights,
                        'identity_overlap': identity_overlap, 'best_epoch': int(saved['epoch']),
                        'best_val_loss': float(best.best_model_score.cpu()), 'best_checkpoint': checkpoint_relative,
                        'best_checkpoint_loaded_for_predictions': True,
                        'output_sha256': {'predictions.npz': sha(folder / 'predictions.npz'),
                                          checkpoint_relative: sha(best.best_model_path)}}
            write_json(marker, metadata)
            del model, trainer, train_loader, val_loader, saved
            gc.collect()
            if accelerator == 'gpu':
                torch.cuda.empty_cache()
        with np.load(folder / 'predictions.npz') as result:
            if not np.array_equal(valid, result['valid_positions']):
                raise ValueError('Saved fold predictions have a different order')
            oof[valid] = result['valid_proba']
            fold_queries.append(result['query_proba'].copy())
        fold_metadata.append(metadata)
        print(json.dumps({'stage': 'gnn_fold_done', 'cohort': cohort, 'seed': seed, 'fold': fold,
                          'elapsed_seconds': time.time() - start, 'best_epoch': metadata['best_epoch']}), flush=True)
    if int(max_folds) < 5:
        report={'status':'pilot_complete','folds_completed':int(max_folds),'seconds':time.time()-start,'signature':signature}
        write_json(out/'pilot.json',report)
        return report
    query_bag = np.mean(np.stack(fold_queries), axis=0)
    if not np.isfinite(oof).all() or not np.isfinite(query_bag).all():
        raise ValueError('Incomplete fivefold prediction coverage')
    np.save(out / 'oof_proba.npy', oof)
    np.save(out / 'query_proba.npy', query_bag)
    np.savez_compressed(out / 'predictions.npz', oof=oof, hard_oof=(oof >= .5).astype(float),
                        query_bag=query_bag, query_full=query_bag,
                        query_full_hard=(query_bag >= .5).astype(float),
                        dev_indices=dev, query_indices=query)
    outputs = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p != complete and not p.name.endswith('.log')}
    record = {'status': 'complete', 'signature': signature, 'folds': fold_metadata,
              'seconds': time.time() - start, 'output_sha256': outputs,
              'prediction_sha256': sha(out / 'predictions.npz'),
              'oof_shape': list(oof.shape), 'query_shape': list(query_bag.shape),
              'query_full_is_fold_bag_alias': True, 'outer_labels_used_for_selection': False}
    write_json(complete, record)
    return record
