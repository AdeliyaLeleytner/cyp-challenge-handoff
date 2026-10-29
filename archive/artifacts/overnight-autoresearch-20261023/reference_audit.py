#!/usr/bin/env python3
"""Public source/data snapshot and reconstruction of briford's published 529 holdout.

Artifact preparation only: no model training, account use, submission, or private S3.
Run with the existing scientific Python environment. Defaults do not modify any input.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import platform
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, rdBase
from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator

REPO = "SuperCowPowers/workbench"
HISTORICAL = "8c72c7559471febaf0962fd551b4eaab8db3a136"
UNION18 = "971f6a7f24d86e59bab219347c3e14c006ae4e35"
CURRENT = "2c43e78e16978ea365244a003e95bf371fd72173"
OFFICIAL_SHA = "b8f79addd266fb6f9f4c222c5e4e73d926362328b6a8d2841871a54e46bd2278"
PUBLIC_SHA = "95576058689db7537458cde2615f8d72a84748cea9d4a2d73fe3c287f7c1cf0c"
HOLDOUT_ID_SHA = "f5b99359b0752a485b2123a87777fb09b7b3b8b8db60052e63d5468439de2a08"
ISOFORMS = ["CYP3A4", "CYP2C9", "CYP2D6", "CYP1A2"]
TARGETS = [f"{x}_pIC50_direct_inhibition" for x in ISOFORMS]
SOURCE_FILES = {
    HISTORICAL: [
        "src/workbench/training/splits.py",
        "src/workbench/utils/chem_utils/fingerprints.py",
        "src/workbench/training/chemprop_core.py",
        "src/workbench/training/validation.py",
        "src/workbench/model_scripts/chemprop/chemprop.template",
        "src/workbench/model_scripts/chemprop/requirements.txt",
        "src/workbench/utils/multi_task.py",
        "src/workbench/public_data.py",
        "ml_pipelines/OpenADMET/cyp/storage/cyp_chemprop_mt_aux.py",
        "ml_pipelines/OpenADMET/cyp/storage/cyp_chemprop_mt_all.py",
        "ml_pipelines/OpenADMET/cyp/storage/README.md",
        "ml_pipelines/OpenADMET/cyp/cyp_chemprop_mt_aux_100.py",
        "ml_pipelines/OpenADMET/cyp/cyp_chemprop_2d6.py",
        "ml_pipelines/OpenADMET/cyp/cyp_aux_features.py",
        "ml_pipelines/OpenADMET/cyp/cyp_union_features.py",
        "ml_pipelines/OpenADMET/cyp/scripts/cyp_ensemble_submit.py",
        "ml_pipelines/OpenADMET/cyp/scripts/cyp_recalibrate.py",
        "docs/blogs/cyp_challenge.md",
    ],
    UNION18: [
        "ml_pipelines/OpenADMET/cyp/cyp_chemprop_union.py",
        "ml_pipelines/OpenADMET/cyp/cyp_union_features.py",
    ],
    CURRENT: [
        "src/workbench/training/splits.py",
        "src/workbench/training/chemprop_core.py",
        "src/workbench/model_scripts/chemprop/chemprop.template",
        "src/workbench/core/artifacts/endpoint_core.py",
        "src/workbench/utils/chemprop_utils.py",
        "src/workbench/utils/multi_task.py",
        "src/workbench/core/transforms/features_to_model/features_to_model.py",
        "ml_pipelines/OpenADMET/cyp/scripts/cyp_ensemble_submit.py",
    ],
}
PUBLIC_ROOT = "https://workbench-public-data.s3.us-west-2.amazonaws.com/"
PUBLIC_FILES = {
    "inhibition.csv": "comp_chem/openadmet/cyp/training/inhibition.csv",
    "single_concentration.csv": "comp_chem/openadmet/cyp/training/single_concentration.csv",
    "tdi.csv": "comp_chem/openadmet/cyp/training/tdi.csv",
    "emax.csv": "comp_chem/openadmet/cyp/training/emax.csv",
    "chembl_all_isoforms.csv": "comp_chem/chembl/cyp_inhibition/all_isoforms.csv",
    "pubchem_all_isoforms.csv": "comp_chem/pubchem/cyp_inhibition/all_isoforms.csv",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data = path.read_bytes()
        return {"url": url, "sha256": sha(data), "bytes": len(data), "reused_local": True}
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                data = response.read()
                meta = {"url": url, "sha256": sha(data), "bytes": len(data),
                        "last_modified": response.headers.get("Last-Modified"),
                        "etag": response.headers.get("ETag"), "retrieved_unix": time.time()}
            tmp = path.with_name(path.name + ".partial")
            tmp.write_bytes(data)
            tmp.replace(path)
            return meta
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise AssertionError("unreachable")


def published_analog_holdout(df: pd.DataFrame) -> tuple[np.ndarray, set[int]]:
    """Literal algorithm from pinned splits.py/fingerprints.py; only names adapted."""
    generator = GetMorganGenerator(radius=2, fpSize=2048)
    fps, valid_indices = [], []
    for i, smiles in enumerate(df.SMILES):
        if not isinstance(smiles, str) or not smiles:
            continue
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            fps.append(generator.GetSparseCountFingerprint(mol))
            valid_indices.append(i)
    assert len(fps) == len(df), "Changed parsing support; do not silently change published cohort"
    fp_position = {row: i for i, row in enumerate(valid_indices)}
    hits_by_target = {}
    for target in TARGETS:
        values = pd.to_numeric(df[target], errors="coerce").to_numpy(dtype=float)
        ranked = [p for p in np.argsort(-values, kind="stable")
                  if not np.isnan(values[p]) and p in fp_position]
        hits_by_target[target] = ranked[:50]
    all_hits = {hit for hits in hits_by_target.values() for hit in hits}
    held = np.zeros(len(df), dtype=bool)
    for hits in hits_by_target.values():
        for hit in hits:
            sims = np.asarray(DataStructs.BulkTanimotoSimilarity(fps[fp_position[hit]], fps))
            picked = 0
            for pos in np.argsort(-sims, kind="stable"):
                if sims[pos] < 0.4 or picked >= 10:
                    break
                row = valid_indices[pos]
                if row in all_hits:
                    continue
                held[row] = True
                picked += 1
    return held, all_hits


def inverse_weights(df: pd.DataFrame) -> list[float]:
    # Historical source uses float32, current source changed to float64.
    counts = df[TARGETS].notna().sum().to_numpy(dtype=np.float32)
    inv = 1.0 / counts
    return (inv / inv.mean()).tolist()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "reference_audit")
    parser.add_argument("--official", type=Path, default=Path.home() / ".cache/cyp-inhibition/data/cyp-challenge-TRAIN_inhibition.csv")
    parser.add_argument("--structures", type=Path, default=Path.home() / ".cache/cyp-inhibition/data/all_molecule_structures.csv")
    parser.add_argument("--our-holdout", type=Path, default=Path("/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/chemeleon-baseline-20261023/split/holdout.csv"))
    parser.add_argument("--sources-only", action="store_true", help="Fetch source and public inhibition only, omit extra public data")
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"repository": REPO, "historical_head": HISTORICAL, "union18_commit": UNION18,
                "current_head": CURRENT, "sources": {}, "data": {}, "runtime": {
                    "python": platform.python_version(), "rdkit": rdBase.rdkitVersion,
                    "numpy": np.__version__, "pandas": pd.__version__}}
    for ref, paths in SOURCE_FILES.items():
        for relative in paths:
            location = out / "sources" / ref / relative
            manifest["sources"][str(location.relative_to(out))] = fetch(
                f"https://raw.githubusercontent.com/{REPO}/{ref}/{relative}", location)
    for filename, key in PUBLIC_FILES.items():
        if args.sources_only and filename != "inhibition.csv":
            continue
        manifest["data"][filename] = fetch(PUBLIC_ROOT + key, out / "public_data" / filename)
    official_raw = args.official.read_bytes()
    assert sha(official_raw) == OFFICIAL_SHA, "Official dataset revision changed"
    df = pd.read_csv(io.BytesIO(official_raw))
    public_raw = (out / "public_data/inhibition.csv").read_bytes()
    assert sha(public_raw) == PUBLIC_SHA, "Public reference data changed; review before replacing frozen source"
    public = pd.read_csv(io.BytesIO(public_raw))
    assert public.molecule_name.tolist() == df.Molecule_Name.tolist()
    assert public.smiles.tolist() == df.SMILES.tolist()
    columns_checked = {}
    for column in df.columns:
        if column in ["Molecule_Name", "SMILES"]:
            continue
        public_column = column.lower().replace("_conf_low", "_ci_lower").replace("_conf_high", "_ci_upper")
        a = df[column].to_numpy(float)
        b = public[public_column].to_numpy(float)
        assert np.array_equal(np.isnan(a), np.isnan(b)), column
        equal = bool(np.allclose(a, b, atol=0, rtol=0, equal_nan=True))
        columns_checked[column] = {"exact_numeric_equal": equal, "max_abs_difference": float(np.nanmax(np.abs(a-b)))}
        assert equal, (column, columns_checked[column])
    held, hits = published_analog_holdout(df)
    holdout_ids = df.loc[held, "Molecule_Name"].tolist()
    id_hash = sha("\n".join(holdout_ids).encode())
    assert held.sum() == 529 and id_hash == HOLDOUT_ID_SHA, (int(held.sum()), id_hash)
    structures_raw = args.structures.read_bytes()
    structures = pd.read_csv(io.BytesIO(structures_raw)).set_index("Molecule_Name")
    assert structures.index.is_unique
    keys = structures.loc[df.Molecule_Name, "parent_no_stereo"].to_numpy()
    assert pd.notna(keys).all()
    held_parents = set(keys[held])
    purged = (~held) & np.array([key in held_parents for key in keys])
    fit = (~held) & (~purged)
    assert set(keys[fit]).isdisjoint(held_parents)
    roles = df[["Molecule_Name", "SMILES"]].copy()
    roles["parent_no_stereo"] = keys
    roles["raw_role"] = np.where(held, "holdout", "train")
    roles["purged_role"] = np.where(held, "holdout", np.where(purged, "excluded_parent_match", "train"))
    roles["selected_hit"] = [i in hits for i in range(len(df))]
    roles.to_csv(out / "briford529_roles.csv", index=False)
    for name, mask in [("holdout_ids", held), ("raw_train_ids", ~held), ("purged_train_ids", fit), ("excluded_parent_matches", purged)]:
        roles.loc[mask].to_csv(out / f"{name}.csv", index=False)
    (out / "official_train.csv").write_bytes(official_raw)
    primary = inverse_weights(df)
    mean_primary = float(np.mean(primary))
    recipe = {
        "source_historical_float_precision": "inverse-count uses float32, then Python list; mean-normalized to1",
        "primary_order": TARGETS,
        "primary_full_data_weights": primary,
        "primary_purged_training_weights": inverse_weights(df.loc[fit]),
        "primary_fraction": "No primary_fraction parameter in inspected historical/current scripts, template or core. Effective weighted-label mass is data-dependent; no enforced primary minibatch fraction.",
        "template_defaults": {"n_folds":5,"max_epochs":400,"patience":40,"batch_size":64,
                              "hidden_dim":700,"depth":5,"dropout":0.1,"ffn_hidden_dim":300,
                              "ffn_num_layers":2,"warmup_epochs":2,"init_lr":1e-4,"max_lr":1e-3,
                              "final_lr":1e-4,"criterion":"mae","bounded_loss":False,
                              "split_strategy":"scaffold","seed":42,"from_foundation":None,
                              "freeze_mpnn_epochs":0,"batch_norm":True,"aggregation":"NormAggregation",
                              "precision":"16-mixed","fold_seed":"42+fold_idx","checkpoint":"best validation loss"},
        "explicit_member_overrides": {
            "union18p30":{"task_weights":primary+[0.3*mean_primary]*14,"uq_version":"v1",
                          "heads":"4direct+4log2fc+5ChEMBLpotency+5Veithmax_response", "source_commit":UNION18},
            "mtaux8":{"task_weights":primary+[0.3*mean_primary]*4,"uq_version":"v1","heads":"4direct+4log2fc"},
            "2d6isoform6":{"task_weights":[1.0]+[0.3]*5,"uq_version":"v1",
                           "heads":["direct2D6","log2fc2D6","TDI-condition2D6","directEmax2D6","ChEMBL2D6","Veithmax_response2D6"]},
            "2d6single":{"uq_version":"v1","task_weights_effective":None,"heads":["direct2D6"]}},
        "historical_combination":"Flatmean2members for1A2/2C9/3A4; flatmean4members for2D6. Each member itself5foldensemble.",
        "current_cross_fold_inference":"Retrieves training-time OOF captures through chemprop_pull_cv; does not create fresh splits or retrain.",
        "calibration":"Historical leaderboard entry applies board-derived placement; do not import these constants into a train-only local reference. Define calibration on internal training data separately.",
    }
    (out / "reference_recipe.json").write_text(json.dumps(recipe, indent=2))
    overlap = None
    if args.our_holdout.exists():
        our = pd.read_csv(args.our_holdout)
        overlap = len(set(holdout_ids) & set(our.Molecule_Name))
    manifest["verification"] = {
        "official_sha256": sha(official_raw), "public_inhibition_sha256": sha(public_raw),
        "structures_source_sha256": sha(structures_raw), "all_16_numeric_columns": columns_checked,
        "identity_order_and_smiles_exact":True,"holdout_id_hash_definition":"sha256(newlinejoinedIDs,no trailingnewline,originalroworder)",
        "holdout_id_sha256":id_hash,"holdout_n":int(held.sum()),"raw_train_n":int((~held).sum()),
        "purged_train_n":int(fit.sum()),"removed_parent_counterparts_n":int(purged.sum()),
        "cross_parent_groups_raw":len(set(keys[held]) & set(keys[~held])),"cross_parent_groups_purged":0,
        "hits_union_n":len(hits),"label_counts":df.loc[held,TARGETS].notna().sum().to_dict(),
        "overlap_with_our750":overlap,
        "holdout_ids_preserved_after_purge":True,
    }
    manifest["limits"] = [
        "Original author heldout-ID/OOF/model artifacts not found publicly; reconstruction matches529count and inputvalues, not recovered original persistedIDs.",
        "The author marked this analog holdout retired; current reference also uses scaffoldOOF on each member-specific input set.",
        "ChEMBL/PubChem public objects were modified after historical leaderboard submission; historical data objectversions unverified.",
        "The0.4378historicalentry uses18headunion, althoughAug30sourcealready26heads. UNION18pin chosen from matching earlier source.",
        "No training, submission, cloudallocation or privatebucketaccess performed by this builder.",
    ]
    manifest["output_sha256"] = {str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob("*") if p.is_file() and p.name != "manifest.json"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest["verification"], indent=2))


if __name__ == "__main__":
    main()
