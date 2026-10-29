"""Small, explicit TDI learners; the orchestrator owns folds and model selection.

Jeremy reference: jeremycheminf/openadmet_scripts d3a5549e0c98167435cbf8f5115c68a9a184ed7a.
Native predictions use estimator.predict, not a reconstructed probability cutoff.
A caller can compare hard voting and soft ensembling from the SAME fitted models.
No validation labels are used by this module, including for stopping or thresholds.
"""
from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

JEREMY_REVISION = "d3a5549e0c98167435cbf8f5115c68a9a184ed7a"
JEREMY_LGBM_PARAMS = dict(
    n_estimators=500, learning_rate=0.05, num_leaves=31,
    subsample=0.8, colsample_bytree=0.8, verbose=-1,
    class_weight="balanced",
)
# Fixed complementary candidates, not a hidden hyperparameter search.
PRESETS = {
    "jeremy_lgbm": dict(JEREMY_LGBM_PARAMS),
    "jeremy_tabicl": dict(n_estimators=8, pca_components=200),
    "extra_trees": dict(n_estimators=500, max_features=0.5,
                        min_samples_leaf=2, class_weight="balanced"),
    "logistic": dict(C=1.0, class_weight="balanced", solver="lbfgs", max_iter=2000),
    "tanimoto_knn": dict(n_neighbors=10, weighting="similarity", fingerprint_width=2048),
    "hauser_lgbm": dict(n_estimators=200, learning_rate=0.03, max_depth=7,
                        num_leaves=63, min_child_samples=20, colsample_bytree=0.4,
                        subsample=1.0, subsample_freq=0, reg_alpha=0.0, reg_lambda=0.5),
}


def _rows(indices, n: int, label: str) -> np.ndarray:
    raw = np.asarray(indices)
    if raw.dtype == bool:
        if raw.shape != (n,):
            raise ValueError(f"{label} boolean mask must have length {n}")
        raw = np.flatnonzero(raw)
    if raw.ndim == 1 and raw.size == 0:
        raw = raw.astype(np.int64)
    if raw.ndim != 1 or not np.issubdtype(raw.dtype, np.integer):
        raise ValueError(f"{label} must be integer row indices or a boolean mask")
    rows = raw.astype(np.int64, copy=False)
    if np.any(rows < 0) or np.any(rows >= n) or len(np.unique(rows)) != len(rows):
        raise ValueError(f"{label} contains out-of-range or duplicate rows")
    return rows


def _hash_rows(rows: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(rows, dtype="<i8").tobytes()).hexdigest()


def make_pca_pipeline(n_rows: int, n_features: int, n_components: int = 200):
    """Jeremy's exact median/scaler/PCA transform; caller decides fitting rows."""
    from sklearn.decomposition import PCA
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("pca", PCA(n_components=min(n_components, n_rows, n_features), random_state=42)),
    ])


class TanimotoKNN:
    """Ten-neighbour similarity-weighted classification on binary Morgan bits.

    The fingerprint block alone is used (first fingerprint_width columns).
    Descriptor values are never included in a Tanimoto calculation. Query rows
    with no positive similarity receive the training class prior.
    """
    def __init__(self, n_neighbors=10, fingerprint_width=2048):
        self.n_neighbors = int(n_neighbors)
        self.fingerprint_width = int(fingerprint_width)

    def _bits(self, X):
        X = np.asarray(X)
        if X.ndim != 2 or X.shape[1] < self.fingerprint_width:
            raise ValueError("TanimotoKNN requires the declared binary fingerprint block")
        bits = X[:, :self.fingerprint_width]
        if not np.isfinite(bits).all() or not np.isin(bits, [0, 1]).all():
            raise ValueError("TanimotoKNN accepts binary bits, not count fingerprints/descriptors")
        return bits.astype(np.float32, copy=False)

    def fit(self, X, y):
        self.X_ = self._bits(X)
        self.y_ = np.asarray(y, dtype=float)
        self.sums_ = self.X_.sum(axis=1)
        self.prior_ = float(self.y_.mean())
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        bits = self._bits(X)
        result = np.empty(len(bits), dtype=float)
        k = min(self.n_neighbors, len(self.X_))
        for start in range(0, len(bits), 256):
            query = bits[start:start + 256]
            intersection = query @ self.X_.T
            union = query.sum(axis=1)[:, None] + self.sums_[None, :] - intersection
            sim = np.divide(intersection, union, out=np.zeros_like(intersection), where=union > 0)
            # Stable sorting makes boundary-neighbour ties deterministic by training row order.
            top = np.argsort(-sim, axis=1, kind="stable")[:, :k]
            weights = np.take_along_axis(sim, top, axis=1).astype(np.float64)
            den = weights.sum(axis=1)
            result[start:start + len(query)] = np.divide(
                (weights * self.y_[top]).sum(axis=1), den,
                out=np.full(len(query), self.prior_), where=den > 0,
            )
        return np.column_stack([1 - result, result])

    def predict(self, X):
        return self.predict_proba(X)[:, 1] >= 0.5


