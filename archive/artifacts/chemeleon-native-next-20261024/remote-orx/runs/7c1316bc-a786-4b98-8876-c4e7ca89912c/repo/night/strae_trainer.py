"""Explicit loss/trainer adapter around unchanged native model construction.

Native architecture, optimizer schedule, batch size, patience and inference are retained.
Packed CI labels use the center-only scaler; checkpointing uses primary validation ST-RAE.
"""
from pathlib import Path
import json, time
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from chemprop import data, models, nn
from lightning import pytorch as pl
from .strae_objective import ExactSTObjective, fit_statistics, pack_targets, primary_metric, evaluation_statistics


def extract_targets(frame, targets):
    center = frame[targets].to_numpy(dtype=np.float64)
    lower, upper = center.copy(), center.copy()
    primary = [j for j, name in enumerate(targets) if name.endswith('_pic50_direct_inhibition')]
    if not primary:
        raise ValueError('No scored direct-inhibition target in component')
    for j in primary:
        name = targets[j]
        lc, hc = name + '_ci_lower', name + '_ci_upper'
        if lc not in frame or hc not in frame:
            raise ValueError(f'Missing experimental interval columns for {name}')
        lower[:, j] = frame[lc].to_numpy(float); upper[:, j] = frame[hc].to_numpy(float)
    return center, lower, upper, primary


class ExactSTMPNN(models.MPNN):
    # No constructor changes: checkpoints retain native hyperparameter/state layout.
    def attach_objective(self, objective, validation_arrays):
        self.loss_objective = objective
        self.validation_arrays = validation_arrays
        self.loss_history = []

    def _scaled_prediction(self, batch):
        bmg, v_d, x_d, *_ = batch
        # RegressionFFN.train_step aliases forward and conditionally unscales in eval mode.
        # Read the raw head explicitly so loss coordinates never depend on transform.train().
        return self.predictor.ffn(self.fingerprint(bmg, v_d, x_d))

    def training_step(self, batch, batch_idx):
        pred = self._scaled_prediction(batch)
        total, primary, auxiliary = self.loss_objective(pred, batch.Y, batch.w)
        b = len(pred)
        for key, value in [('train_loss', total), ('train_primary_fitnorm', primary), ('train_auxiliary', auxiliary)]:
            self.log(key, value, batch_size=b, on_step=False, on_epoch=True)
        return total

    def on_validation_epoch_start(self):
        self._validation_predictions = []

    def validation_step(self, batch, batch_idx=0):
        scaled = self._scaled_prediction(batch)
        physical = self.loss_objective.physical_predictions(scaled)
        self._validation_predictions.append(physical.detach().cpu().numpy())

    def on_validation_epoch_end(self):
        predictions = np.concatenate(self._validation_predictions, axis=0)
        y, lower, upper, primary = self.validation_arrays
        # During Lightning sanity checking only a prefix is evaluated. Do not treat it as
        # a full official metric or allow it into checkpoint/early-stopping decisions.
        if self.trainer.sanity_checking:
            return
        if len(predictions) != len(y):
            raise ValueError('Validation loader dropped or duplicated rows')
        result = primary_metric(predictions, y, lower, upper, primary)
        value = result['macro_ST_RAE']
        self.log('val_primary_strae', value, batch_size=len(y), prog_bar=True, on_epoch=True)
        for index, score in zip(primary, result['per_primary_ST_RAE']):
            self.log(f'val_primary_strae_head{index}', score, batch_size=len(y), on_epoch=True)
        row = {'epoch': int(self.current_epoch), 'val_primary_strae': value,
               'per_primary_ST_RAE': result['per_primary_ST_RAE']}
        self.loss_history.append(row)
        print(json.dumps({'event': 'exact_strae_epoch', **row}), flush=True)


