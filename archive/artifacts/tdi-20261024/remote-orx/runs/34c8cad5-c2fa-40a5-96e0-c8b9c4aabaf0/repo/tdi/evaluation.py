"""Masked scoring and train-OOF-only TDI ensemble policies. No file/label loading."""
from __future__ import annotations
import hashlib
import inspect
import itertools
import json
import numpy as np

TARGETS = ('CYP2D6_is_TDI', 'CYP3A4_is_TDI')
THRESHOLDS = np.linspace(.05, .95, 37)


def _labels(y, ndim=2):
    a = np.asarray(y, dtype=float)
    if a.ndim != ndim or (ndim == 2 and a.shape[1] != 2):
        raise ValueError('Expected N x 2 labels' if ndim == 2 else 'Expected 1D labels')
    if np.isinf(a).any() or not np.isin(a[np.isfinite(a)], [0, 1]).all():
        raise ValueError('Known labels must be 0/1; missing labels must be NaN')
    return a


def _ids(ids, n):
    result = [str(x) for x in ids] if ids is not None else [f'row:{i}' for i in range(n)]
    if len(result) != n or len(set(result)) != n:
        raise ValueError('IDs must be unique and match row count')
    return {'ids': result, 'id_kind': 'molecule_ids' if ids is not None else 'array_row_indices',
            'ids_sha256': hashlib.sha256(json.dumps(result, separators=(',', ':')).encode()).hexdigest()}


def _binary_score(y, pred):
    y = np.asarray(y, dtype=bool); pred = np.asarray(pred, dtype=bool)
    tp = int(np.sum(y & pred)); tn = int(np.sum(~y & ~pred))
    fp = int(np.sum(~y & pred)); fn = int(np.sum(y & ~pred))
    den = float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** .5
    return {'mcc': float((tp * tn - fp * fn) / den) if den else 0.,
            'n': len(y), 'positive': int(y.sum()), 'negative': int((~y).sum()),
            'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
            'predicted_positive_rate': float(pred.mean()) if len(pred) else None,
            'degenerate': den == 0}


def score(y, pred, ids=None):
    """Known-label binary MCC and equal-target macro; undefined if task unlabeled."""
    y = _labels(y); pred = np.asarray(pred, dtype=float)
    if pred.shape != y.shape:
        raise ValueError('Prediction shape differs from labels')
    metadata = _ids(ids, len(y)); per_target = {}
    for j, target in enumerate(TARGETS):
        known = np.isfinite(y[:, j]); p = pred[known, j]
        if not np.isfinite(p).all() or not np.isin(p, [0, 1]).all():
            raise ValueError('Predictions at known labels must be binary and finite')
        per_target[target] = ({'defined': True, **_binary_score(y[known, j], p)} if known.any()
                              else {'defined': False, 'mcc': None, 'n': 0})
    defined = all(x['defined'] for x in per_target.values())
    return {'defined': defined, 'macro_mcc': float(np.mean([x['mcc'] for x in per_target.values()])) if defined else None,
            'per_target': per_target, 'evaluation_input': metadata}


def optimize_threshold(y, prob, *, exact=False):
    """Native ascending 37-point grid; ties retain first threshold (Jeremy rule)."""
    y = _labels(y, 1); p = np.asarray(prob, dtype=float)
    if p.shape != y.shape:
        raise ValueError('Probability shape differs from labels')
    known = np.isfinite(y); y = y[known]; p = p[known]
    if not len(y):
        raise ValueError('Cannot fit a threshold without observed labels')
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError('Known-label probabilities must be finite in [0, 1]')
    grid = np.unique(np.r_[THRESHOLDS, p, np.nextafter(p.max(), np.inf)]) if exact else THRESHOLDS
    best = None
    for threshold in grid:
        result = _binary_score(y, p >= threshold)
        if best is None or result['mcc'] > best['mcc']:
            best = {'threshold': float(threshold), **result}
    return {**best, 'comparison': '>=', 'candidate_count': len(grid),
            'grid': 'native_37' if not exact else 'native_37_plus_exact_breakpoints'}


def _library(oofdict, y=None):
    if not oofdict:
        raise ValueError('Empty prediction library')
    names = list(oofdict); values = [np.asarray(oofdict[n], dtype=float) for n in names]
    shape = values[0].shape
    if len(shape) != 2 or shape[1] != 2 or any(v.shape != shape for v in values):
        raise ValueError('Every model must provide the same N x 2 array')
    if y is not None and shape != y.shape:
        raise ValueError('OOF predictions and labels must align')
    matrix = np.stack(values, axis=-1)
    required = np.ones(shape, dtype=bool) if y is None else np.isfinite(y)
    selected = matrix[required]
    if not np.isfinite(selected).all() or np.any((selected < 0) | (selected > 1)):
        raise ValueError('All models need finite [0,1] scores at required rows')
    return names, matrix