def make_classifier(name: str, *, seed: int = 42, device: str = "cpu", n_jobs: int = 1):
    """Build a fixed preset; no training or data access here."""
    if name == "jeremy_lgbm":
        from lightgbm import LGBMClassifier
        # Jeremy supplies subsample=.8 but no subsample_freq: retain that exact behavior.
        return LGBMClassifier(**JEREMY_LGBM_PARAMS, random_state=seed, n_jobs=n_jobs)
    if name == "jeremy_tabicl":
        from tabicl import TabICLClassifier
        from pathlib import Path
        pinned=Path('/workspace/cyp-tdi/tabicl-classifier.ckpt')
        kwargs={'model_path':str(pinned),'allow_auto_download':False} if pinned.exists() else {}
        return TabICLClassifier(n_estimators=8, device=device, random_state=seed, **kwargs)
    if name == "extra_trees":
        from sklearn.ensemble import ExtraTreesClassifier
        return ExtraTreesClassifier(**PRESETS[name], random_state=seed, n_jobs=n_jobs)
    if name == "logistic":
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        return Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("classifier", LogisticRegression(**PRESETS[name], random_state=seed)),
        ])
    if name == "tanimoto_knn":
        return TanimotoKNN(n_neighbors=10, fingerprint_width=2048)
    if name == "hauser_lgbm":
        from .hauser import structural_classifier
        return structural_classifier(seed)
    raise ValueError(f"Unknown learner {name!r}; choose one of {tuple(PRESETS)}")


def _outputs(model, features):
    if not len(features):
        return np.empty(0, dtype=float), np.empty(0, dtype=bool)
    classes = np.asarray(model.classes_)
    positive = np.flatnonzero(classes == 1)
    if len(positive) != 1:
        raise ValueError(f"Expected classifier classes 0 and 1, received {classes}")
    probability = np.asarray(model.predict_proba(features), dtype=float)[:, positive[0]]
    hard = np.asarray(model.predict(features)).reshape(-1).astype(bool)
    if (not np.isfinite(probability).all() or np.any(probability < 0)
            or np.any(probability > 1) or len(probability) != len(features)):
        raise ValueError("Classifier returned invalid probabilities")
    return probability, hard


