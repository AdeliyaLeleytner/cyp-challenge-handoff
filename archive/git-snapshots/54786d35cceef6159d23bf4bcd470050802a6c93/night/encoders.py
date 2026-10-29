"""Offline, pinned optional encoders; execute extraction inside an ORX run.

CLI writes one ID-aligned feature asset and merges it into a shared manifest.
All inputs are structures only. No labels, downloads, truncation or dropped rows.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import tempfile

import numpy as np
import pandas as pd
from rdkit import Chem, rdBase

from .features import molecule_ids, verified_file, _path


class ExtractionFailure(RuntimeError):
    def __init__(self, message, audit):
        super().__init__(message)
        self.audit = audit


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=path.name+'.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def _bundle(record, root, directory_key, suffixes):
    """Require every executable/config/weight file to be pinned, not only weights."""
    directory = _path(record[directory_key], root).resolve()
    revision = record.get('revision')
    if not isinstance(revision, str) or len(revision) != 40:
        raise ValueError('Encoder asset requires its full 40-character source revision')
    files = record.get('files_sha256', {})
    if not files:
        raise ValueError('Encoder asset requires files_sha256 covering its local bundle')
    for name, digest in files.items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory):
            raise ValueError('Asset bundle member escapes its directory')
        verified_file(path, digest, root)
    relevant = {str(p.relative_to(directory)) for p in directory.rglob('*')
                if p.is_file() and p.suffix in suffixes and '.git' not in p.parts}
    missing = sorted(relevant - set(files))
    if missing:
        raise ValueError(f'Unpinned bundle files: {missing[:12]}')
    return directory


def _failed(audit, ids, reason, policy):
    audit['failures'].extend({'id': value, 'reason': reason} for value in ids)
    if ids and policy == 'raise':
        raise ExtractionFailure(f'{reason}: {len(ids)} molecules; examples {ids[:8]}', audit)


def _prepare_smiles(frame, canonicalize, remove_stereo, audit, policy):
    if 'SMILES' not in frame:
        raise ValueError('SMILES is required')
    smiles = []
    invalid = []
    for identifier, value in zip(audit['ids'], frame.SMILES):
        mol = Chem.MolFromSmiles(value) if isinstance(value, str) and value else None
        if mol is None or mol.GetNumAtoms() == 0:
            smiles.append(None); invalid.append(identifier)
        else:
            if remove_stereo:
                Chem.RemoveStereochemistry(mol)
            smiles.append(Chem.MolToSmiles(mol, canonical=True, isomericSmiles=not remove_stereo)
                          if canonicalize or remove_stereo else value)
    _failed(audit, invalid, 'invalid_smiles', policy)
    audit.update(canonicalize=bool(canonicalize), remove_stereo=bool(remove_stereo))
    return smiles


def _molformer(frame, record, root, config, audit):
    directory = _bundle(record, root, 'model_dir',
                        {'.py', '.json', '.txt', '.model', '.safetensors', '.bin'})
    import torch
    from transformers import AutoModel, AutoTokenizer
    torch.manual_seed(int(config.get('seed', 42)))
    model_config = json.loads((directory / 'config.json').read_text())
    limit = int(model_config['max_position_embeddings'])
    width = int(model_config['hidden_size'])
    policy = config.get('failure_policy', 'raise')
    smiles = _prepare_smiles(frame, config.get('canonicalize', True),
                             config.get('remove_stereo', True), audit, policy)
    tokenizer = AutoTokenizer.from_pretrained(str(directory), trust_remote_code=True, local_files_only=True)
    valid = [i for i, smi in enumerate(smiles) if smi is not None]
    lengths = [None] * len(smiles)
    # Deliberately tokenize without truncation before sending any batch to a model.
    for i in valid:
        lengths[i] = len(tokenizer(smiles[i], add_special_tokens=True, truncation=False)['input_ids'])
    too_long = [i for i in valid if lengths[i] > limit]
    audit.update(token_lengths=lengths, max_positions=limit, pooling='pooler_output')
    _failed(audit, [audit['ids'][i] for i in too_long], 'token_limit_exceeded', policy)
    too_long = set(too_long); valid = [i for i in valid if i not in too_long]
    X = np.full((len(smiles), width), np.nan, dtype=np.float32)
    if not valid:
        return X
    model = AutoModel.from_pretrained(str(directory), deterministic_eval=True,
                                      trust_remote_code=True, local_files_only=True)
    device = config.get('device', 'cuda')
    model.eval().to(device)
    batch_size = int(config.get('batch_size', 64))
    if batch_size < 1:
        raise ValueError('batch_size must be positive')
    with torch.inference_mode():
        for start in range(0, len(valid), batch_size):
            batch_ids = valid[start:start+batch_size]
            tokens = tokenizer([smiles[i] for i in batch_ids], padding=True,
                               truncation=False, return_tensors='pt')
            tokens = {key: value.to(device) for key, value in tokens.items()}
            values = model(**tokens).pooler_output.detach().float().cpu().numpy()
            if values.shape != (len(batch_ids), width):
                raise ValueError(f'Unexpected MoLFormer output shape {values.shape}')
            X[batch_ids] = values
    return X


def _monroe(frame, record, root, config, audit):
    source = _bundle(record, root, 'source_dir', {'.py', '.json', '.csv'})
    weights = verified_file(record['model_asset']['path'], record['model_asset']['sha256'], root)
    configuration = verified_file(record['config_asset']['path'], record['config_asset']['sha256'], root)
    # Do not accidentally use an already-imported installation from a different revision.
    loaded = sys.modules.get('monroe')
    if loaded is not None and not Path(loaded.__file__).resolve().is_relative_to(source):
        raise ValueError('A different Monroe source bundle is already imported')
    sys.path.insert(0, str(source))
    import torch
    from torch_geometric.data import Batch
    from monroe.eval.embed import featurize_smiles, to_pyg
    from monroe.model.ckpt import _build_encoder, _load_state_dict
    torch.manual_seed(int(config.get('seed', 42)))
    policy = config.get('failure_policy', 'raise')
    smiles = _prepare_smiles(frame, config.get('canonicalize', False), False, audit, policy)
    unique = list(dict.fromkeys(s for s in smiles if s is not None))
    # The public helper forks workers: prepare graphs before initializing CUDA.
    workers = int(config.get('num_workers', 4))
    if workers < 1:
        raise ValueError('num_workers must be positive')
    graphs = dict(featurize_smiles(unique, n_workers=workers))
    missing = [audit['ids'][i] for i, smi in enumerate(smiles) if smi is not None and smi not in graphs]
    _failed(audit, missing, 'monroe_featurization_failed', policy)
    flat = set()
    for smi, graph in graphs.items():
        pos = np.asarray(graph['pos_rdkit'])
        if pos.ndim != 2 or pos.shape[1] != 3 or not np.isfinite(pos).all():
            raise ExtractionFailure(f'Invalid Monroe coordinates for {smi}', audit)
        if np.allclose(pos[:, 2], 0):
            flat.add(smi)
    audit['flat_coordinate_ids'] = [audit['ids'][i] for i, smi in enumerate(smiles) if smi in flat]
    audit['flat_coordinate_note'] = 'All z coordinates zero; may be planar or source 2D fallback, not proof of failure.'
    audit['geometry_reproducibility'] = 'Upstream ETKDGv3 uses random coordinates without an explicit randomSeed; preserve the hashed output matrix for exact reuse.'
    flat_policy = config.get('flat_policy', 'record')
    if flat_policy not in ('record', 'raise'):
        raise ValueError('flat_policy must be record or raise')
    if flat_policy == 'raise':
        _failed(audit, audit['flat_coordinate_ids'], 'flat_coordinates', 'raise')
    hp = json.loads(configuration.read_text())
    encoder = _build_encoder(hp)
    state = _load_state_dict(weights, device='cpu')
    if any(k.startswith('encoder.') for k in state):
        encoder_state = {k[len('encoder.'):]: v for k, v in state.items() if k.startswith('encoder.')}
        audit['ignored_nonencoder_state_keys'] = [k for k in state if not k.startswith('encoder.')]
    else:
        encoder_state = state
        audit['ignored_nonencoder_state_keys'] = []
    encoder.load_state_dict(encoder_state, strict=True)
    width = int(hp['encoder']['hidden_dim'])
    device = config.get('device', 'cuda'); encoder.eval().to(device)
    batch_size = int(config.get('batch_size', 32))
    if batch_size < 1:
        raise ValueError('batch_size must be positive')
    keys = [smi for smi in unique if smi in graphs]; vectors = {}
    with torch.inference_mode():
        for start in range(0, len(keys), batch_size):
            batch_smiles = keys[start:start+batch_size]
            batch = Batch.from_data_list([to_pyg(graphs[smi]) for smi in batch_smiles]).to(device)
            values, _ = encoder(batch)
            values = values.detach().float().cpu().numpy()
            if values.shape != (len(batch_smiles), width):
                raise ValueError(f'Unexpected Monroe output shape {values.shape}')
            vectors.update(zip(batch_smiles, values))
    X = np.full((len(smiles), width), np.nan, dtype=np.float32)
    for i, smi in enumerate(smiles):
        if smi in vectors:
            X[i] = vectors[smi]
    audit['unique_valid_smiles'] = len(keys)
    return X


def _chemeleon_foundation(frame, record, root, config, audit):
    """Original descriptor-pretrained message passing only; no CYP-fit layers."""
    expected = 'c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651'
    asset = record['model_asset']
    if asset['sha256'].lower() != expected:
        raise ValueError('chemeleon_foundation requires the original published descriptor-pretrained checkpoint SHA')
    weights = verified_file(asset['path'], expected, root)
    import torch
    from chemprop import nn, featurizers
    from chemprop.data.collate import BatchMolGraph
    torch.manual_seed(int(config.get('seed', 42)))
    ck = torch.load(weights, weights_only=True, map_location='cpu')
    mp = nn.BondMessagePassing(**ck['hyper_parameters'])
    mp.load_state_dict(ck['state_dict'], strict=True)
    device = config.get('device', 'cuda'); mp.eval().to(device)
    aggregation = config.get('aggregation', 'mean')
    if aggregation not in ('mean', 'sum', 'norm'):
        raise ValueError('aggregation must be mean, sum or norm')
    aggregate = {'mean': nn.MeanAggregation, 'sum': nn.SumAggregation, 'norm': nn.NormAggregation}[aggregation]().to(device)
    feat = featurizers.SimpleMoleculeMolGraphFeaturizer()
    policy = config.get('failure_policy', 'raise')
    smiles = _prepare_smiles(frame, config.get('canonicalize', False), False, audit, policy)
    graphs, indices = [], []
    for i, smi in enumerate(smiles):
        if smi is None:
            continue
        try:
            graph = feat(Chem.MolFromSmiles(smi))
            if graph.V.shape[1] != ck['hyper_parameters']['d_v'] or graph.E.shape[1] != ck['hyper_parameters']['d_e']:
                raise ValueError('Featurizer dimensions disagree with foundation checkpoint')
            graphs.append(graph); indices.append(i)
        except Exception as exc:
            _failed(audit, [audit['ids'][i]], f'chemeleon_featurization:{type(exc).__name__}:{exc}', policy)
    width = int(mp.output_dim)
    X = np.full((len(smiles), width), np.nan, dtype=np.float32)
    batch_size = int(config.get('batch_size', 128))
    if batch_size < 1:
        raise ValueError('batch_size must be positive')
    with torch.inference_mode():
        for start in range(0, len(graphs), batch_size):
            batch = BatchMolGraph(graphs[start:start+batch_size]); batch.to(device)
            values = aggregate(mp(batch), batch.batch).detach().float().cpu().numpy()
            batch_indices = indices[start:start+batch_size]
            if values.shape != (len(batch_indices), width):
                raise ValueError(f'Unexpected CheMeleon output shape {values.shape}')
            X[batch_indices] = values
    audit.update(aggregation=aggregation, foundation_sha256=expected,
                 foundation_url='https://zenodo.org/records/15460715/files/chemeleon_mp.pt',
                 cyp_finetuning=False, pooling_before_predictor=True,
                 encoder_hyperparameters={k:v for k,v in ck['hyper_parameters'].items()
                                          if isinstance(v, (str,int,float,bool,type(None)))})
    return X


def extract_features(frame, family, asset_root, config=None):
    config = dict(config or {}); root = Path(asset_root)
    policy = config.get('failure_policy', 'raise')
    if policy not in ('raise', 'nan'):
        raise ValueError('failure_policy must be raise or nan')
    manifest_path = _path(config.get('encoder_manifest', 'encoder_manifest.json'), root)
    record = config.get('encoder_asset')
    if record is None:
        record = json.loads(manifest_path.read_text())['encoders'][config.get('encoder_key', family)]
    audit = {'family': family, 'ids': molecule_ids(frame), 'failures': [],
             'encoder_asset': record, 'config': config, 'rdkit_version': rdBase.rdkitVersion,
             'downloads_disabled': True, 'failure_policy': policy, 'versions': {}}
    for package in ('torch', 'torch-geometric', 'transformers', 'numpy', 'datamol', 'chemprop'):
        try:
            audit['versions'][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    try:
        adapters = {'monroe': _monroe, 'molformer': _molformer, 'chemeleon_foundation': _chemeleon_foundation}
        if family not in adapters:
            raise ValueError(f'Unsupported encoder {family}')
        X = adapters[family](frame, record, root, config, audit)
        bad = np.flatnonzero(~np.isfinite(X).all(axis=1))
        failed = {item['id'] for item in audit['failures']}
        _failed(audit, [audit['ids'][i] for i in bad if audit['ids'][i] not in failed],
                'nonfinite_encoder_output', policy)
        X[~np.isfinite(X)] = np.nan
        audit.update(shape=list(X.shape), failed_rows=len(bad), status='completed')
        return X, [f'{family}_{i}' for i in range(X.shape[1])], audit
    except ExtractionFailure:
        raise
    except Exception as exc:
        audit.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        raise ExtractionFailure(str(exc), audit) from exc


def publish_features(frame, X, names, audit, asset_root, asset_key, manifest_name='feature_manifest.json'):
    """Atomic shared manifest update. Lock serializes different encoder publishers."""
    root = Path(asset_root).resolve(); root.mkdir(parents=True, exist_ok=True)
    if not asset_key or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in asset_key):
        raise ValueError('asset_key must contain only letters, digits, underscore or hyphen')
    ids = molecule_ids(frame)
    if X.shape != (len(ids), len(names)) or audit['ids'] != ids:
        raise ValueError('Embedding publication alignment mismatch')
    # Content-addressed directories keep old manifests valid while an update is prepared.
    signature = hashlib.sha256(json.dumps({'ids': ids, 'smiles': frame.SMILES.tolist(),
        'encoder': audit['encoder_asset'], 'config': audit['config']}, sort_keys=True).encode()).hexdigest()
    directory = root / 'features' / f'{asset_key}-{signature[:20]}'
    manifest_path = _path(manifest_name, root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with Path(str(manifest_path)+'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'features': {}}
        assets = manifest.setdefault('features', {})
        if asset_key in assets:
            raise FileExistsError(f'Feature key {asset_key} already published; use a new explicit key')
        directory.mkdir(parents=True, exist_ok=True)
        matrix_path = directory / 'matrix.npy'; ids_path = directory / 'ids.csv'
        np.save(matrix_path, np.asarray(X, dtype=np.float32), allow_pickle=False)
        pd.DataFrame({'Molecule_Name': ids}).to_csv(ids_path, index=False)
        audit['dataset_signature'] = signature
        _atomic_json(directory / 'audit.json', audit)
        record = {'matrix_path': str(matrix_path.relative_to(root)), 'sha256': _sha(matrix_path),
                  'ids_path': str(ids_path.relative_to(root)), 'ids_sha256': _sha(ids_path),
                  'id_column': 'Molecule_Name', 'columns': names, 'shape': list(X.shape),
                  'audit_path': str((directory/'audit.json').relative_to(root)),
                  'audit_sha256': _sha(directory/'audit.json'), 'dataset_signature': signature,
                  'nonfinite_policy': audit['failure_policy']}
        assets[asset_key] = record
        _atomic_json(manifest_path, manifest)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--molecules', required=True, help='CSV with unique Molecule_Name and SMILES; labels ignored')
    parser.add_argument('--encoder', choices=['monroe', 'molformer', 'chemeleon_foundation'], required=True)
    parser.add_argument('--asset-root', required=True)
    parser.add_argument('--asset-key', required=True)
    parser.add_argument('--encoder-manifest', default='encoder_manifest.json')
    parser.add_argument('--feature-manifest', default='feature_manifest.json')
    parser.add_argument('--expected-rows', type=int, default=5655)
    parser.add_argument('--config', help='JSON with extraction settings, no model downloads')
    parser.add_argument('--audit-path', required=True, help='Written on success and failure')
    args = parser.parse_args(argv)
    try:
        frame = pd.read_csv(args.molecules, usecols=['Molecule_Name', 'SMILES'], dtype=str)
        config = json.loads(Path(args.config).read_text()) if args.config else {}
        config['encoder_manifest'] = args.encoder_manifest
        ids = molecule_ids(frame)
        if len(ids) != args.expected_rows:
            raise ValueError(f'Expected {args.expected_rows} molecules, received {len(ids)}')
        X, names, audit = extract_features(frame, args.encoder, Path(args.asset_root), config)
        record = publish_features(frame, X, names, audit, args.asset_root, args.asset_key, args.feature_manifest)
        audit['published_asset'] = record
        _atomic_json(args.audit_path, audit)
        print(json.dumps({'status': 'completed', 'asset_key': args.asset_key,
                          'shape': list(X.shape), 'failed_rows': audit['failed_rows']}), flush=True)
    except Exception as exc:
        audit = getattr(exc, 'audit', {})
        audit.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        _atomic_json(args.audit_path, audit)
        raise


if __name__ == '__main__':
    main()
