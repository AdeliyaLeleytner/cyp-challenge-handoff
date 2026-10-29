"""Optional, isolated BindingDB patent source; does not alter initial D0/D1 assets.

Run only in a future committed ORX CPU child:
python -m night.bindingdb_patents --asset-root /workspace/cyp-night/assets
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from .public_data import (
    CachedHTTP, PublicDataError, _atomic_bytes, _atomic_json, _digest,
    _fetch_bindingdb_zip, _join_bindingdb_assays, _single_zip_text, _utc,
    normalize_and_exclude, normalize_parent_key, parse_bindingdb_stream, wide_auxiliary_table,
)

SOURCE = "bindingdb_patents"


def official_exclusions(root):
    path = root / "cohorts.json"
    values = json.loads(path.read_text()).get("excluded_parent_keys")
    if not isinstance(values, list) or not values or any(not isinstance(x, str) or not x for x in values):
        raise PublicDataError("Nonempty excluded_parent_keys required in cohorts.json")
    excluded = set(values)
    meta = {"cohorts_sha256": _digest(path), "excluded_parent_count": len(excluded), "official_files": {}}
    for name in ["official-train.csv", "official-test.csv"]:
        frame = pd.read_csv(root / name, usecols=["SMILES"])
        keys = frame.SMILES.map(normalize_parent_key)
        if keys.isna().any() or set(keys) - excluded:
            raise PublicDataError(f"Incomplete or invalid official parent exclusion for {name}")
        meta["official_files"][name] = {"sha256": _digest(root / name), "rows": len(frame), "parents": int(keys.nunique())}
    return excluded, meta


def reference_parents(root, excluded):
    known, meta = set(), {}
    for name in ["chembl_all_isoforms.csv", "pubchem_all_isoforms.csv"]:
        path = next((root / folder / name for folder in ["reference/public_data", "reference_audit/public_data"]
                     if (root / folder / name).exists()), None)
        if path is None:
            meta[name] = {"status": "not_available"}
            continue
        frame = pd.read_csv(path, usecols=["smiles"])
        keys = {normalize_parent_key(s) for s in frame.smiles.dropna().unique()} - {None} - excluded
        known.update(keys)
        meta[name] = {"sha256": _digest(path), "rows": len(frame), "eligible_unique_parents": len(keys)}
    return (known if any("sha256" in x for x in meta.values()) else None), meta


def _write_parquet_atomic(frame, path):
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


def parse_patents_stream(handle, *, release="202610"):
    """Reuse exact human-accession/single-chain/units parser, then add patent scope.

    Native-article curation-source filtering is disabled deliberately: this parser
    consumes the dedicated patent archive and requires each retained row to have
    explicit Patent Number provenance. ChEMBL imports are not used as a fallback.
    """
    table, audit = parse_bindingdb_stream(handle, release=release, require_native=False)
    patent_numbers = [str(json.loads(p).get("Patent Number", "")).strip()
                      for p in table.provenance_json]
    has_patent = pd.Series([bool(p) for p in patent_numbers], index=table.index, dtype=bool)
    audit["measurements_missing_patent_number"] = int((~has_patent).sum())
    table = table.loc[has_patent].copy()
    table["source"] = SOURCE
    table["source_version"] = release
    for idx, row in table.iterrows():
        provenance = json.loads(row.provenance_json)
        provenance.update(archive_scope="BindingDB dedicated Patents TSV",
                          archive_filename=f"BindingDB_Patents_{release}_tsv.zip")
        table.at[idx, "provenance_json"] = json.dumps(provenance, sort_keys=True)
        table.at[idx, "document_id"] = "PATENT:" + str(provenance["Patent Number"]).strip()
        table.at[idx, "quality_flag"] = ("patent_equal_point" if row.is_point_eligible
                                         else "patent_censored_or_invalid_point")
    audit.update(parsed_patent_measurements=len(table),
                 patent_document_count=int(table.document_id.nunique()),
                 original_source_counts={str(k): int(v) for k, v in table.original_source.value_counts().items()})
    return table.reset_index(drop=True), audit


def load_bindingdb_patents(client: CachedHTTP, *, release="202610", join_assays=True):
    if not re.fullmatch(r"20\d{4}", release):
        raise ValueError("BindingDB release must be YYYYMM")
    filename = f"BindingDB_Patents_{release}_tsv.zip"
    path = _fetch_bindingdb_zip(client, filename, release)
    archive, stream = _single_zip_text(path)
    try:
        table, audit = parse_patents_stream(stream, release=release)
    finally:
        stream.close()
        archive.close()
    if join_assays and not table.empty:
        mapping = _fetch_bindingdb_zip(client, f"BindingDB_rsid_eaids_{release}_tsv.zip", release)
        assays = _fetch_bindingdb_zip(client, f"BindingDB_Assays_{release}_tsv.zip", release)
        table, joins = _join_bindingdb_assays(table, mapping, assays)
        audit.update(joins)
    audit.update(release=release, archive_filename=filename,
                 source_policy="Dedicated patent archive plus explicit patent number; exact human CYP accessions and single-chain targets",
                 endpoint_policy="IC50, Ki, Kd, EC50 retained separately in nM; relation reversed on p transform")
    return table, audit


def prepare_patents(asset_root: Path, *, release="202610", join_assays=True, parquet=True):
    root = Path(asset_root)
    output = root / "new_public_patents"
    output.mkdir(parents=True, exist_ok=True)
    _atomic_json(output / "data_quality.json", {"status": "running", "passed": False, "started_utc": _utc()})
    try:
        excluded, official_meta = official_exclusions(root)
        known, reference_meta = reference_parents(root, excluded)
        # Shares immutable raw cache only; no writes to new_public or its head tables.
        client = CachedHTTP(root / "public_data/cache")
        raw, source_audit = load_bindingdb_patents(client, release=release, join_assays=join_assays)
        tidy, exclusion_audit = normalize_and_exclude(raw, excluded)
        duplicate_key = ["source", "source_version", "assay_id", "record_id", "target",
                         "endpoint", "relation", "raw_value", "parent_key"]
        duplicates = int(tidy.duplicated(duplicate_key).sum())
        tidy = tidy.drop_duplicates(duplicate_key).reset_index(drop=True)
        wide, heads, head_meta = wide_auxiliary_table(tidy, group_by=("source", "target", "endpoint"), endpoints=("IC50",))
        points = tidy.loc[tidy.is_point_eligible.fillna(False).astype(bool)]
        failures = []
        if not heads:
            failures.append("No eligible patent IC50 auxiliary heads after official-parent exclusion")
        if set(tidy.parent_key) & excluded:
            failures.append("Excluded official parents remain")
        if tidy.parent_key.isna().any() or tidy.canonical_smiles.isna().any():
            failures.append("Missing normalized structures")
        if (not np.isfinite(pd.to_numeric(points.p_activity, errors="coerce")).all()
                or not points.p_relation.eq("=").all()):
            failures.append("Eligible point labels are nonfinite or censored")
        if not tidy.document_id.str.startswith("PATENT:").all():
            failures.append("Missing patent document provenance")
        parents = set(tidy.parent_key)
        initial_path = root / "new_public/measurements.csv"
        initial_parents = (set(pd.read_csv(initial_path, usecols=["parent_key"]).parent_key.dropna())
                           if initial_path.exists() else None)
        overlap = {"reference_tables": reference_meta,
                   "reference_overlap_parents": None if known is None else len(parents & known),
                   "net_new_parents_vs_reference": None if known is None else len(parents - known),
                   "initial_public_table_sha256": _digest(initial_path) if initial_path.exists() else None,
                   "initial_public_overlap_parents": None if initial_parents is None else len(parents & initial_parents),
                   "net_new_parents_vs_initial_public": None if initial_parents is None else len(parents - initial_parents),
                   "interpretation": "Structural overlap only; distinct sources may repeat the same assays or patent families"}
        quality = {"status": "pass" if not failures else "fail", "passed": not failures,
                   "failures": failures, "source": SOURCE, "records": len(tidy),
                   "eligible_ic50_records": int((points.endpoint == "IC50").sum()),
                   "excluded_parent_overlap_count": len(parents & excluded),
                   "interpretation": "Schema/identity gate only; does not establish source-domain equivalence or model improvement"}
        csv_path = output / "measurements.csv"
        _atomic_bytes(csv_path, tidy.to_csv(index=False).encode())
        _atomic_bytes(output / "auxiliary_wide.csv", wide.to_csv(index=False).encode())
        parquet_meta = _write_parquet_atomic(tidy, output / "measurements.parquet") if parquet else {"status": "disabled"}
        manifest = {"schema_version": 1, "created_utc": _utc(), "sources": [SOURCE],
                    "config": {"release": release, "join_assays": join_assays},
                    "official_exclusions": official_meta, "source_audit": source_audit,
                    "exclusion_audit": exclusion_audit, "exact_duplicate_records_removed": duplicates,
                    "retained_unique_parents": len(parents),
                    "endpoint_counts": {str(k): int(v) for k, v in tidy.endpoint.value_counts().items()},
                    "table": {"path": str(csv_path), "sha256": _digest(csv_path), "rows": len(tidy)},
                    "parquet": parquet_meta, "auxiliary_heads": heads, "head_metadata": head_meta,
                    "auxiliary_wide_sha256": _digest(output / "auxiliary_wide.csv"),
                    "downloads": client.records, "data_quality": quality,
                    "implementation_sha256": {p.name: _digest(p) for p in [Path(__file__), Path(__file__).with_name("public_data.py")]}}
        _atomic_json(output / "overlap.json", overlap)
        _atomic_json(output / "manifest.json", manifest)
        _atomic_json(output / "data_quality.json", quality)
        print(json.dumps({"event": "bindingdb_patents_prepared", "rows": len(tidy), "heads": len(heads),
                          "quality_status": quality["status"], "manifest": str(output / "manifest.json")}), flush=True)
        if failures:
            raise PublicDataError("Patent data quality gate failed: " + "; ".join(failures))
        return manifest
    except Exception as error:
        _atomic_json(output / "data_quality.json", {"status": "fail", "passed": False,
                     "error_type": type(error).__name__, "error": str(error), "time_utc": _utc()})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--release", default="202610")
    parser.add_argument("--no-assay-join", action="store_true")
    parser.add_argument("--no-parquet", action="store_true")
    args = parser.parse_args()
    try:
        prepare_patents(args.asset_root, release=args.release,
                        join_assays=not args.no_assay_join, parquet=not args.no_parquet)
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)


if __name__ == "__main__":
    main()