def fit_predict(
    name: str, X, y, train_idx, valid_idx, X_query, *,
    seed: int = 42, device: str = "cpu", n_jobs: int = 1,
    pca_scope: str = "fold_local", pca_fit_idx=None,
    return_model: bool = False,
) -> dict[str, Any]:
    """Fit once and return probabilities AND native hard predictions.

    X/y retain the full row-aligned training pool; missing y is NaN. train_idx
    and valid_idx are global row indices; predictions cover ALL valid_idx,
    even when a validation label is missing. Only observed train labels fit a
    classifier. X_query contains features only, never assay labels.

    TabICL modes:
      fold_local: PCA fits train_idx (including their unlabelled rows).
      native_global: explicit pca_fit_idx must contain train_idx and valid_idx;
        it describes Jeremy's global TRAINING-pool transform. For an outer
        holdout, that outer holdout must instead be passed as X_query and must
        not be included in pca_fit_idx. The caller owns this outer boundary.
    No PCA is applied to other models. Fold-local logistic imputation/scaling
    is built into its estimator and fitted on observed train rows only.
    """
    X, X_query = np.asarray(X), np.asarray(X_query)
    y = np.asarray(y, dtype=float)
    if X.ndim != 2 or X_query.ndim != 2 or X.shape[1] != X_query.shape[1]:
        raise ValueError("X and X_query must be aligned two-dimensional feature matrices")
    if y.shape != (len(X),) or np.isinf(y).any():
        raise ValueError("y must have one finite binary or NaN label per X row")
    if not np.isin(y[np.isfinite(y)], [0, 1]).all():
        raise ValueError("Observed labels must be 0 or 1")
    train_idx, valid_idx = _rows(train_idx, len(X), "train_idx"), _rows(valid_idx, len(X), "valid_idx")
    if np.intersect1d(train_idx, valid_idx).size:
        raise ValueError("Training and validation rows overlap")
    observed = train_idx[np.isfinite(y[train_idx])]
    if len(np.unique(y[observed])) != 2:
        raise ValueError("Both classes must be present in observed training labels")
    metadata = dict(
        learner=name, seed=int(seed), device=device, n_jobs=int(n_jobs),
        n_train_pool=len(train_idx), n_train_observed=len(observed),
        n_train_positive=int(y[observed].sum()), n_valid=len(valid_idx), n_query=len(X_query),
        feature_width=X.shape[1], train_rows_sha256=_hash_rows(train_idx),
        observed_train_rows_sha256=_hash_rows(observed), valid_rows_sha256=_hash_rows(valid_idx),
        pca_scope="none", preset=PRESETS.get(name),
    )
    transform = None
    fit_X, val_X, query_X = X[observed], X[valid_idx], X_query
    if name == "jeremy_tabicl":
        if pca_scope == "fold_local":
            if pca_fit_idx is not None:
                raise ValueError("fold_local PCA takes train_idx automatically; omit pca_fit_idx")
            prep_rows = train_idx
        elif pca_scope == "native_global":
            if pca_fit_idx is None:
                raise ValueError("native_global PCA requires explicit allowed training-pool pca_fit_idx")
            prep_rows = _rows(pca_fit_idx, len(X), "pca_fit_idx")
            if not np.isin(np.r_[train_idx, valid_idx], prep_rows).all():
                raise ValueError("Native global PCA pool must include inner train and validation rows")
        else:
            raise ValueError("pca_scope must be fold_local or native_global")
        if not len(prep_rows):
            raise ValueError("Empty PCA fitting pool")
        transform = make_pca_pipeline(len(prep_rows), X.shape[1])
        # Exact native path uses fit_transform for fitted rows, cast to float32.
        transformed_pool = transform.fit_transform(X[prep_rows]).astype(np.float32)
        mapping = np.full(len(X), -1, dtype=int)
        mapping[prep_rows] = np.arange(len(prep_rows))
        fit_X = transformed_pool[mapping[observed]]
        if pca_scope == "native_global":
            val_X = transformed_pool[mapping[valid_idx]]
        else:
            val_X = transform.transform(X[valid_idx]).astype(np.float32) if len(valid_idx) else np.empty((0, transformed_pool.shape[1]), dtype=np.float32)
        query_X = transform.transform(X_query).astype(np.float32) if len(X_query) else np.empty((0, transformed_pool.shape[1]), dtype=np.float32)
        metadata.update(pca_scope=pca_scope, pca_rows_sha256=_hash_rows(prep_rows),
                        pca_fit_rows=len(prep_rows), pca_components=transformed_pool.shape[1])
    if name == "hauser_lgbm":
        metadata["feature_fidelity"] = (
            "4279_columns_supplied_caller_must_verify_native_order"
            if X.shape[1] == 4279 else "learner_parameters_only_not_native_Hauser_features"
        )
        metadata["n_jobs"] = 1  # Author explicitly fixes deterministic one-thread fitting.
    model = make_classifier(name, seed=seed, device=device, n_jobs=n_jobs)
    model.fit(fit_X, y[observed].astype(int))
    valid_proba, valid_hard = _outputs(model, val_X)
    query_proba, query_hard = _outputs(model, query_X)
    result = dict(valid_proba=valid_proba, query_proba=query_proba,
                  valid_hard=valid_hard, query_hard=query_hard, metadata=metadata)
    if return_model:
        result.update(model=model, transform=transform)
    return result