def train_exact_strae_fold(core, spec, train_df, val_df, train_targets, val_targets,
                           *, fold_idx=0, checkpoint_dir=None,
                           train_extra=None, val_extra=None, val_extra_raw=None):
    hp = spec.hyperparameters
    if hp.get('criterion_mode') != 'exact_strae_v1':
        raise ValueError('Explicit criterion_mode=exact_strae_v1 is required')
    if spec.use_bounded_loss or spec.task != 'regression' or hp.get('freeze_mpnn_epochs', 0) != 0:
        raise ValueError('Adapter supports uncensored regression with full-encoder training; no hidden freeze stage')
    if checkpoint_dir is None:
        raise ValueError('Best-primary-metric checkpoint directory is required')
    train_arrays = extract_targets(train_df, spec.target_columns)
    val_arrays = extract_targets(val_df, spec.target_columns)
    for supplied, actual in [(train_targets, train_arrays[0]), (val_targets, val_arrays[0])]:
        if not np.array_equal(np.asarray(supplied, np.float32), actual.astype(np.float32), equal_nan=True):
            raise ValueError('Frame/target row alignment differs')
    # Same StandardScaler fit inputs as the native MoleculeDataset.normalize_targets.
    scaler = StandardScaler().fit(np.asarray(train_targets, np.float32))
    weights = spec.task_weights if spec.task_weights is not None else np.ones(spec.n_targets)
    statistics = fit_statistics(*train_arrays, weights, scaler.mean_, scaler.scale_)
    validation_statistics = evaluation_statistics(*val_arrays)
    packed_train = pack_targets(*train_arrays[:3], scaler.mean_, scaler.scale_, train_arrays[3])
    packed_val = pack_targets(*val_arrays[:3], scaler.mean_, scaler.scale_, val_arrays[3])
    train_dps, _ = core.create_molecule_datapoints(train_df[spec.smiles_column].tolist(), packed_train, train_extra)
    val_dps, _ = core.create_molecule_datapoints(val_df[spec.smiles_column].tolist(), packed_val, val_extra)
    train_dataset, val_dataset = data.MoleculeDataset(train_dps), data.MoleculeDataset(val_dps)
    x_d_transform = None
    if spec.use_extra_features:
        feature_scaler = train_dataset.normalize_inputs('X_d')
        val_dataset.normalize_inputs('X_d', feature_scaler)
        x_d_transform = nn.ScaleTransform.from_standard_scaler(feature_scaler)
    train_dataset.cache = True; val_dataset.cache = True
    loader_kwargs = {'num_workers': spec.num_workers, 'pin_memory': True}
    if spec.num_workers > 0:
        loader_kwargs.update(persistent_workers=not spec.concurrent, prefetch_factor=2)
    train_loader = data.build_dataloader(train_dataset, batch_size=hp['batch_size'], shuffle=True, **loader_kwargs)
    val_loader = data.build_dataloader(val_dataset, batch_size=core.safe_batch_size(len(val_dataset), hp['batch_size']), shuffle=False, **loader_kwargs)
    pl.seed_everything(hp['seed'] + fold_idx)
    base = core.build_mpnn_model(hp, task=spec.task, num_classes=spec.num_classes,
        n_targets=spec.n_targets, n_extra_descriptors=spec.n_extra_descriptors,
        x_d_transform=x_d_transform, output_transform=nn.UnscaleTransform.from_standard_scaler(scaler),
        task_weights=spec.task_weights, use_bounded_loss=False)
    # Both are pure-Python LightningModule subclasses with identical instance layout;
    # switching methods preserves every native-created module and initial parameter.
    base.__class__ = ExactSTMPNN
    model = base
    model.attach_objective(ExactSTObjective(statistics), val_arrays)
    checkpoint = pl.callbacks.ModelCheckpoint(dirpath=checkpoint_dir, filename=f'best_{fold_idx}',
        monitor='val_primary_strae', mode='min', save_top_k=1, enable_version_counter=False)
    callbacks = [pl.callbacks.EarlyStopping(monitor='val_primary_strae', patience=hp['patience'], mode='min'), checkpoint]
    destination = Path(checkpoint_dir).parent
    destination.mkdir(parents=True, exist_ok=True)
    metadata = {'criterion_mode': hp['criterion_mode'], 'fit_statistics': statistics,
                'validation_statistics': validation_statistics,
                'checkpoint_monitor': 'val_primary_strae',
                'bounds_scaling': 'same fit-center mean and scale for central/lower/upper; no bound-specific fitting',
                'native_architecture_and_optimizer_preserved': True,
                'explicit_changes': ['primary exact interval macro objective', 'per-auxiliary-head observed-label mean and nominal author budget',
                                     'uniform-row unbiased minibatch estimator', 'primary-only validation checkpoint selection'],
                'precision': '16-mixed forward; FP32 differentiable loss; float64 full-validation official arithmetic'}
    (destination/'loss_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({'event': 'exact_strae_fold_config', 'fold': fold_idx, **metadata}), flush=True)
    trainer = pl.Trainer(accelerator='auto', devices=1, max_epochs=hp['max_epochs'], precision='16-mixed',
        logger=False, enable_progress_bar=spec.enable_progress_bar, enable_checkpointing=True, callbacks=callbacks)
    start = time.time(); trainer.fit(model, train_loader, val_loader)
    if not checkpoint.best_model_path:
        raise RuntimeError('No checkpoint selected by primary validation ST-RAE')
    saved = torch.load(checkpoint.best_model_path, weights_only=False, map_location='cpu')
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    (destination/'loss_history.json').write_text(json.dumps(model.loss_history, indent=2) + '\n')
    print(json.dumps({'event': 'exact_strae_fold_fit_complete', 'fold': fold_idx, 'seconds': time.time()-start,
                     'best_primary_validation_ST_RAE': float(checkpoint.best_model_score), 'best_epoch': int(saved['epoch'])}), flush=True)
    prediction = core.predict_chemprop_frame(model, spec, val_df, targets=val_targets, extra=val_extra_raw)
    return model, prediction
