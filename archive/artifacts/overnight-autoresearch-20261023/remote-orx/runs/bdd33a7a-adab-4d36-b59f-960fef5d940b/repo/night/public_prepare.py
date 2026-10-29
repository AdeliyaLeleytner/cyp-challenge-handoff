"""CPU-only public-data preparation CLI; launch only through a committed ORX node.

Example: python -m night.public_prepare --asset-root /workspace/cyp-night/assets
No model fitting, reference-recipe changes, or compute provisioning occurs here.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from .public_data import (
    PublicDataError, _atomic_bytes, _atomic_json, _digest, _utc,
    load_public_data, normalize_parent_key, wide_auxiliary_table,
)

SOURCE_NAMES = {"tox21_cyp": "pubchem_tox21_cyp",
                "bindingdb_native_articles": "bindingdb_native_articles"}


def official_exclusions(asset_root: Path) -> tuple[set[str], dict]:
    """Verify cohorts.json covers every currently staged official train/test parent."""
    path = asset_root / "cohorts.json"
    cohort = json.loads(path.read_text())
    values = cohort.get("excluded_parent_keys")
    if not isinstance(values, list) or not values or any(not isinstance(x, str) or not x for x in values):
        raise PublicDataError("cohorts.json must contain a nonempty list of excluded_parent_keys")
    excluded = set(values)
    details = {"cohorts_sha256": _digest(path), "excluded_parent_count": len(excluded), "official_files": {}}
    for filename in ("official-train.csv", "official-test.csv"):
        file = asset_root / filename
        frame = pd.read_csv(file, usecols=["Molecule_Name", "SMILES"])
        parents = frame.SMILES.map(normalize_parent_key)
        if parents.isna().any():
            raise PublicDataError(f"Invalid official structures in {filename}; exclusion completeness unresolved")
        missing = set(parents) - excluded
        if missing:
            raise PublicDataError(f"cohorts.json excludes too few parents: {len(missing)} missing from {filename}")
        details["official_files"][filename] = {
            "sha256": _digest(file), "rows": len(frame), "unique_parents": int(parents.nunique()),
        }
    return excluded, details


def reference_parents(asset_root: Path, excluded: set[str]) -> tuple[set[str] | None, dict]:
    """Read optional historical public tables solely for structural-overlap accounting."""
    known = set()
    records = {}
    for filename in ("chembl_all_isoforms.csv", "pubchem_all_isoforms.csv"):
        candidates = [asset_root / "reference/public_data" / filename,
                      asset_root / "reference_audit/public_data" / filename]
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            records[filename] = {"status": "not_available"}
            continue
        frame = pd.read_csv(path, usecols=["smiles"])
        parents = {normalize_parent_key(x) for x in frame.smiles.dropna().unique()}
        valid = parents - {None} - excluded
        known.update(valid)
        records[filename] = {"path": str(path), "sha256": _digest(path),
                             "rows": len(frame), "eligible_unique_parents": len(valid)}
    available = any("sha256" in x for x in records.values())
    return known if available else None, records


def assess_quality(tidy: pd.DataFrame, sources: list[str], excluded: set[str]) -> dict:
    """Structural/schema gates, not an invented model-quality/effect-size threshold."""
    failures = []
    if tidy.empty:
        failures.append("No retained public measurements")
    overlap = set(tidy.parent_key.dropna()) & excluded
    if overlap:
        failures.append(f"External data includes {len(overlap)} excluded official parents")
    if tidy.parent_key.isna().any() or tidy.canonical_smiles.isna().any():
        failures.append("Retained measurements have missing normalized structures")
    points = tidy.loc[tidy.is_point_eligible.fillna(False).astype(bool)]
    if not points.empty:
        if not np.isfinite(pd.to_numeric(points.p_activity, errors="coerce")).all():
            failures.append("Eligible point rows contain non-finite p-activity")
        if not points.p_relation.eq("=").all() or not points.task_kind.eq("regression").all():
            failures.append("Eligible point view includes censored or non-regression rows")
    source_counts = {}
    for adapter in sources:
        name = SOURCE_NAMES[adapter]
        rows = tidy.loc[tidy.source.eq(name)]
        eligible = points.loc[points.source.eq(name) & points.endpoint.isin(["IC50", "AC50"])]
        source_counts[adapter] = {"records": len(rows), "eligible_ic50_ac50_records": len(eligible),
                                  "targets": sorted(rows.target.dropna().unique().tolist())}
        if eligible.empty:
            failures.append(f"Requested source {adapter} has no eligible IC50/AC50 rows after exclusion")
    return {"status": "pass" if not failures else "fail", "passed": not failures,
            "failures": failures, "excluded_parent_overlap_count": len(overlap),
            "source_counts": source_counts,
            "interpretation": "Pass means reproducible usable source/identity/label schema, not challenge-domain equivalence or model improvement"}


def _write_parquet_atomic(frame: pd.DataFrame, path: Path) -> dict:
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    os.close(fd)
    try:
        frame.to_parquet(temporary, index=False)
        with open(temporary, "rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        return {"status": "written", "path": str(path), "sha256": _digest(path)}
    except ImportError as error:
        return {"status": "optional_engine_unavailable", "reason": str(error)}
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare(asset_root: Path, *, sources=None, config=None, parquet=True) -> dict:
    root = Path(asset_root)
    output = root / "new_public"
    output.mkdir(parents=True, exist_ok=True)
    sources = list(SOURCE_NAMES if sources is None else sources)
    if not sources or set(sources) - set(SOURCE_NAMES):
        raise PublicDataError(f"Specify one or more supported sources: {list(SOURCE_NAMES)}")
    config = dict(config or {})
    _atomic_json(output / "data_quality.json", {"status": "running", "passed": False, "started_utc": _utc()})
    try:
        excluded, official_meta = official_exclusions(root)
        known, reference_meta = reference_parents(root, excluded)
        tidy, loader_manifest = load_public_data(root, sources=sources, excluded_parent_keys=excluded,
                                                config=config, known_parent_keys=known)
        quality = assess_quality(tidy, sources, excluded)
        wide, heads, head_meta = wide_auxiliary_table(tidy, group_by=("source", "target", "endpoint"))
        csv_path = output / "measurements.csv"
        _atomic_bytes(csv_path, tidy.to_csv(index=False).encode())
        _atomic_bytes(output / "auxiliary_wide.csv", wide.to_csv(index=False).encode())
        parquet_meta = _write_parquet_atomic(tidy, output / "measurements.parquet") if parquet else {"status": "disabled"}
        source_sets = {str(s): set(g.parent_key) for s, g in tidy.groupby("source")}
        overlap = {"reference_tables": reference_meta, "known_reference_parent_count": None if known is None else len(known),
                   "per_source": {s: {"unique_parents": len(keys),
                                        "overlap_reference_parents": None if known is None else len(keys & known),
                                        "net_new_parents_vs_reference": None if known is None else len(keys - known)}
                                  for s, keys in source_sets.items()},
                   "pairwise_parent_overlap": {f"{a} | {b}": len(source_sets[a] & source_sets[b])
                                                 for a in source_sets for b in source_sets if a < b},
                   "interpretation": "Structural overlap only; no assay-equivalence or source-independence claim"}
        manifest = {"schema_version": 1, "created_utc": _utc(), "sources": sources, "config": config,
                    "official_exclusions": official_meta, "loader": loader_manifest,
                    "table": {"path": str(csv_path), "sha256": _digest(csv_path), "rows": len(tidy)},
                    "parquet": parquet_meta, "auxiliary_heads": heads, "head_metadata": head_meta,
                    "auxiliary_wide_sha256": _digest(output / "auxiliary_wide.csv"),
                    "data_quality": quality,
                    "implementation_sha256": {p.name: _digest(p) for p in [Path(__file__), Path(__file__).with_name("public_data.py")]}}
        _atomic_json(output / "overlap.json", overlap)
        _atomic_json(output / "manifest.json", manifest)
        _atomic_json(output / "data_quality.json", quality)
        print(json.dumps({"event": "public_data_prepared", "rows": len(tidy), "heads": len(heads),
                          "quality_status": quality["status"], "manifest": str(output / "manifest.json")}), flush=True)
        if not quality["passed"]:
            raise PublicDataError("Public-data quality gate failed: " + "; ".join(quality["failures"]))
        return manifest
    except Exception as error:
        _atomic_json(output / "data_quality.json", {"status": "fail", "passed": False,
                     "error_type": type(error).__name__, "error": str(error), "time_utc": _utc()})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--sources", nargs="+", choices=list(SOURCE_NAMES), default=list(SOURCE_NAMES))
    parser.add_argument("--config", type=Path, help="Optional public loader config JSON")
    parser.add_argument("--no-parquet", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text()) if args.config else {}
    try:
        prepare(args.asset_root, sources=args.sources, config=config, parquet=not args.no_parquet)
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)


if __name__ == "__main__":
    main()
