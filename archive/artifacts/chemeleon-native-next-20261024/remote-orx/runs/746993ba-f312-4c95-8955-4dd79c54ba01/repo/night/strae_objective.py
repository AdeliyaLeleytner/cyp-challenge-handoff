"""Exact primary ST-RAE and explicit nominal-head-budget auxiliary objective.

All fitting statistics are training-fold-only. No batch label-count denominator.
"""
import numpy as np
import torch
from torch import nn

MODE = 'exact_strae_v1'


def interval_distance(prediction, lower, upper):
    return torch.relu(lower - prediction) + torch.relu(prediction - upper)


def _validate_arrays(center, lower, upper, primary_indices):
    center, lower, upper = [np.asarray(x, dtype=np.float64) for x in (center, lower, upper)]
    if center.ndim != 2 or center.shape != lower.shape or center.shape != upper.shape:
        raise ValueError('Targets and interval bounds must have identical N x T shape')
    if np.isinf(center).any():
        raise ValueError('Infinite target value')
    primary = np.asarray(primary_indices, dtype=int)
    if not len(primary) or len(set(primary.tolist())) != len(primary) or np.any(primary < 0) or np.any(primary >= center.shape[1]):
        raise ValueError('Nonempty unique primary indices are required')
    observed = np.isfinite(center)
    p_observed = observed[:, primary]
    invalid = (~np.isfinite(lower[:, primary]) | ~np.isfinite(upper[:, primary]) | (lower[:, primary] > upper[:, primary]))
    if np.any(p_observed & invalid):
        raise ValueError('Observed primary target has absent/nonfinite/reversed experimental bounds')
    return center, lower, upper, primary, observed


def evaluation_statistics(center, lower, upper, primary_indices):
    y, lo, hi, primary, observed = _validate_arrays(center, lower, upper, primary_indices)
    counts, means, denominators = [], [], []
    for j in primary:
        mask = observed[:, j]
        if mask.sum() < 2:
            raise ValueError(f'Primary target {j} needs at least two observations')
        mean = float(y[mask, j].mean())
        denom = float((np.maximum(lo[mask, j] - mean, 0) + np.maximum(mean - hi[mask, j], 0)).sum())
        if not np.isfinite(denom) or denom <= 0:
            raise ValueError(f'Primary target {j} has undefined ST-RAE denominator: {denom}')
        counts.append(int(mask.sum())); means.append(mean); denominators.append(denom)
    return {'primary_indices': primary.tolist(), 'primary_counts': counts, 'primary_means': means, 'primary_denominators': denominators}


def primary_metric(predictions, center, lower, upper, primary_indices):
    y, lo, hi, primary, observed = _validate_arrays(center, lower, upper, primary_indices)
    predictions = np.asarray(predictions, dtype=np.float64)
    if predictions.shape != y.shape or not np.isfinite(predictions).all():
        raise ValueError('Finite predictions with the same N x T shape are required')
    stats = evaluation_statistics(y, lo, hi, primary)
    values = []
    for j, denominator in zip(primary, stats['primary_denominators']):
        mask = observed[:, j]
        error = np.maximum(lo[mask, j] - predictions[mask, j], 0) + np.maximum(predictions[mask, j] - hi[mask, j], 0)
        values.append(float(error.sum() / denominator))
    return {'macro_ST_RAE': float(np.mean(values)), 'per_primary_ST_RAE': values, **stats}


