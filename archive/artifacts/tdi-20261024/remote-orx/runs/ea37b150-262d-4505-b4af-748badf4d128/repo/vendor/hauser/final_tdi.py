"""Frozen FinalTDI-StructureScreen recipe; see MODELS.md."""

import logging
from pathlib import Path

import joblib
import numpy as np
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import KFold

LOG = logging.getLogger(__name__)
ENDPOINTS = ("CYP2D6_is_TDI", "CYP3A4_is_TDI")
STRUCTURE_WEIGHTS = np.array([0.95, 0.60])


def compound_folds(identities, labels, seed, n_splits=5):
    """Balance joint observed/negative/positive patterns, grouping duplicates."""
    identities = np.asarray(identities, dtype=str)
    labels = np.asarray(labels, dtype=float)
    if labels.shape != (len(identities), 2):
        raise ValueError("Require two row-aligned binary label columns")
    if np.isinf(labels).any() or not np.isin(labels[np.isfinite(labels)], [0, 1]).all():
        raise ValueError("Labels must be binary or NaN")
    groups = np.unique(identities)
    if len(groups) < n_splits:
        raise ValueError("Too few compound groups")
    patterns = {}
    for identity in groups:
        rows = np.flatnonzero(identities == identity)
        pattern = []
        for column in range(2):
            observed = np.unique(
                labels[rows, column][np.isfinite(labels[rows, column])]
            )
            if len(observed) > 1:
                raise ValueError("Conflicting labels for an identical compound")
            pattern.append(int(observed[0]) if len(observed) else -1)
        patterns.setdefault(tuple(pattern), []).append((identity, rows))
    rng = np.random.default_rng(seed)
    sizes = np.zeros(n_splits, dtype=int)
    assignments = np.full(len(labels), -1, dtype=int)
    for pattern in sorted(patterns, key=lambda p: (-len(patterns[p]), p)):
        members = patterns[pattern]
        counts = np.zeros(n_splits, dtype=int)
        for member in rng.permutation(len(members)):
            _, rows = members[member]
            eligible = np.flatnonzero(counts == counts.min())
            eligible = eligible[sizes[eligible] == sizes[eligible].min()]
            fold = int(rng.choice(eligible))
            assignments[rows] = fold
            counts[fold] += len(rows)
            sizes[fold] += len(rows)
    return assignments


