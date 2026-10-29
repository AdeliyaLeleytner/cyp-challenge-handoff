"""Development-OOF-only interval-aware convex stacking, with a frozen model list.

Default protocol (version1, fixed before scores): compare flat mean against a
simplex+intercept LP with L1 shrinkage [0, .01, .1, 1] toward uniform weights.
Choose one configuration by cross-fitted development macro ST-RAE; refit that
configuration on all development OOF predictions and apply it to query rows.
The caller owns base-model training, outer gates, and any optional reference
average supplied as one explicitly named, complete four-target model.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

import numpy as np
import pandas as pd

from .evaluation import score
from .reference import CANONICAL

PROTOCOL_VERSION = 1
DEFAULT_L1_GRID = (0.0, 0.01, 0.1, 1.0)


def _ids(frame, name):
    if "Molecule_Name" not in frame or frame.Molecule_Name.isna().any():
        raise ValueError(f"{name} needs non-null Molecule_Name")
    ids = frame.Molecule_Name.astype(str).tolist()
    if len(ids) != len(set(ids)):
        raise ValueError(f"{name} contains duplicate molecule IDs")
    return ids


def _hash_frame(frame):
    return hashlib.sha256(frame.to_csv(index=False, float_format="%.17g").encode()).hexdigest()


def _prediction_array(frame, ids, targets, name):
    actual = _ids(frame, name)
    if set(actual) != set(ids):
        raise ValueError(f"{name} ID set differs; no silent dropping or subsetting")
    missing = set(targets) - set(frame)
    if missing:
        raise ValueError(f"{name} lacks required targets: {sorted(missing)}")
    aligned = frame.assign(Molecule_Name=actual).set_index("Molecule_Name").loc[ids, targets]
    values = aligned.to_numpy(float)
    if not np.isfinite(values).all():
        raise ValueError(f"{name} has nonfinite predictions, including possibly unlabelled rows")
    canonical = aligned.reset_index()
    return values, _hash_frame(canonical)


def _fit_target(predictions, low, high, prior, strength, *, flat=False):
    """min mean interval distance + lambda*||w-prior||1, w>=0, sum(w)=1."""
    from scipy.optimize import linprog
    from scipy.sparse import csr_matrix, eye, hstack, vstack

    n, m = predictions.shape
    if n == 0:
        raise ValueError("A fitting partition has no observed labels for a required target")
    if flat:
        weights, intercept = np.full(m, 1.0 / m), 0.0
        solver = {"method": "flat_mean", "status": 0}
    else:
        # Variables are [w(M), intercept(1), errors(N), |w-prior|(M)].
        design = csr_matrix(np.column_stack([predictions, np.ones(n)]))
        zeros_nm = csr_matrix((n, m))
        identity_m = eye(m, format="csr")
        zeros_mrest = csr_matrix((m, 1 + n))
        constraints = vstack([
            hstack([-design, -eye(n), zeros_nm]),
            hstack([design, -eye(n), zeros_nm]),
            hstack([identity_m, zeros_mrest, -identity_m]),
            hstack([-identity_m, zeros_mrest, -identity_m]),
        ], format="csr")
        objective = np.r_[np.zeros(m + 1), np.full(n, 1.0 / n), np.full(m, strength)]
        equality = csr_matrix(np.r_[np.ones(m), np.zeros(1 + n + m)].reshape(1, -1))
        result = linprog(objective, A_ub=constraints, b_ub=np.r_[-low, high, prior, -prior],
                         A_eq=equality, b_eq=[1.0],
                         bounds=[(0.0, 1.0)] * m + [(None, None)] + [(0.0, None)] * (n + m),
                         method="highs")
        if not result.success:
            raise RuntimeError(f"Stacking LP failed: {result.message}")
        weights, intercept = result.x[:m], float(result.x[m])
        if not np.isfinite(weights).all() or not np.isfinite(intercept):
            raise RuntimeError("Stacking LP returned nonfinite coefficients")
        if np.min(weights) < -1e-7 or abs(weights.sum() - 1) > 1e-7:
            raise RuntimeError("Stacking LP violated simplex constraints")
        solver = {"method": "scipy.optimize.linprog/highs", "status": int(result.status),
                  "objective": float(result.fun), "iterations": int(result.nit)}
    fitted = predictions @ weights + intercept
    errors = np.maximum(low - fitted, 0.0) + np.maximum(fitted - high, 0.0)
    return {"weights": weights.tolist(), "intercept": intercept, "n_observed": n,
            "fit_interval_mae": float(errors.mean()),
            "l1_distance_to_prior": float(np.abs(weights - prior).sum()), "solver": solver}


def _fit_all(values, low, high, observed, indices, targets, prior, candidate):
    parameters = {}
    for j, target in enumerate(targets):
        use = indices & observed[:, j]
        parameters[target] = _fit_target(values[use, j, :], low[use, j], high[use, j],
                                         prior, candidate.get("l1_strength", 0.0),
                                         flat=candidate["kind"] == "flat_mean")
    return parameters


def _apply(values, parameters, targets):
    result = np.column_stack([values[:, j, :] @ np.asarray(parameters[t]["weights"])
                              + parameters[t]["intercept"] for j, t in enumerate(targets)])
    if not np.isfinite(result).all():
        raise RuntimeError("Nonfinite stacked predictions")
    return result


def fit_stack(truth, oof_by_model, query_by_model, development_folds, config):
    """Return (query_predictions, metadata); never read query labels or fit query moments.

    Required config: model_names, a fixed ordered family list. Optional keys:
    l1_grid (default [0,.01,.1,1]), reference_model (one listed model, making the
    prior its simplex vertex), allowed_fit_ids, forbidden_fit_ids. An optional
    targets value must equal the canonical four-target order. Ridge is not
    silently substituted: this LP supports L1 regularization only.

    Missing molecules/models/targets and nonfinite prediction cells raise.
    truth may have unknown target labels; these remain masked, never imputed.
    """
    cfg = dict(config)
    targets = list(CANONICAL)
    if "targets" in cfg and list(cfg["targets"]) != targets:
        raise ValueError("Stacking requires all four canonical targets in canonical order")
    if cfg.get("regularization", "l1") != "l1":
        raise ValueError("Only explicit L1 shrinkage is implemented by this LP")
    names = cfg.get("model_names")
    if not isinstance(names, (list, tuple)) or not names or any(not isinstance(n, str) or not n for n in names):
        raise ValueError("Supply a fixed nonempty config.model_names list before scoring")
    names = list(names)
    if len(names) != len(set(names)):
        raise ValueError("Repeated model names are not allowed")
    for label, mapping in [("OOF", oof_by_model), ("query", query_by_model)]:
        if not isinstance(mapping, Mapping) or set(mapping) != set(names):
            raise ValueError(f"{label} model names must exactly equal the frozen model list")
    ids = _ids(truth, "development truth")
    query_ids = _ids(query_by_model[names[0]], "query predictions")
    if not ids or not query_ids:
        raise ValueError("Development and query sets must be nonempty")
    if set(ids) & set(query_ids):
        raise ValueError("Development truth/query IDs overlap")
    if cfg.get("allowed_fit_ids") is not None and not set(ids) <= set(map(str, cfg["allowed_fit_ids"])):
        raise ValueError("Development labels include IDs outside the allowed cohort")
    if set(ids) & set(map(str, cfg.get("forbidden_fit_ids", []))):
        raise ValueError("Development labels include forbidden gate/test IDs")
    required = targets + [t + suffix for t in targets for suffix in ["_conf_low", "_conf_high"]]
    if not set(required) <= set(truth):
        raise ValueError("Development truth lacks required primary targets or confidence bounds")
    canonical_truth = truth.assign(Molecule_Name=ids).reset_index(drop=True)
    central = canonical_truth[targets].to_numpy(float)
    if np.isinf(central).any():
        raise ValueError("Infinite central truth labels")
    observed = np.isfinite(central)
    low = canonical_truth[[t + "_conf_low" for t in targets]].to_numpy(float)
    high = canonical_truth[[t + "_conf_high" for t in targets]].to_numpy(float)
    if np.any(observed & (~np.isfinite(low) | ~np.isfinite(high) | (low > high))):
        raise ValueError("Observed development labels have invalid confidence bounds")
    raw_fold_mapping = dict(development_folds)
    fold_mapping = {str(k): v for k, v in raw_fold_mapping.items()}
    if len(fold_mapping) != len(raw_fold_mapping):
        raise ValueError("Development fold IDs collide after string normalization")
    if set(fold_mapping) != set(ids):
        raise ValueError("Development fold IDs must exactly cover development truth")
    folds = pd.Series([fold_mapping[i] for i in ids])
    if folds.isna().any() or folds.nunique() < 2:
        raise ValueError("At least two nonmissing development folds are required")
    unique_folds = list(pd.unique(folds))
    arrays, query_arrays, hashes = [], [], {}
    for name in names:
        x, h = _prediction_array(oof_by_model[name], ids, targets, name + " OOF")
        q, qh = _prediction_array(query_by_model[name], query_ids, targets, name + " query")
        arrays.append(x)
        query_arrays.append(q)
        hashes[name] = {"oof_sha256": h, "query_sha256": qh}
    values, queries = np.stack(arrays, axis=-1), np.stack(query_arrays, axis=-1)
    strengths = [float(x) for x in cfg.get("l1_grid", DEFAULT_L1_GRID)]
    if not strengths or not np.isfinite(strengths).all() or min(strengths) < 0 or len(strengths) != len(set(strengths)):
        raise ValueError("l1_grid must contain distinct finite nonnegative strengths")
    prior = np.full(len(names), 1.0 / len(names))
    reference = cfg.get("reference_model")
    if reference is not None:
        if reference not in names:
            raise ValueError("reference_model must be in the fixed model list")
        prior[:] = 0.0
        prior[names.index(reference)] = 1.0
    candidates = [{"name": "flat_mean", "kind": "flat_mean"}] + [
        {"name": "simplex_l1_" + format(v, ".17g"), "kind": "simplex_intercept", "l1_strength": v}
        for v in strengths]
    # Record the complete protocol before computing any development candidate score.
    protocol = {"version": PROTOCOL_VERSION, "model_names": names, "targets": targets,
                "candidates": candidates, "prior_weights": dict(zip(names, prior.tolist())),
                "selection": "Minimum pooled cross-fitted development macro ST-RAE across all four targets",
                "tie_order": [c["name"] for c in candidates],
                "regularizer": "L1 distance from fixed prior; objective = mean interval distance + lambda*L1",
                "intercept": "Unconstrained per target for LP; fixed zero for flat mean"}
    cv = {}
    for candidate in candidates:
        crossfit = np.empty((len(ids), len(targets)), dtype=float)
        fold_parameters = []
        for fold in unique_folds:
            val = folds.eq(fold).to_numpy()
            parameters = _fit_all(values, low, high, observed, ~val, targets, prior, candidate)
            crossfit[val] = _apply(values[val], parameters, targets)
            fold_parameters.append({"fold": str(fold), "train_rows": int((~val).sum()),
                                    "validation_rows": int(val.sum()), "per_target": parameters})
        pred = pd.DataFrame(crossfit, columns=targets)
        pred.insert(0, "Molecule_Name", ids)
        metric = score(canonical_truth, pred, targets=targets)
        if not metric["defined"]:
            raise ValueError("Undefined cross-fitted development ST-RAE; no candidate can be selected")
        cv[candidate["name"]] = {"metrics": metric, "prediction_sha256": _hash_frame(pred),
                                   "fold_parameters": fold_parameters}
    selected = min(candidates, key=lambda c: cv[c["name"]]["metrics"]["macro_ST_RAE"])
    fitted = _fit_all(values, low, high, observed, np.ones(len(ids), dtype=bool), targets, prior, selected)
    result = pd.DataFrame(_apply(queries, fitted, targets), columns=targets)
    result.insert(0, "Molecule_Name", query_ids)
    weights = {t: {"weights": dict(zip(names, fitted[t]["weights"])),
                   **{k: v for k, v in fitted[t].items() if k != "weights"}} for t in targets}
    metadata = {"protocol": protocol, "protocol_sha256": hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest(),
                "selected_candidate": selected["name"], "per_target": weights,
                "development_crossfit": cv, "source_prediction_hashes": hashes,
                "truth_sha256": _hash_frame(canonical_truth[["Molecule_Name"] + required]),
                "development_fold_sha256": hashlib.sha256(json.dumps({i: str(fold_mapping[i]) for i in ids}, sort_keys=True).encode()).hexdigest(),
                "n_development": len(ids), "n_query": len(query_ids),
                "allowed_fit_ids_checked": cfg.get("allowed_fit_ids") is not None,
                "forbidden_fit_ids_checked": "forbidden_fit_ids" in cfg,
                "query_labels_used": False, "query_moments_used": False,
                "query_prediction_sha256": _hash_frame(result),
                "caveats": [
                    "Caller must establish base OOF provenance. This module cannot undo base-model epoch selection on the same OOF labels.",
                    "Development method-selection score is selected among candidates and is not an independent performance estimate; use the frozen outer gate.",
                    "Cross-fitting only the stack is not fully nested retraining of base models; base OOF fits can share other development-fold labels.",
                    "Single-fold base OOF predictions and fold-bagged outer predictions may differ in variance. No query-moment correction is fitted.",
                    "A supplied reference average may duplicate component models; fixed-family membership and prior must be chosen before scoring.",
                ]}
    return result, metadata