def fit_statistics(center, lower, upper, primary_indices, native_task_weights, scaler_mean, scaler_scale):
    y, lo, hi, primary, observed = _validate_arrays(center, lower, upper, primary_indices)
    stats = evaluation_statistics(y, lo, hi, primary)
    counts = observed.sum(axis=0)
    if np.any(counts == 0):
        raise ValueError('Every trained head needs at least one observed fit label')
    weights = np.asarray(native_task_weights, dtype=np.float64)
    means, scales = np.asarray(scaler_mean, dtype=np.float64), np.asarray(scaler_scale, dtype=np.float64)
    if weights.shape != (y.shape[1],) or not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError('Expected finite nonnegative native weights for every target')
    if means.shape != weights.shape or scales.shape != weights.shape or not np.isfinite(means).all() or not np.isfinite(scales).all() or np.any(scales <= 0):
        raise ValueError('Expected finite center-only target scaler with positive scale')
    primary_budget = float(weights[primary].sum())
    if primary_budget <= 0:
        raise ValueError('Native primary head budget must be positive')
    auxiliary = np.asarray([j for j in range(y.shape[1]) if j not in primary], dtype=int)
    coefficients = np.zeros(y.shape[1], dtype=np.float64)
    coefficients[primary] = scales[primary] / (len(primary) * np.asarray(stats['primary_denominators']))
    coefficients[auxiliary] = weights[auxiliary] / (primary_budget * counts[auxiliary])
    return {**stats, 'mode': MODE, 'n_fit_rows': len(y), 'n_targets': y.shape[1],
            'target_counts': counts.astype(int).tolist(), 'auxiliary_indices': auxiliary.tolist(),
            'native_task_weights': weights.tolist(), 'primary_native_weight_sum': primary_budget,
            'auxiliary_head_coefficients': (weights[auxiliary] / primary_budget).tolist(),
            'auxiliary_total_nominal_budget': float(weights[auxiliary].sum() / primary_budget),
            'scaler_mean': means.tolist(), 'scaler_scale': scales.tolist(),
            'per_entry_coefficients': coefficients.tolist(),
            'normalization': 'N_fit / B; primary sigma/(J*D_fit); auxiliary native_weight/(sum_primary_native_weights*n_aux_fit)',
            'qualification': 'Preserves nominal native auxiliary head ratios, not native realized label-frequency weighting. Test denominators are unknown.'}


def pack_targets(center, lower, upper, scaler_mean, scaler_scale, primary_indices):
    y, lo, hi, _, _ = _validate_arrays(center, lower, upper, primary_indices)
    mean, scale = np.asarray(scaler_mean), np.asarray(scaler_scale)
    # Both bounds use the center-only scaler; they are never fitted separately.
    return np.concatenate([(x - mean) / scale for x in (y, lo, hi)], axis=1).astype(np.float32)


class ExactSTObjective(nn.Module):
    """Uniform-row minibatch estimate; buffers do not alter native model checkpoints."""
    def __init__(self, statistics):
        super().__init__()
        self.statistics = statistics
        self.n_targets = int(statistics['n_targets'])
        self.n_fit_rows = int(statistics['n_fit_rows'])
        mask = torch.zeros(self.n_targets, dtype=torch.bool)
        mask[statistics['primary_indices']] = True
        self.register_buffer('primary_mask', mask, persistent=False)
        self.register_buffer('coefficients', torch.tensor(statistics['per_entry_coefficients'], dtype=torch.float32), persistent=False)
        self.register_buffer('center_mean', torch.tensor(statistics['scaler_mean'], dtype=torch.float32), persistent=False)
        self.register_buffer('center_scale', torch.tensor(statistics['scaler_scale'], dtype=torch.float32), persistent=False)

    def physical_predictions(self, predictions):
        return predictions.float() * self.center_scale + self.center_mean

    def forward(self, predictions, packed_targets, sample_weights=None):
        if predictions.ndim != 2 or predictions.shape[1] != self.n_targets or packed_targets.shape != (len(predictions), 3 * self.n_targets) or len(predictions) == 0:
            raise ValueError('Expected nonempty B x T predictions and B x 3T packed targets')
        # The prediction forward pass may be mixed precision; losses/reductions must not be.
        with torch.autocast(device_type=predictions.device.type, enabled=False):
            pred = predictions.float()
            target = packed_targets.float()
            center, lower, upper = target.split(self.n_targets, dim=1)
            observed = center.isfinite()
            center, lower, upper = [torch.where(observed, x, 0.).nan_to_num(nan=0., posinf=0., neginf=0.) for x in (center, lower, upper)]
            if sample_weights is not None and not torch.all(sample_weights == 1):
                raise ValueError('Exact ST-RAE adapter requires uniform row sampling and unit sample weights')
            distances = interval_distance(pred, lower, upper)
            errors = torch.where(self.primary_mask, distances, (pred - center).abs())
            entries = errors * observed * self.coefficients
            factor = self.n_fit_rows / len(pred)
            primary = factor * entries[:, self.primary_mask].sum()
            auxiliary = factor * entries[:, ~self.primary_mask].sum()
            return primary + auxiliary, primary, auxiliary
