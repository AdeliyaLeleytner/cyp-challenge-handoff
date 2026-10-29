"""Unified dataset container and feature alignment for CYP challenge cross-validation.

Centralizes loading of raw challenge tables, compound registry indexing,
fold partitioning (random / Butina), target arrays, and multi-modal feature blocks.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from evaluation.config import DATASET_REVISION
from evaluation.cross_validation import make_folds
from evaluation.dataset import load_challenge_tables
from models.base import canonical_smiles

LOG = logging.getLogger("training_data")

ROOT = Path(__file__).resolve().parents[1]
CYPS = ("CYP1A2", "CYP2C9", "CYP2D6", "CYP3A4")


def align_feature_frame(registry: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    """Align a complete cache by chemical identity; row count alone is insufficient."""
    key = (
        "canonical_smiles"
        if "canonical_smiles" in frame and "canonical_smiles" in registry
        else "SMILES"
    )
    for table in (registry, frame):
        if key not in table or table[key].isna().any() or table[key].duplicated().any():
            raise ValueError(f"Feature tables require unique, nonmissing {key}")
    if set(registry[key]) != set(frame[key]):
        raise ValueError("Feature cache does not cover exactly the registry compounds")
    return frame.set_index(key).loc[registry[key]].reset_index()


def load_identity_npz(path: Path, registry: pd.DataFrame) -> np.ndarray:
    """Read numeric features only when their compound identities can be checked."""
    with np.load(path, allow_pickle=False) as data:
        if "canonical_smiles" not in data:
            raise ValueError(f"{path} lacks compound identities; regenerate the cache")
        values = data["features"].astype(np.float32)
        identities = data["canonical_smiles"].astype(str)
    if (
        values.ndim != 2
        or len(values) != len(identities)
        or not np.isfinite(values).all()
    ):
        raise ValueError(f"Invalid feature matrix in {path}")
    frame = pd.DataFrame(values)
    frame["canonical_smiles"] = identities
    return (
        align_feature_frame(registry, frame)
        .drop(columns="canonical_smiles")
        .to_numpy(dtype=np.float32)
    )


class ExperimentDataset:
    """Master dataset container for 5-fold cross-validation and blinded test evaluation.

    Parameters
    ----------
    split : str, default="random"
        Cross-validation scheme ('random' or 'butina').
    n_splits : int, default=5
        Number of cross-validation folds.
    revision : str, default=DATASET_REVISION
        Pinned Hugging Face dataset revision commit.
    feat_dir : Path | None, default=None
        Directory containing extracted feature parquets. Defaults to `data/gemini_features`.
    tables : dict[str, pd.DataFrame] | None, default=None
        Optional already loaded challenge tables, copied before registry alignment.
        Pass local CSV tables for offline training.
    """

    def __init__(
        self,
        split: str = "random",
        n_splits: int = 5,
        revision: str = DATASET_REVISION,
        feat_dir: Path | None = None,
        tables: dict[str, pd.DataFrame] | None = None,
    ):
        self.split = split
        self.n_splits = n_splits
        self.revision = revision
        self.feat_dir = feat_dir or (ROOT / "data" / "features")

        # 1. Load Challenge Raw Tables
        LOG.info("Loading challenge tables (revision=%s)...", revision[:8])
        self.tables = (
            load_challenge_tables(revision=revision)
            if tables is None
            else {name: table.copy() for name, table in tables.items()}
        )
        # Screening is optional for ordinary regression/classification runners.
        required_tables = {"regression", "classification", "test"}
        if not required_tables.issubset(self.tables):
            raise ValueError(
                f"Missing challenge tables: {sorted(required_tables - set(self.tables))}"
            )
        self.reg_truth = self.tables["regression"]
        self.tdi_truth = self.tables["classification"]
        self.test_table = self.tables["test"]

        # Ensure canonical SMILES
        for df in self.tables.values():
            if "canonical_smiles" not in df.columns:
                df["canonical_smiles"] = df["SMILES"].map(canonical_smiles)

        # 2. Master Molecule Registry
        mol_path = self.feat_dir / "molecules.parquet"
        if mol_path.exists():
            self.molecules = pd.read_parquet(mol_path)
        else:
            LOG.warning(
                "%s not found; building master molecule registry dynamically.", mol_path
            )
            train_smiles = (
                pd.concat(
                    [
                        self.tables[name][["SMILES", "canonical_smiles"]]
                        for name in ("regression", "classification", "screen")
                        if name in self.tables
                    ]
                )
                .drop_duplicates("canonical_smiles")
                .reset_index(drop=True)
            )

            test_smiles = (
                self.test_table[["SMILES", "canonical_smiles"]]
                .drop_duplicates("canonical_smiles")
                .reset_index(drop=True)
            )
            if test_smiles.canonical_smiles.isin(train_smiles.canonical_smiles).any():
                raise ValueError("Training and blinded test compounds overlap")
            self.molecules = pd.concat([train_smiles, test_smiles], ignore_index=True)

        self.n_molecules = len(self.molecules)
        test_identities = set(self.test_table.canonical_smiles)
        self.n_train = int(
            (~self.molecules.canonical_smiles.isin(test_identities)).sum()
        )
        if self.molecules.canonical_smiles.duplicated().any():
            raise ValueError("Molecule registry contains duplicate chemical identities")
        if set(self.molecules.iloc[self.n_train :].canonical_smiles) != test_identities:
            raise ValueError(
                "Registry must place every blinded test compound in its tail"
            )
        self.n_test = len(self.test_table)

        # Lookup mapping canonical_smiles -> feature_row index
        self.smiles_to_idx = dict(
            zip(self.molecules["canonical_smiles"], range(self.n_molecules))
        )

        for df in self.tables.values():
            if not df["canonical_smiles"].isin(self.smiles_to_idx).all():
                raise ValueError(
                    "Raw table contains compounds absent from the registry"
                )
            df["feature_row"] = (
                df["canonical_smiles"].map(self.smiles_to_idx).fillna(-1).astype(int)
            )

        self.train_rows = np.arange(self.n_train)
        # Exported predictions follow the raw test table, even when a cache's
        # test tail contains the same identities in a different order.
        self.test_rows = self.test_table.canonical_smiles.map(
            self.smiles_to_idx
        ).to_numpy(dtype=int)

        # 3. Format Pre-aligned Target Matrices
        self._build_target_matrices()

        # 4. Generate Folds (deterministic, seed 0)
        LOG.info("Generating %s folds...", split)
        train_smi = self.molecules.iloc[: self.n_train]["canonical_smiles"].tolist()
        self.folds = make_folds(
            train_smi, n_splits=n_splits, method=split, seed=0, y=self.Y_reg
        )

    def _build_target_matrices(self) -> None:
        """Construct dense aligned target matrices for the training population."""
        self.Y_reg = np.full((self.n_train, 4), np.nan, dtype=np.float32)
        self.Y_low = np.full((self.n_train, 4), np.nan, dtype=np.float32)
        self.Y_high = np.full((self.n_train, 4), np.nan, dtype=np.float32)

        reg_feat_rows = self.reg_truth["feature_row"].to_numpy()
        for c_idx, cyp in enumerate(CYPS):
            endpoint = f"{cyp}_pIC50_direct_inhibition"
            vals = pd.to_numeric(self.reg_truth[endpoint], errors="coerce").to_numpy(
                dtype=float
            )
            conf_low_col = f"{endpoint}_conf_low"
            if conf_low_col in self.reg_truth.columns:
                lows = pd.to_numeric(
                    self.reg_truth[conf_low_col], errors="coerce"
                ).to_numpy(dtype=float)
            else:
                lows = np.full(len(self.reg_truth), np.nan, dtype=np.float32)

            conf_high_col = f"{endpoint}_conf_high"
            if conf_high_col in self.reg_truth.columns:
                highs = pd.to_numeric(
                    self.reg_truth[conf_high_col], errors="coerce"
                ).to_numpy(dtype=float)
            else:
                highs = np.full(len(self.reg_truth), np.nan, dtype=np.float32)

            obs = (
                np.isfinite(vals)
                & (reg_feat_rows >= 0)
                & (reg_feat_rows < self.n_train)
            )
            valid_rows = reg_feat_rows[obs]
            self.Y_reg[valid_rows, c_idx] = vals[obs]
            self.Y_low[valid_rows, c_idx] = lows[obs]
            self.Y_high[valid_rows, c_idx] = highs[obs]

        # TDI Targets (CYP2D6, CYP3A4)
        self.Y_tdi = np.full((self.n_train, 2), np.nan, dtype=np.float32)
        tdi_feat_rows = self.tdi_truth["feature_row"].to_numpy()
        for t_idx, cyp in enumerate(["CYP2D6", "CYP3A4"]):
            endpoint = f"{cyp}_is_TDI"
            vals = pd.to_numeric(self.tdi_truth[endpoint], errors="coerce").to_numpy(
                dtype=float
            )
            obs = (
                np.isfinite(vals)
                & (tdi_feat_rows >= 0)
                & (tdi_feat_rows < self.n_train)
            )
            valid_rows = tdi_feat_rows[obs]
            self.Y_tdi[valid_rows, t_idx] = vals[obs]

    @property
    def train_smiles(self) -> list[str]:
        """SMILES list for the training set."""
        return self.molecules.iloc[: self.n_train]["SMILES"].tolist()

    @property
    def test_smiles(self) -> list[str]:
        """SMILES list for the blinded test set."""
        return self.test_table["SMILES"].tolist()

    def get_fold_compound_masks(self, fold: int) -> tuple[np.ndarray, np.ndarray]:
        """Return (train_compounds_mask, val_compounds_mask) for a given fold."""
        train_mask = self.folds[: self.n_train] != fold
        val_mask = self.folds[: self.n_train] == fold
        return train_mask, val_mask

    def load_embedding_matrix(self, path: Path | str) -> np.ndarray:
        """Load a SMILES-keyed embedding parquet aligned to the registry order."""
        frame = align_feature_frame(self.molecules, pd.read_parquet(path))
        names = [c for c in frame.columns if c not in ("SMILES", "canonical_smiles")]
        values = frame[names].to_numpy(dtype=np.float32)
        if not np.isfinite(values).all():
            raise ValueError(f"{path} does not cover every registry compound")
        return values

    def load_screening_responses(self) -> np.ndarray:
        """Load registry-aligned single-concentration log2fc responses, shape (N, 4)."""
        frame = align_feature_frame(
            self.molecules, pd.read_parquet(self.feat_dir / "screening_targets.parquet")
        )
        cols = [f"screen_log2fc_{cyp}" for cyp in CYPS]
        return frame[cols].to_numpy(dtype=np.float32)

    def load_screening_gate_labels(
        self,
        neg_threshold: float = -1.0,
        pos_threshold: float = 1.0,
    ) -> np.ndarray:
        """Convert single-concentration screen log2fc values to binary gate labels.

        Compounds below ``neg_threshold`` are confirmed inactive (label 0).
        Compounds above ``pos_threshold`` are flagged active (label 1).
        Compounds between the thresholds or absent from the screen get NaN (unknown).

        The result is intended for use as ``active_mask`` in
        ``TwoStagePotencyRegressor.fit()``, where NaN entries do not contribute to
        gate classifier training unless an observed pIC50 is also available.

        Parameters
        ----------
        neg_threshold : float, default=-1.0
            log2fc at or below which a compound is classified as a confirmed inactive.
            The existing convention in cross-fitted screening features is -1.0.
        pos_threshold : float, default=1.0
            log2fc at or above which a compound is treated as a screen positive.
            Between neg_threshold and pos_threshold the label is left as NaN.

        Returns
        -------
        np.ndarray of shape (N, 4), dtype float32
            Gate labels aligned to the molecule registry.  Values are 0.0, 1.0, or NaN.
        """
        responses = self.load_screening_responses()  # (N, 4), log2fc, NaN if unscreened
        labels = np.full_like(responses, np.nan)
        labels[responses <= neg_threshold] = 0.0
        labels[responses >= pos_threshold] = 1.0
        return labels.astype(np.float32)

    def split_features(self, X_all: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Split a registry-aligned matrix into (train, blinded-test) blocks in table order."""
        test_rows = self.test_table["feature_row"].to_numpy()
        if (test_rows < self.n_train).any():
            raise ValueError(
                "Blinded test compounds are missing from the registry tail"
            )
        return X_all[: self.n_train], X_all[test_rows]

    def load_feature_matrices(self) -> dict[str, np.ndarray]:
        """Load common precomputed feature representations from data/gemini_features/."""
        features: dict[str, np.ndarray] = {}

        fps_path = self.feat_dir / "fingerprints.parquet"
        if fps_path.exists():
            df = align_feature_frame(self.molecules, pd.read_parquet(fps_path))
            cols = [c for c in df.columns if c not in ("SMILES", "canonical_smiles")]
            features["fingerprints"] = df[cols].values.astype(np.float32)

        cb_mtr_path = self.feat_dir / "chemberta_mtr.parquet"
        if cb_mtr_path.exists():
            df = align_feature_frame(self.molecules, pd.read_parquet(cb_mtr_path))
            cols = [c for c in df.columns if c not in ("SMILES", "canonical_smiles")]
            features["chemberta_mtr"] = df[cols].values.astype(np.float32)

        cb_zinc_path = self.feat_dir / "chemberta_zinc.parquet"
        if cb_zinc_path.exists():
            df = align_feature_frame(self.molecules, pd.read_parquet(cb_zinc_path))
            cols = [c for c in df.columns if c not in ("SMILES", "canonical_smiles")]
            features["chemberta_zinc"] = df[cols].values.astype(np.float32)

        if "chemberta_mtr" in features and "fingerprints" in features:
            features["fused_mtr_fps"] = np.concatenate(
                [features["chemberta_mtr"], features["fingerprints"]], axis=1
            )

        screen_path = self.feat_dir / "screening_targets.parquet"
        if screen_path.exists():
            features["screening_targets"] = self.load_screening_responses()

        for name, filename in (
            ("mechanistic", "mechanistic_features.npz"),
            ("geometric_3d", "geometric_3d_features.npz"),
        ):
            path = self.feat_dir / filename
            if path.exists():
                try:
                    features[name] = load_identity_npz(path, self.molecules)
                except ValueError as error:
                    # Optional legacy caches must not poison unrelated experiments.
                    # Consumers requiring this block must regenerate or raise.
                    LOG.warning("Ignoring unverified optional cache: %s", error)

        return features
