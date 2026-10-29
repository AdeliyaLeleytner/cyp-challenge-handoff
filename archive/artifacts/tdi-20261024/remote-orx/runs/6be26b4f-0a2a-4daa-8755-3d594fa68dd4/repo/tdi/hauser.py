"""Hauser structural/screen learner parameters and safe nested-screen adapter.

Parameter/seed source: HauserGroup/spooky-cyp-challenge/models/final_tdi.py,
revision 06e1e1fcf7341333e4623ce353c65c6b4b6e71f3.
This adapter does not construct native fingerprints or choose folds/thresholds.
Caller must supply the exact 16-descriptor representation to claim native
feature fidelity, and all allowed training compounds (including screen-only
rows) to preserve the auxiliary fitting pool.
"""
from __future__ import annotations

import numpy as np

HAUSER_REVISION = "06e1e1fcf7341333e4623ce353c65c6b4b6e71f3"
STRUCTURE_WEIGHTS = {"CYP2D6": 0.95, "CYP3A4": 0.60}
NATIVE_THRESHOLDS = {"CYP2D6": 0.277519153001473, "CYP3A4": 0.3084748264872564}


def structural_classifier(seed=42):
    from lightgbm import LGBMClassifier
    return LGBMClassifier(
        objective="binary", n_estimators=200, learning_rate=0.03,
        max_depth=7, num_leaves=63, min_child_samples=20,
        colsample_bytree=0.4, subsample=1.0, subsample_freq=0,
        reg_alpha=0.0, reg_lambda=0.5, random_state=seed, n_jobs=1,
        deterministic=True, force_col_wise=True, verbosity=-1,
    )


def screen_regressor(seed=42):
    from lightgbm import LGBMRegressor
    return LGBMRegressor(
        objective="regression", n_estimators=200, learning_rate=0.05,
        num_leaves=15, max_depth=-1, min_child_samples=20,
        colsample_bytree=0.5, subsample=1.0, subsample_freq=0,
        reg_alpha=0.0, reg_lambda=0.0, random_state=seed, n_jobs=1,
        deterministic=True, force_col_wise=True, verbosity=-1,
    )


def descriptor_classifier(seed=42):
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(
        loss="log_loss", max_iter=150, learning_rate=0.1,
        max_leaf_nodes=31, max_depth=None, min_samples_leaf=20,
        l2_regularization=0.0, max_bins=255, early_stopping=False,
        random_state=seed,
    )


def fit_predict_screen(
    descriptors, y, responses, identities, train_idx, valid_idx,
    query_descriptors, query_identities, *, repeat=0, fold=0,
    return_model=False,
):
    """One endpoint/outer fold of native nested screen -> HGB procedure.

    descriptors: N x 16 structure-derived values. y/responses: length N with
    NaN for missing binary/same-CYP primary-screen outcomes. identities must
    group duplicates (or stricter caller-chosen grouping). Query structures
    must be disjoint from train and validation identities. train_idx includes
    screen-only compounds. All outer validation responses are ignored.

    Screen models fit three grouped inner folds; each training molecule gets
    an out-of-fold screen prediction. Full train screen regressor serves
    validation/query. Binary HGB fits ONLY observed train labels. Exact author
    seed schedule: inner KFold100*repeat+fold; screen1000+100*repeat+10*fold+inner;
    full-screen uses inner=3; HGB42+100*repeat+fold.
    Returns native class predictions at estimator's .5 operating point;
    caller owns the final blend/threshold selected without outer labels.
    """
    from sklearn.model_selection import KFold
    from .learners import _rows, _outputs, _hash_rows
    D = np.asarray(descriptors, dtype=np.float32)
    Q = np.asarray(query_descriptors, dtype=np.float32)
    y, responses = np.asarray(y, dtype=float), np.asarray(responses, dtype=float)
    identities, qids = np.asarray(identities, dtype=str), np.asarray(query_identities, dtype=str)
    n = len(D)
    if D.shape != (n, 16) or Q.shape != (len(qids), 16):
        raise ValueError("Native Hauser screen branch requires 16 aligned descriptors")
    if identities.shape != (n,) or y.shape != (n,) or responses.shape != (n,):
        raise ValueError("Identities/labels/responses must align with descriptor rows")
    if not np.isfinite(D).all() or not np.isfinite(Q).all():
        raise ValueError("Hauser descriptor matrices must be finite")
    if np.isinf(y).any() or np.isinf(responses).any() or not np.isin(y[np.isfinite(y)], [0, 1]).all():
        raise ValueError("Binary labels and screen responses must be finite or NaN")
    tr, va = _rows(train_idx, n, "train_idx"), _rows(valid_idx, n, "valid_idx")
    if np.intersect1d(tr, va).size or np.intersect1d(identities[tr], identities[va]).size:
        raise ValueError("Outer training/validation compound identities overlap")
    if np.intersect1d(identities[np.r_[tr, va]], qids).size:
        raise ValueError("Query identities overlap training or validation identities")
    observed = np.isfinite(y[tr])
    if len(np.unique(y[tr[observed]])) != 2:
        raise ValueError("Observed training labels must contain both classes")
    groups = np.unique(identities[tr])
    if len(groups) < 3:
        raise ValueError("Need at least three training identity groups for nested screen cross-fitting")
    crossfit = np.full(len(tr), np.nan)
    for inner, (_, held_groups) in enumerate(KFold(3, shuffle=True, random_state=100 * repeat + fold).split(groups)):
        held = np.isin(identities[tr], groups[held_groups])
        available = ~held & np.isfinite(responses[tr])
        if not available.any():
            raise ValueError("No observed screen responses in inner fitting partition")
        aux = screen_regressor(1000 + 100 * repeat + 10 * fold + inner)
        aux.fit(D[tr[available]], responses[tr[available]])
        crossfit[held] = aux.predict(D[tr[held]])
    if not np.isfinite(crossfit).all():
        raise ValueError("Incomplete nested screen predictions")
    available = tr[np.isfinite(responses[tr])]
    aux = screen_regressor(1000 + 100 * repeat + 10 * fold + 3)
    aux.fit(D[available], responses[available])
    model = descriptor_classifier(42 + 100 * repeat + fold)
    model.fit(np.column_stack([D[tr[observed]], crossfit[observed]]), y[tr[observed]].astype(int))
    va_screen = aux.predict(D[va]) if len(va) else np.empty(0)
    q_screen = aux.predict(Q) if len(Q) else np.empty(0)
    vp, vh = _outputs(model, np.column_stack([D[va], va_screen]))
    qp, qh = _outputs(model, np.column_stack([Q, q_screen]))
    result = dict(
        valid_proba=vp, query_proba=qp, valid_hard=vh, query_hard=qh,
        metadata=dict(learner="hauser_screen_hgb", revision=HAUSER_REVISION,
                      repeat=int(repeat), fold=int(fold), n_train_pool=len(tr),
                      n_train_observed=int(observed.sum()), n_screen_train=len(available),
                      n_inner_folds=3, train_rows_sha256=_hash_rows(tr),
                      valid_rows_sha256=_hash_rows(va), n_query=len(Q)),
    )
    if return_model:
        result.update(model=model, screen_model=aux)
    return result