def _weight_grid(n, denominator=4):
    if not 1 <= n <= 3:
        raise ValueError('Predeclared blend supports one to three models')
    if not isinstance(denominator, int) or denominator < 1:
        raise ValueError('Grid denominator must be a positive integer')
    rows = [v for v in itertools.product(range(denominator + 1), repeat=n) if sum(v) == denominator]
    rows.sort(key=lambda v: (sum(x > 0 for x in v), tuple(-x for x in v)))
    return [np.asarray(v, dtype=float) / denominator for v in rows]


def fit_policy(oofdict, y, folds, *, ids=None, grid_denominator=4, exact_thresholds=False):
    """Rank fixed blend weights via crossfit thresholds; refit threshold on all OOF.

    Each recipe's threshold is fit on other folds and scored on its excluded fold.
    Choosing the best recipe still makes this a DEVELOPMENT score, not an unbiased
    holdout estimate. Caller owns OOF provenance and consistent row alignment.
    """
    y = _labels(y); names, matrix = _library(oofdict, y); folds = np.asarray(folds)
    if folds.ndim != 1 or len(folds) != len(y):
        raise ValueError('folds must contain one fold ID per row')
    if any(x is None or (isinstance(x, (float, np.floating)) and not np.isfinite(x)) for x in folds):
        raise ValueError('Missing fold IDs')
    unique = np.unique(folds)
    if len(unique) < 2:
        raise ValueError('Crossfit selection needs at least two folds')
    selection_input = _ids(ids, len(y)); selection_input['folds'] = folds.tolist()
    grid = _weight_grid(len(names), grid_denominator)
    weights = {}; thresholds = {}; diagnostics = {}; crossfit = np.full_like(y, np.nan)
    for j, target in enumerate(TARGETS):
        known = np.isfinite(y[:, j]); yy = y[known, j]; ff = folds[known]
        if len(np.unique(yy)) != 2:
            raise ValueError(f'{target}: selection needs both classes')
        x = matrix[known, j, :]; candidates = []
        for w in grid:
            p = x @ w; cf = np.empty(len(yy)); fold_thresholds = {}
            for fold in unique:
                validation = ff == fold
                if not validation.any():
                    continue
                training = ~validation
                if len(np.unique(yy[training])) != 2:
                    raise ValueError(f'{target}: crossfit training partition lacks both classes')
                fitted = optimize_threshold(yy[training], p[training], exact=exact_thresholds)
                cf[validation] = p[validation] >= fitted['threshold']
                fold_thresholds[str(fold)] = fitted['threshold']
            candidates.append({'weights': w.tolist(), 'crossfit': _binary_score(yy, cf),
                               'fold_thresholds': fold_thresholds, 'pred': cf})
        winner = max(candidates, key=lambda c: c['crossfit']['mcc'])
        w = np.asarray(winner['weights']); final = optimize_threshold(yy, x @ w, exact=exact_thresholds)
        weights[target] = dict(zip(names, winner['weights'])); thresholds[target] = final['threshold']
        crossfit[known, j] = winner['pred']
        diagnostics[target] = {'selected_crossfit': winner['crossfit'], 'threshold_fit': final,
            'candidate_ranking': [{k: v for k, v in c.items() if k != 'pred'} for c in candidates]}
    return {'schema_version': 1, 'kind': 'crossfit_probability_grid', 'target_order': list(TARGETS),
            'models': names, 'weights': weights, 'thresholds': thresholds, 'comparison': '>=',
            'selection_input': selection_input, 'selection_metrics': score(y, crossfit, selection_input['ids']),
            'diagnostics': diagnostics, 'grid_denominator': grid_denominator,
            'metric_scope': 'training OOF development selection; not untouched holdout',
            'outer_labels_used': False}


def apply_policy(querydict, policy, *, return_probabilities=False):
    """Apply fixed weights/thresholds; deliberately no query-label parameter."""
    names = policy['models']
    if set(querydict) != set(names):
        raise ValueError('Query model set differs from fitted policy')
    _, matrix = _library({n: querydict[n] for n in names}); p = np.zeros(matrix.shape[:2])
    for j, target in enumerate(TARGETS):
        w = np.array([policy['weights'][target][n] for n in names])
        if not np.isfinite(w).all() or np.any(w < 0) or not np.isclose(w.sum(), 1):
            raise ValueError('Invalid policy weights')
        p[:, j] = matrix[:, j] @ w
    thresholds = np.array([policy['thresholds'][t] for t in TARGETS], dtype=float)
    if not np.isfinite(thresholds).all():
        raise ValueError('Nonfinite thresholds')
    return p if return_probabilities else p >= thresholds


