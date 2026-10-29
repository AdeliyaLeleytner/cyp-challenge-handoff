"""Fit the frozen FinalTDI specification using local challenge CSVs only.

Example: .venv/bin/python scripts/train_final_tdi.py --data-dir /path/to/challenge_csv
No architecture, feature, weight, seed or threshold-policy search is performed.
"""

import argparse
import hashlib
import importlib.metadata
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
from rdkit import Chem
from sklearn.metrics import average_precision_score, matthews_corrcoef, roc_auc_score
from threadpoolctl import threadpool_limits
from training.tdi_features import extract_physicochemical_basis

from evaluation.dataset import DATASET_FILES
from models.final_tdi import ENDPOINTS, STRUCTURE_WEIGHTS, FinalTDI, compound_folds
from training.data import ExperimentDataset, align_feature_frame
from validation.tdi_validation import validate_tdi_submission

LOG = logging.getLogger("final_tdi")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/challenge")
    parser.add_argument("--feat-dir", type=Path, default=ROOT / "data/tdi/features")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT
        / "results/tdi_runs"
        / ("final_tdi_" + datetime.now(UTC).strftime("%Y%m%d_%H%M%S")),
    )
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(out / "run.log")],
    )
    write_json(
        out / "status.json",
        {"state": "loading", "completed_folds": 0, "total_folds": 15},
    )
    try:
        tables = {
            name: pd.read_csv(args.data_dir / filename)
            for name, filename in DATASET_FILES.items()
        }
        dataset = ExperimentDataset(tables=tables, feat_dir=args.feat_dir)
        identities = dataset.molecules.canonical_smiles.to_numpy(str)
        for identity in identities:
            if Chem.MolFromSmiles(identity) is None:
                raise ValueError(f"Invalid structure: {identity}")
        fingerprint_path = dataset.feat_dir / "fingerprints.parquet"
        frame = align_feature_frame(
            dataset.molecules, pd.read_parquet(fingerprint_path)
        )
        columns = [c for c in frame if c not in ("SMILES", "canonical_smiles")]
        if len(columns) != 4263:
            raise ValueError(
                "Frozen recipe requires exactly 4263 structural fingerprint columns"
            )
        descriptors = extract_physicochemical_basis(identities)
        structure = np.column_stack([frame[columns].to_numpy(np.float32), descriptors])
        responses = np.full((len(identities), 2), np.nan)
        # Rebuild from supplied raw screening measurements; do not trust a fitted/cache feature.
        for (row, enzyme), value in (
            dataset.tables["screen"]
            .groupby(["feature_row", "enzyme"])
            .log2fc_estimate.mean()
            .items()
        ):
            if enzyme in ("CYP2D6", "CYP3A4") and int(row) < dataset.n_train:
                responses[int(row), ("CYP2D6", "CYP3A4").index(enzyme)] = value
        feature_manifest = {
            "fingerprints": columns,
            "descriptors": [
                "mw",
                "logp",
                "tpsa",
                "hbd",
                "hba",
                "rotb",
                "arom_rings",
                "heavy",
                "fsp3",
                "charge",
                "basic_amine",
                "acid_center",
                "aromatic_heterocycle",
                "halogen_count",
                "lipophilic_density",
                "surface_roughness",
            ],
        }
        write_json(out / "features.json", feature_manifest)
        folds = dataset.molecules.iloc[: dataset.n_train][["canonical_smiles"]].copy()
        for repeat in range(3):
            folds[f"repeat_{repeat}"] = compound_folds(
                identities[: dataset.n_train], dataset.Y_tdi, repeat
            )
        folds.to_parquet(out / "folds.parquet", index=False)
        dataset.molecules.to_parquet(out / "registry.parquet", index=False)
        spec = ROOT / "MODELS.md"
        (out / spec.name).write_bytes(spec.read_bytes())
        sources = [
            Path(__file__),
            ROOT / "models/final_tdi.py",
            ROOT / "training/tdi_features.py",
            ROOT / "training/features.py",
            ROOT / "training/data.py",
            ROOT / "evaluation/dataset.py",
            spec,
        ]
        manifest = {
            "model": "FinalTDI-StructureScreen",
            "data_dir": str(args.data_dir.resolve()),
            "out_dir": str(out),
            "created_utc": datetime.now(UTC).isoformat(),
            "input_sha256": {f: sha(args.data_dir / f) for f in DATASET_FILES.values()},
            "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sources},
            "fingerprint_cache_sha256": sha(fingerprint_path),
            "features_sha256": sha(out / "features.json"),
            "folds_sha256": sha(out / "folds.parquet"),
            "registry_sha256": sha(out / "registry.parquet"),
            "software": {
                p: importlib.metadata.version(p)
                for p in (
                    "numpy",
                    "pandas",
                    "scikit-learn",
                    "lightgbm",
                    "rdkit",
                    "joblib",
                )
            },
            "repetitions": 3,
            "folds_per_repetition": 5,
            "partition_seeds": [0, 1, 2],
            "structure_weights": dict(zip(ENDPOINTS, STRUCTURE_WEIGHTS.tolist())),
            "threshold_policy": "exact OOF MCC partitions; highest threshold on exact ties",
            "score_role": "OOF threshold calibration, not independent performance assessment",
            "external_data_or_pretrained_models": False,
            "label_counts": {
                e: {
                    "observed": int(np.isfinite(dataset.Y_tdi[:, c]).sum()),
                    "positive": int(np.nansum(dataset.Y_tdi[:, c])),
                }
                for c, e in enumerate(ENDPOINTS)
            },
        }
        write_json(out / "run_manifest.json", manifest)
        LOG.info(
            "Frozen model: %s training compounds, %s blind queries, %s",
            dataset.n_train,
            dataset.n_test,
            manifest["label_counts"],
        )

        def progress(model, record):
            write_json(
                out / "status.json",
                {
                    "state": "running",
                    "completed_folds": len(model.models_),
                    "total_folds": 15,
                    "last_repeat": record["repeat"],
                    "last_fold": record["fold"],
                },
            )

        with threadpool_limits(limits=1):
            model = FinalTDI().fit(
                structure,
                descriptors,
                dataset.Y_tdi,
                responses,
                identities,
                dataset.n_train,
                out / "models",
                progress=progress,
            )
        joblib.dump(model, out / "final_tdi.joblib")
        oof = dataset.molecules.iloc[: dataset.n_train][["canonical_smiles"]].copy()
        test = dataset.test_table[["SMILES", "Molecule_Name"]].copy()
        query_positions = dataset.test_rows - dataset.n_train
        summary = {"score_role": manifest["score_role"], "endpoint_metrics": {}}
        for column, endpoint in enumerate(ENDPOINTS):
            observed = np.isfinite(dataset.Y_tdi[:, column])
            y = dataset.Y_tdi[observed, column].astype(int)
            scores = model.oof_scores_[observed, column]
            threshold = model.thresholds_[column]
            for branch, name in enumerate(("structure", "descriptor_screen")):
                oof[f"{endpoint}__{name}"] = model.oof_components_[:, column, branch]
                test[f"{endpoint}__{name}"] = model.test_components_[
                    query_positions, column, branch
                ]
            oof[f"{endpoint}__truth"] = dataset.Y_tdi[:, column]
            oof[endpoint] = model.oof_scores_[:, column]
            oof[f"{endpoint}__call"] = model.oof_scores_[:, column] >= threshold
            test[endpoint] = model.test_scores_[query_positions, column]
            summary["endpoint_metrics"][endpoint] = {
                "threshold": float(threshold),
                "calibration_mcc": float(matthews_corrcoef(y, scores >= threshold)),
                "oof_auc": float(roc_auc_score(y, scores)),
                "oof_average_precision": float(average_precision_score(y, scores)),
                "test_positive_calls": int((test[endpoint] >= threshold).sum()),
            }
        oof.to_parquet(out / "classification_oof_components.parquet", index=False)
        test.to_parquet(out / "classification_test_components.parquet", index=False)
        submission = test[["SMILES", "Molecule_Name"]].copy()
        for column, endpoint in enumerate(ENDPOINTS):
            submission[endpoint] = test[endpoint] >= model.thresholds_[column]
        submission.to_parquet(out / "classification_submission.parquet", index=False)
        submission.to_csv(out / "classification_submission.csv", index=False)
        valid, errors = validate_tdi_submission(
            out / "classification_submission.parquet",
            expected_ids=set(dataset.test_table.Molecule_Name),
        )
        summary.update(
            {
                "calibration_macro_mcc": float(
                    np.mean(
                        [
                            m["calibration_mcc"]
                            for m in summary["endpoint_metrics"].values()
                        ]
                    )
                ),
                "submission_valid": valid,
                "validation_errors": errors,
            }
        )
        write_json(
            out / "thresholds.json", dict(zip(ENDPOINTS, model.thresholds_.tolist()))
        )
        write_json(out / "summary.json", summary)
        write_json(
            out / "status.json",
            {
                "state": "complete" if valid else "validation_failed",
                "completed_folds": 15,
                "total_folds": 15,
                "summary": summary,
            },
        )
        LOG.info("Finished: %s", summary)
        if not valid:
            raise ValueError(f"Submission validation failed: {errors}")
    except Exception as exc:
        state = json.loads((out / "status.json").read_text())
        state.update({"state": "failed", "error": repr(exc)})
        write_json(out / "status.json", state)
        LOG.exception("Final TDI run failed")
        raise


if __name__ == "__main__":
    main()