def fit_mcc_threshold(labels, scores):
    """Exact distinct-score partitions; highest threshold wins exact MCC ties."""
    labels, scores = np.asarray(labels), np.asarray(scores, dtype=float)
    if (
        labels.ndim != 1
        or labels.shape != scores.shape
        or not len(scores)
        or not np.isfinite(scores).all()
        or not np.isin(labels, [0, 1]).all()
    ):
        raise ValueError("Require finite scores and observed binary labels")
    order = np.argsort(scores, kind="stable")
    values, y = scores[order], labels[order].astype(int)
    ends = np.r_[np.flatnonzero(values[:-1] != values[1:]) + 1, len(y)]
    removed = np.r_[0, ends]
    positives = np.r_[0, np.cumsum(y)][removed]
    tp = y.sum() - positives
    fp = len(y) - removed - tp
    fn = positives
    tn = removed - positives
    denominator = np.sqrt((tp + fp).astype(float) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = np.divide(
        tp * tn - fp * fn,
        denominator,
        out=np.zeros(len(removed), dtype=float),
        where=denominator > 0,
    )
    thresholds = [np.nextafter(values[0], -np.inf)]
    for index in ends[:-1]:
        midpoint = values[index - 1] + (values[index] - values[index - 1]) / 2
        # Adjacent floats can have no representable midpoint; preserve the partition.
        thresholds.append(midpoint if midpoint > values[index - 1] else values[index])
    thresholds.append(np.nextafter(values[-1], np.inf))
    best = np.flatnonzero(mcc == mcc.max())[-1]
    return float(thresholds[best]), float(mcc[best])


def structural_classifier(seed):
    return LGBMClassifier(
        objective="binary",
        n_estimators=200,
        learning_rate=0.03,
        max_depth=7,
        num_leaves=63,
        min_child_samples=20,
        colsample_bytree=0.4,
        subsample=1.0,
        subsample_freq=0,
        reg_alpha=0.0,
        reg_lambda=0.5,
        random_state=seed,
        n_jobs=1,
        deterministic=True,
        force_col_wise=True,
        verbosity=-1,
    )


def screen_regressor(seed):
    return LGBMRegressor(
        objective="regression",
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=15,
        max_depth=-1,
        min_child_samples=20,
        colsample_bytree=0.5,
        subsample=1.0,
        subsample_freq=0,
        reg_alpha=0.0,
        reg_lambda=0.0,
        random_state=seed,
        n_jobs=1,
        deterministic=True,
        force_col_wise=True,
        verbosity=-1,
    )


def descriptor_classifier(seed):
    return HistGradientBoostingClassifier(
        loss="log_loss",
        max_iter=150,
        learning_rate=0.1,
        max_leaf_nodes=31,
        max_depth=None,
        min_samples_leaf=20,
        l2_regularization=0.0,
        max_bins=255,
        early_stopping=False,
        random_state=seed,
    )


def cross_fit_screen(
    descriptors, responses, identities, fit_rows, query_rows, repeat, fold
):
    """No query response is accessed; each fitting compound gets inner OOF features."""
    fit_rows = np.asarray(fit_rows, dtype=int)
    query_rows = np.asarray(query_rows, dtype=int)
    if np.intersect1d(fit_rows, query_rows).size:
        raise ValueError("Screen fitting and query rows overlap")
    if np.intersect1d(identities[fit_rows], identities[query_rows]).size:
        raise ValueError("Screen fitting and query identities overlap")
    groups = np.unique(identities[fit_rows])
    training_features = np.full((len(fit_rows), 2), np.nan)
    query_features = np.full((len(query_rows), 2), np.nan)
    retained = []
    for column in range(2):
        for inner, (_, held_groups) in enumerate(
            KFold(3, shuffle=True, random_state=100 * repeat + fold).split(groups)
        ):
            held = np.isin(identities[fit_rows], groups[held_groups])
            available = ~held & np.isfinite(responses[fit_rows, column])
            if not available.any():
                raise ValueError(
                    "No observed screen responses in inner fitting partition"
                )
            model = screen_regressor(1000 + 100 * repeat + 10 * fold + inner)
            model.fit(
                descriptors[fit_rows[available]], responses[fit_rows[available], column]
            )
            training_features[held, column] = model.predict(descriptors[fit_rows[held]])
        available = fit_rows[np.isfinite(responses[fit_rows, column])]
        model = screen_regressor(1000 + 100 * repeat + 10 * fold + 3)
        model.fit(descriptors[available], responses[available, column])
        query_features[:, column] = model.predict(descriptors[query_rows])
        retained.append(model)
    return training_features, query_features, retained


class FinalTDI:
    """Three repetitions of five folds, two branches and two endpoint thresholds."""

    def fit(
        self,
        structure,
        descriptors,
        labels,
        responses,
        identities,
        n_train,
        output_dir,
        progress=None,
    ):
        structure = np.asarray(structure, dtype=np.float32)
        descriptors = np.asarray(descriptors, dtype=np.float32)
        labels = np.asarray(labels, dtype=float)
        responses = np.asarray(responses, dtype=float)
        identities = np.asarray(identities, dtype=str)
        if (
            structure.shape != (len(identities), 4279)
            or descriptors.shape != (len(identities), 16)
            or responses.shape != (len(identities), 2)
            or labels.shape != (n_train, 2)
            or not np.isfinite(structure).all()
            or not np.isfinite(descriptors).all()
        ):
            raise ValueError(
                "Final model requires aligned 4279/16 feature matrices and two targets"
            )
        if np.intersect1d(identities[:n_train], identities[n_train:]).size:
            raise ValueError("Blind and training compounds overlap")
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        self.models_ = []
        self.folds_ = np.stack(
            [compound_folds(identities[:n_train], labels, r) for r in range(3)]
        )
        self.oof_components_ = np.zeros((n_train, 2, 2))
        self.test_components_ = np.zeros((len(identities) - n_train, 2, 2))
        for repeat in range(3):
            for fold in range(5):
                fitting = np.flatnonzero(self.folds_[repeat] != fold)
                held = np.flatnonzero(self.folds_[repeat] == fold)
                query = np.r_[held, np.arange(n_train, len(identities))]
                fit_screen, query_screen, auxiliary = cross_fit_screen(
                    descriptors, responses, identities, fitting, query, repeat, fold
                )
                record = {
                    "repeat": repeat,
                    "fold": fold,
                    "auxiliary": auxiliary,
                    "structure": [],
                    "descriptor": [],
                    "training_counts": [],
                }
                for column in range(2):
                    observed = np.isfinite(labels[fitting, column])
                    target = labels[fitting[observed], column].astype(int)
                    if len(np.unique(target)) != 2:
                        raise ValueError(
                            "Each classifier fitting partition must contain both classes"
                        )
                    structural = structural_classifier(100 * repeat + fold)
                    structural.fit(structure[fitting[observed]], target)
                    descriptor = descriptor_classifier(42 + 100 * repeat + fold)
                    descriptor.fit(
                        np.column_stack(
                            [
                                descriptors[fitting[observed]],
                                fit_screen[observed, column],
                            ]
                        ),
                        target,
                    )
                    predictions = np.column_stack(
                        [
                            structural.predict_proba(structure[query])[:, 1],
                            descriptor.predict_proba(
                                np.column_stack(
                                    [descriptors[query], query_screen[:, column]]
                                )
                            )[:, 1],
                        ]
                    )
                    self.oof_components_[held, column] += predictions[: len(held)] / 3
                    self.test_components_[:, column] += predictions[len(held) :] / 15
                    record["structure"].append(structural)
                    record["descriptor"].append(descriptor)
                    record["training_counts"].append(
                        {
                            "observed": int(observed.sum()),
                            "positive": int(target.sum()),
                            "negative": int((target == 0).sum()),
                        }
                    )
                self.models_.append(record)
                joblib.dump(record, out / f"repeat_{repeat}_fold_{fold}.joblib")
                LOG.info(
                    "Completed repeat %d/3 fold %d/5: %s",
                    repeat + 1,
                    fold + 1,
                    record["training_counts"],
                )
                if progress is not None:
                    progress(self, record)
        self.oof_scores_ = self.blend(self.oof_components_)
        self.test_scores_ = self.blend(self.test_components_)
        self.thresholds_ = np.array(
            [
                fit_mcc_threshold(
                    labels[np.isfinite(labels[:, c]), c],
                    self.oof_scores_[np.isfinite(labels[:, c]), c],
                )[0]
                for c in range(2)
            ]
        )
        return self

    @staticmethod
    def blend(components):
        return components[:, :, 0] * STRUCTURE_WEIGHTS + components[:, :, 1] * (
            1 - STRUCTURE_WEIGHTS
        )

    def predict_scores(self, structure, descriptors):
        """Inference on identity-aligned features; independent of query cohort composition."""
        structure, descriptors = np.asarray(structure), np.asarray(descriptors)
        if structure.shape != (len(descriptors), 4279) or descriptors.shape[1:] != (
            16,
        ):
            raise ValueError("Require saved structural and descriptor feature order")
        components = np.zeros((len(descriptors), 2, 2))
        for record in self.models_:
            for column in range(2):
                screen = record["auxiliary"][column].predict(descriptors)
                components[:, column, 0] += record["structure"][column].predict_proba(
                    structure
                )[:, 1]
                components[:, column, 1] += record["descriptor"][column].predict_proba(
                    np.column_stack([descriptors, screen])
                )[:, 1]
        return self.blend(components / len(self.models_))

    def predict(self, structure, descriptors):
        return self.predict_scores(structure, descriptors) >= self.thresholds_