def fit_native_policy(oofdict, y, *, ids=None, caruana_fn=None, seed=42):
    """Original Jeremy selector plus threshold loop; accepts native hard-vote OOF.

    Root stages the pinned original cyp_submission package, or injects its exact
    caruana_bagged_ensemble function. Same-OOF selection optimism is retained.
    """
    if caruana_fn is None:
        from cyp_submission.caruana import caruana_bagged_ensemble
        caruana_fn = caruana_bagged_ensemble
    y = _labels(y); names, matrix = _library(oofdict, y)
    weights = {}; thresholds = {}; diagnostics = {}; fitted = np.full_like(y, np.nan)
    for j, target in enumerate(TARGETS):
        known = np.isfinite(y[:, j]); yy = y[known, j]; x = matrix[known, j]
        if not len(yy):
            raise ValueError(f'No known labels for {target}')
        w = caruana_fn(x, yy.astype(bool), lambda a, p: _binary_score(a, p >= .5)['mcc'],
                       minimize=False, seed=seed)
        w = np.asarray(w, dtype=float)
        if w.shape != (len(names),) or not np.isfinite(w).all() or np.any(w < 0) or not np.isclose(w.sum(), 1):
            raise ValueError('Native selector returned invalid weights')
        result = optimize_threshold(yy, x @ w)
        weights[target] = dict(zip(names, w.tolist())); thresholds[target] = result['threshold']
        diagnostics[target] = result; fitted[known, j] = (x @ w) >= result['threshold']
    try:
        source_sha = hashlib.sha256(inspect.getsource(caruana_fn).encode()).hexdigest()
    except (OSError, TypeError):
        source_sha = None
    selection_input = _ids(ids, len(y))
    return {'schema_version': 1, 'kind': 'native_jeremy_caruana', 'target_order': list(TARGETS),
            'models': names, 'weights': weights, 'thresholds': thresholds, 'comparison': '>=',
            'selection_input': selection_input, 'selection_metrics': score(y, fitted, selection_input['ids']),
            'diagnostics': diagnostics, 'caruana_function_source_sha256': source_sha, 'seed': seed,
            'metric_scope': 'same-OOF native development selection; not unbiased holdout',
            'outer_labels_used': False}


def fit_pool_policy(oofdict, y, folds, *, ids=None, grid_denominator=4, exact_thresholds=False):
    """Screen a larger fixed pool by single-model crossfit MCC, then blend top 3.

    Screening is by equal-target macro MCC using the same training OOF folds.
    Ties preserve the declared model order. All candidate scores and input IDs
    are retained. Selecting candidates and weights on this pool remains a
    development procedure; only a separate outer holdout can judge improvement.
    """
    y = _labels(y)
    names, _ = _library(oofdict, y)
    selection_input = _ids(ids, len(y))
    candidate_results = []
    for index, name in enumerate(names):
        individual = fit_policy({name: oofdict[name]}, y, folds,
                                ids=selection_input['ids'], grid_denominator=grid_denominator,
                                exact_thresholds=exact_thresholds)
        candidate_results.append({
            'name': name, 'declared_order': index,
            'crossfit_macro_mcc': individual['selection_metrics']['macro_mcc'],
            'crossfit_per_target': individual['selection_metrics']['per_target'],
            'fitted_thresholds': individual['thresholds'],
            'crossfit_threshold_diagnostics': individual['diagnostics'],
        })
    ranking = sorted(candidate_results, key=lambda r: (-r['crossfit_macro_mcc'], r['declared_order']))
    selected = [r['name'] for r in ranking[:3]]
    policy = fit_policy({n: oofdict[n] for n in selected}, y, folds, ids=selection_input['ids'],
                        grid_denominator=grid_denominator, exact_thresholds=exact_thresholds)
    policy['kind'] = 'crossfit_pool_top3_probability_grid'
    policy['selection_input']['id_kind'] = selection_input['id_kind']
    policy['pool_selection'] = {
        'candidate_names': names, 'candidate_count': len(names),
        'selected_names': selected, 'ranking': ranking,
        'criterion': 'single-model crossfit-threshold equal-target macro MCC descending',
        'tie_break': 'declared candidate order',
        'source': 'training OOF labels only; no outer labels supplied',
        'selection_input': selection_input,
    }
    return policy
