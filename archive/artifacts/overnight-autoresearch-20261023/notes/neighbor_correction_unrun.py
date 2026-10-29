"""Cheap local residual transfer inspired by MolPAIR, not its paper reproduction.

Default development-only grid is K=[5,20], power=[2,4], blend=[0,.25,.5,1].
One global setting is selected across all four targets. mode='fixed' instead
uses preregistered K5/power4/blend.5 without choosing settings from scores.
Nonnegative count fingerprints use explicitly defined dot-product Tanimoto;
counts are not binarized and no metric-learning model is fitted.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

import numpy as np
import pandas as pd
from scipy import sparse

from .evaluation import score
from .reference import CANONICAL


def _ids(frame, name):
    if "Molecule_Name" not in frame or frame.Molecule_Name.isna().any():
        raise ValueError(f"{name} needs non-null Molecule_Name")
    ids = frame.Molecule_Name.astype(str).tolist()
    if len(ids) != len(set(ids)):
        raise ValueError(f"{name} contains duplicate IDs")
    return ids


def _frame_hash(frame):
    return hashlib.sha256(frame.to_csv(index=False, float_format="%.17g").encode()).hexdigest()


def _predictions(frame, ids, name):
    actual = _ids(frame, name)
    if set(actual) != set(ids) or not set(CANONICAL) <= set(frame):
        raise ValueError(f"{name} must cover the exact IDs and all four targets")
    out = frame.assign(Molecule_Name=actual).set_index("Molecule_Name").loc[ids, CANONICAL].reset_index()
    if not np.isfinite(out[CANONICAL].to_numpy(float)).all():
        raise ValueError(f"{name} contains nonfinite predictions")
    return out


def _features(value, ids, name):
    """Accept ID-bearing DataFrame or {'ids': [...], 'X': dense/CSR, optional feature_names}."""
    if isinstance(value, pd.DataFrame):
        actual = _ids(value, name)
        columns = [c for c in value.columns if c != "Molecule_Name"]
        matrix = value[columns].to_numpy()
        columns = list(map(str, columns))
    elif isinstance(value, Mapping) and "ids" in value and "X" in value:
        if any(pd.isna(v) for v in value["ids"]):
            raise ValueError(f"{name} has missing feature IDs")
        actual = list(map(str, value["ids"]))
        matrix = value["X"]
        columns = None if value.get("feature_names") is None else list(map(str, value["feature_names"]))
    else:
        raise TypeError(f"{name} must carry explicit IDs; bare positional arrays are not accepted")
    if len(actual) != len(set(actual)) or set(actual) != set(ids):
        raise ValueError(f"{name} IDs must exactly match predictions/truth without duplicates")
    if getattr(matrix, "ndim", None) != 2 or matrix.shape[0] != len(actual) or matrix.shape[1] == 0:
        raise ValueError(f"{name} has invalid feature shape")
    raw = matrix.data if sparse.issparse(matrix) else np.asarray(matrix)
    if not np.issubdtype(raw.dtype, np.number) or np.iscomplexobj(raw):
        raise ValueError(f"{name} must contain real numeric counts")
    if not np.isfinite(raw).all() or np.any(raw < 0):
        raise ValueError(f"{name} counts must be finite and nonnegative")
    if columns is not None and (len(columns) != matrix.shape[1] or len(columns) != len(set(columns))):
        raise ValueError(f"{name} has invalid or duplicate feature names")
    original_dtype = str(matrix.dtype)
    result = sparse.csr_matrix(matrix, dtype=np.float64, copy=True)
    result.sum_duplicates()
    result.sort_indices()
    result.eliminate_zeros()
    lookup = {key: i for i, key in enumerate(actual)}
    result = result[[lookup[key] for key in ids]]
    if not np.isfinite(result.data).all():
        raise ValueError(f"{name} overflows after combining sparse entries")
    digest = hashlib.sha256(json.dumps({"ids": ids, "shape": result.shape, "feature_names": columns}, sort_keys=True).encode())
    for array in [result.indptr, result.indices, result.data]:
        digest.update(str(array.dtype).encode())
        digest.update(array.tobytes())
    return result, columns, {"sha256": digest.hexdigest(), "shape": list(result.shape),
                             "nonzero_entries": int(result.nnz), "input_dtype": original_dtype,
                             "storage": "CSR float64 for kernel accumulation; no binarization or learned scaling"}


def tanimoto_kernel(left, right, *, block_size=256):
    """Dot-product count Tanimoto; zero/zero is0 (no similarity evidence), not1."""
    if block_size < 1:
        raise ValueError("Kernel block_size must be positive")
    ln = np.asarray(left.multiply(left).sum(axis=1)).ravel()
    rn = np.asarray(right.multiply(right).sum(axis=1)).ravel()
    if not np.isfinite(ln).all() or not np.isfinite(rn).all():
        raise ValueError("Feature squared norms overflow")
    output = np.empty((left.shape[0], right.shape[0]), dtype=np.float32)
    for start in range(0, left.shape[0], block_size):
        stop = min(start + block_size, left.shape[0])
        dot = (left[start:stop] @ right.T).toarray()
        denominator = ln[start:stop, None] + rn[None, :] - dot
        if not np.isfinite(dot).all() or not np.isfinite(denominator).all():
            raise ValueError("Tanimoto arithmetic overflow")
        values = np.divide(dot, denominator, out=np.zeros_like(dot), where=denominator > 0)
        if np.any(values < -1e-7) or np.any(values > 1 + 1e-7):
            raise ValueError("Tanimoto kernel violates nonnegative count bounds")
        output[start:stop] = np.clip(values, 0, 1)
    return output


def _transfers(kernel, residuals, observed, anchor_pool, row_ids, anchor_ids,
               row_parents, anchor_parents, combinations):
    """Reuse a top-maxK shortlist for all K/power settings, independently by target."""
    n = kernel.shape[0]
    outputs = {key: {"correction": np.zeros((n, 4)), "nearest_similarity": np.zeros((n, 4)),
                     "anchor_count": np.zeros((n, 4), dtype=int), "effective_anchors": np.zeros((n, 4))}
               for key in combinations}
    max_k = max(k for k, _ in combinations)
    anchor_ids = np.asarray(anchor_ids, dtype=str)
    row_ids = np.asarray(row_ids, dtype=str)
    for j in range(4):
        candidates = np.flatnonzero(anchor_pool & observed[:, j])
        if not len(candidates):
            continue  # Explicit uncovered rows keep the supplied baseline unchanged.
        similarities = kernel[:, candidates].copy()
        similarities[row_ids[:, None] == anchor_ids[candidates][None, :]] = 0
        if row_parents is not None:
            similarities[np.asarray(row_parents)[:, None] == np.asarray(anchor_parents)[candidates][None, :]] = 0
        count = min(max_k, len(candidates))
        # Stable sorting makes tied similarities deterministic in official training-row order.
        order = np.argsort(-similarities, axis=1, kind="stable")[:, :count]
        nearest = np.take_along_axis(similarities, order, axis=1)
        anchor_residuals = residuals[candidates, j][order]
        for (k, power), out in outputs.items():
            use = min(k, count)
            similarity = nearest[:, :use].astype(float)
            weights = similarity ** power
            total = weights.sum(axis=1)
            weighted = (weights * anchor_residuals[:, :use]).sum(axis=1)
            out["correction"][:, j] = np.divide(weighted, total, out=np.zeros(n), where=total > 0)
            out["nearest_similarity"][:, j] = similarity[:, 0]
            out["anchor_count"][:, j] = (weights > 0).sum(axis=1)
            square_sum = (weights ** 2).sum(axis=1)
            out["effective_anchors"][:, j] = np.divide(total ** 2, square_sum, out=np.zeros(n), where=square_sum > 0)
    return outputs


def _diagnostic_summary(values):
    result = {}
    for j, target in enumerate(CANONICAL):
        covered = values["anchor_count"][:, j] > 0
        result[target] = {"n_rows": len(covered), "covered_rows": int(covered.sum()),
            "coverage": float(covered.mean()),
            "nearest_similarity_mean": float(values["nearest_similarity"][:, j].mean()),
            "nearest_similarity_quantiles": np.quantile(values["nearest_similarity"][:, j], [0, .25, .5, .75, 1]).tolist(),
            "mean_positive_anchor_count": float(values["anchor_count"][:, j].mean()),
            "mean_effective_anchors": float(values["effective_anchors"][:, j].mean()),
            "mean_absolute_transfer": float(np.abs(values["correction"][:, j]).mean())}
    return result


def fit_neighbor_correction(ooftruth, oofpred, querypred, trainfeatures, queryfeatures,
                            development_folds, config=None):
    """Return (query predictions, metadata); no query labels/moments enter selection.

    ID-bearing feature inputs: DataFrame with Molecule_Name + feature columns, or
    {'ids': [...], 'X': dense/CSR, 'feature_names': optional names}. Parent guard:
    optional config.normalized_parent_keys mapping must cover every development
    and query ID; same-parent anchors are then excluded in CV and final transfer.
    config.mode='fixed' uses K5,power4,blend.5 without score-based selection.
    Optional allowed_fit_ids/forbidden_fit_ids enforce the caller's outer cohort.
    """
    cfg = dict(config or {})
    if cfg.get("kernel", "tdp") != "tdp":
        raise ValueError("Only explicitly defined dot-product count Tanimoto is implemented")
    ids, qids = _ids(ooftruth, "development truth"), _ids(querypred, "query predictions")
    if not ids or not qids or set(ids) & set(qids):
        raise ValueError("Development and query IDs must be nonempty and disjoint")
    if cfg.get("allowed_fit_ids") is not None and not set(ids) <= set(map(str, cfg["allowed_fit_ids"])):
        raise ValueError("Development labels lie outside allowed fitting IDs")
    if set(ids) & set(map(str, cfg.get("forbidden_fit_ids", []))):
        raise ValueError("Forbidden gate/test IDs occur in development truth")
    truth = ooftruth.assign(Molecule_Name=ids).reset_index(drop=True)
    required = list(CANONICAL) + [t + s for t in CANONICAL for s in ["_conf_low", "_conf_high"]]
    if not set(required) <= set(truth):
        raise ValueError("All four development labels and confidence-bound columns are required")
    central = truth[CANONICAL].to_numpy(float)
    if np.isinf(central).any():
        raise ValueError("Infinite central truth labels")
    observed = np.isfinite(central)
    low = truth[[t + "_conf_low" for t in CANONICAL]].to_numpy(float)
    high = truth[[t + "_conf_high" for t in CANONICAL]].to_numpy(float)
    if np.any(observed & (~np.isfinite(low) | ~np.isfinite(high) | (low > high))):
        raise ValueError("Observed labels have invalid uncertainty bounds")
    base = _predictions(oofpred, ids, "OOF predictions")
    query = _predictions(querypred, qids, "query predictions")
    base_values = base[CANONICAL].to_numpy(float)
    residuals = np.where(observed, np.clip(base_values, low, high) - base_values, 0.0)
    features, feature_names, feature_meta = _features(trainfeatures, ids, "training features")
    qfeatures, qfeature_names, qfeature_meta = _features(queryfeatures, qids, "query features")
    if features.shape[1] != qfeatures.shape[1] or feature_names != qfeature_names:
        raise ValueError("Training/query feature dimensions or feature-name order differ")
    raw_mapping = dict(development_folds)
    mapping = {str(k): v for k, v in raw_mapping.items()}
    if len(mapping) != len(raw_mapping) or set(mapping) != set(ids):
        raise ValueError("Development fold mapping must cover exactly the development IDs")
    folds = pd.Series([mapping[i] for i in ids])
    if folds.isna().any() or folds.nunique() < 2:
        raise ValueError("At least two nonmissing development folds are required")
    parent_map = cfg.get("normalized_parent_keys")
    parents = qparents = None
    if parent_map is not None:
        raw_parents = dict(parent_map)
        parent_map = {str(k): v for k, v in raw_parents.items()}
        if len(parent_map) != len(raw_parents) or not set(ids + qids) <= set(parent_map):
            raise ValueError("Provided parent mapping does not cover all IDs")
        if any(not isinstance(parent_map[i], str) or not parent_map[i] for i in ids + qids):
            raise ValueError("Provided normalized parent keys must be nonempty strings")
        parents = np.asarray([parent_map[i] for i in ids])
        qparents = np.asarray([parent_map[i] for i in qids])
    mode = cfg.get("mode", "crossfit")
    if mode == "fixed":
        settings = [{"k": 5, "power": 4.0, "blend": .5}]
    elif mode == "crossfit":
        ks = cfg.get("k_grid", [5, 20])
        powers = cfg.get("power_grid", [2, 4])
        blends = cfg.get("blend_grid", [0, .25, .5, 1])
        if not ks or not powers or not blends:
            raise ValueError("Candidate grids must be nonempty")
        if any(isinstance(k, bool) or not isinstance(k, (int, np.integer)) or k < 1 for k in ks):
            raise ValueError("K values must be positive integers")
        if any(not np.isfinite(p) or p <= 0 for p in powers) or any(not np.isfinite(b) or not 0 <= b <= 1 for b in blends):
            raise ValueError("Powers must be finite positive; blends finite in [0,1]")
        if any(len(set(v)) != len(v) for v in [ks, powers, blends]):
            raise ValueError("Candidate grids must not contain duplicates")
        settings = [{"k": int(k), "power": float(p), "blend": float(b)} for b in blends for k in ks for p in powers]
        # Deterministic ties prefer no correction, then lower blend, smaller K, lower power.
        settings.sort(key=lambda s: (s["blend"], s["k"], s["power"]))
    else:
        raise ValueError("mode must be crossfit or fixed")
    combinations = sorted({(s["k"], s["power"]) for s in settings})
    protocol = {"version": 1, "mode": mode, "settings": settings,
                "kernel": "dot-product count Tanimoto: dot/(squared_norm_left+squared_norm_right-dot); zero/zero=0",
                "residual": "clip(OOF prediction, observed confidence lower, observed confidence upper) - OOF prediction; zero inside interval",
                "selection": "No CV tuning: fixed preregistered setting" if mode == "fixed" else "One global setting minimizing pooled development crossfit macro ST-RAE",
                "parent_guard": parents is not None, "self_exclusion": True,
                "zero_coverage": "Transfer0 and preserve baseline; no random or label-imputation fallback",
                "tie_order": "Ascending blend, K, power; neighbor ties use aligned development row order"}
    kernel = tanimoto_kernel(features, features, block_size=int(cfg.get("kernel_block_size", 256)))
    np.fill_diagonal(kernel, 0.0)
    crossfit = {key: {"correction": np.zeros((len(ids), 4)), "nearest_similarity": np.zeros((len(ids), 4)),
                      "anchor_count": np.zeros((len(ids), 4), dtype=int), "effective_anchors": np.zeros((len(ids), 4))}
                for key in combinations}
    fold_counts = []
    for fold in pd.unique(folds):
        val = folds.eq(fold).to_numpy()
        transfers = _transfers(kernel[val], residuals, observed, ~val, np.asarray(ids)[val], ids,
                               None if parents is None else parents[val], parents, combinations)
        for key in combinations:
            for field in crossfit[key]:
                crossfit[key][field][val] = transfers[key][field]
        fold_counts.append({"fold": str(fold), "validation_rows": int(val.sum()),
                            "known_training_anchor_counts": dict(zip(CANONICAL, observed[~val].sum(axis=0).astype(int).tolist()))})
    del kernel
    baseline_score = score(truth, base, targets=CANONICAL)
    if not baseline_score["defined"]:
        raise ValueError("Undefined development ST-RAE; no valid global setting comparison")
    candidates = []
    for setting in settings:
        transfer = crossfit[(setting["k"], setting["power"])]
        predicted = base.copy()
        predicted[CANONICAL] = base_values + setting["blend"] * transfer["correction"]
        metrics = score(truth, predicted, targets=CANONICAL)
        if not metrics["defined"]:
            raise ValueError("Undefined crossfit candidate ST-RAE")
        candidates.append({"setting": setting, "metrics": metrics, "prediction_sha256": _frame_hash(predicted)})
    selected = candidates[0] if mode == "fixed" else min(candidates, key=lambda c: c["metrics"]["macro_ST_RAE"])
    setting = selected["setting"]
    key = (setting["k"], setting["power"])
    query_kernel = tanimoto_kernel(qfeatures, features, block_size=int(cfg.get("kernel_block_size", 256)))
    transfers = _transfers(query_kernel, residuals, observed, np.ones(len(ids), dtype=bool), qids, ids,
                           qparents, parents, [key])[key]
    result = query.copy()
    result[CANONICAL] = query[CANONICAL].to_numpy(float) + setting["blend"] * transfers["correction"]
    if not np.isfinite(result[CANONICAL].to_numpy(float)).all():
        raise ValueError("Nonfinite corrected query predictions")
    metadata = {"protocol": protocol, "protocol_sha256": hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest(),
                "selected_setting": setting, "selection_used_development_scores": mode == "crossfit",
                "development_baseline_metrics": baseline_score, "development_candidates": candidates,
                "development_selected_diagnostics": _diagnostic_summary(crossfit[key]),
                "query_diagnostics": _diagnostic_summary(transfers), "fold_anchor_counts": fold_counts,
                "query_row_diagnostics": {"Molecule_Name": qids, "target_order": list(CANONICAL),
                    **{name: transfers[name].tolist() for name in ["nearest_similarity", "anchor_count", "effective_anchors", "correction"]}},
                "observed_anchor_counts": dict(zip(CANONICAL, observed.sum(axis=0).astype(int).tolist())),
                "nonzero_residual_counts": dict(zip(CANONICAL, ((residuals != 0) & observed).sum(axis=0).astype(int).tolist())),
                "training_features": feature_meta, "query_features": qfeature_meta,
                "source_prediction_hashes": {"oof": _frame_hash(base), "query": _frame_hash(query)},
                "truth_sha256": _frame_hash(truth[["Molecule_Name"] + required]),
                "folds_sha256": hashlib.sha256(json.dumps({i: str(mapping[i]) for i in ids}, sort_keys=True).encode()).hexdigest(),
                "parent_keys_sha256": None if parents is None else hashlib.sha256(json.dumps({i: parent_map[i] for i in ids + qids}, sort_keys=True).encode()).hexdigest(),
                "prediction_sha256": _frame_hash(result), "query_labels_used": False, "query_moments_used": False,
                "allowed_fit_ids_checked": cfg.get("allowed_fit_ids") is not None,
                "forbidden_fit_ids_checked": "forbidden_fit_ids" in cfg,
                "caveats": ["MolPAIR-inspired local residual control, not a reproduction of its learned pair model.",
                    "Scaffold development folds and analogue-enriched outer cohorts can have different neighbor similarity/coverage.",
                    "Base OOF provenance is caller-owned; neural OOF epoch selection may have used the same inner validation labels.",
                    "Cross-fitting this correction is not fully nested retraining of its base model; selected development score is not an independent performance estimate.",
                    "Single-fold OOF residuals and fold-bagged query predictions can differ in variance; no query-distribution adjustment is learned."]}
    return result, metadata


fit_correction = fit_neighbor_correction
