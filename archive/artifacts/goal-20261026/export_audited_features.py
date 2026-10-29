#!/usr/bin/env python3
"""Lossless, status-aware user export from a completed v3 audit. No network or fits."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames))
        return reader.fieldnames, list(reader)


def export(audit, quarantine, out):
    audit = audit.resolve()
    assert not out.exists(), "Choose a new export directory"
    summary = json.loads((audit / "summary.json").read_text())
    assert summary.get("audit_version") == "final-output-v3", "Completed v3 audit required"
    assert summary.get("outcomes_complete") is True and summary.get("requested_outcomes") == 32421, "All 32421 outcomes required"
    assert summary.get("mechanical_checks_passed") is True and summary.get("mechanical_errors") == [], "Unresolved audit errors"
    hashes = json.loads((audit / "audit-artifacts-sha256.json").read_text())
    required = {"summary.json", "raw-snapshot.csv", "features-snapshot.csv", "queue-snapshot.csv", "source-id-map-snapshot.csv", "outcome-ledger.csv", "schema.json"}
    assert required <= set(hashes), "Audit hash manifest incomplete"
    for name, expected in hashes.items():
        path = (audit / name).resolve()
        assert path.parent == audit and sha(path) == expected, "Audit file changed: " + name
    assert sha(audit / "features-snapshot.csv") == summary["features_sha256"]
    assert sha(audit / "queue-snapshot.csv") == summary["queue_sha256"]
    _, queue = read_rows(audit / "queue-snapshot.csv")
    _, features = read_rows(audit / "features-snapshot.csv")
    _, ledger = read_rows(audit / "outcome-ledger.csv")
    source_policy_path = Path(__file__).parent / "data-policy/DISPOSITION.json"
    source_policy = json.loads(source_policy_path.read_text())
    assert sha(quarantine) == source_policy["quarantine_sha256"], "Unreviewed source quarantine"
    _, source_exclusions = read_rows(quarantine)
    q = {r["request_id"]: r["SMILES"] for r in queue}
    f = {r["request_id"]: r for r in features}
    status = {r["request_id"]: r for r in ledger}
    assert len(queue) == len(q) == len(features) == len(f) == len(ledger) == len(status) == 32421
    assert set(q) == set(f) == set(status)
    excluded = {r["request_id"] for r in source_exclusions}
    assert excluded <= set(q)
    raw_headers, _ = read_rows(audit / "raw-snapshot.csv")
    schema = json.loads((audit / "schema.json").read_text())
    columns = sorted("ADMETLAB::" + "::".join(schema["web_column_to_endpoint"].get(c, ["csv_extra", c])) for c in raw_headers if c not in {"raw_smiles", "smiles"})
    assert len(columns) == len(set(columns)) == 120
    fields = ["request_id", "SMILES", "service_smiles", "outcome_status", "service_structure_relation", "numeric_prediction_complete", "chemistry_eligible", "source_supervision_excluded", "fresh_supervision_eligible"] + columns
    output = []
    for request in queue:
        rid, smiles = request["request_id"], request["SMILES"]
        row, record = f[rid], status[rid]
        assert hashlib.sha256(smiles.encode()).hexdigest() == rid and row["SMILES"] == smiles
        eligible = record["chemistry_eligible"].lower() == "true"
        numeric = record["numeric_endpoint_complete"].lower() == "true"
        assert not eligible or numeric
        output.append({"request_id": rid, "SMILES": smiles, "service_smiles": row["service_smiles"], "outcome_status": record["status"], "service_structure_relation": record["relation"], "numeric_prediction_complete": numeric, "chemistry_eligible": eligible, "source_supervision_excluded": rid in excluded, "fresh_supervision_eligible": eligible and rid not in excluded, **{c: row[c] for c in columns}})
    out.mkdir(parents=True)
    table = out / "admetlab-32421-audited-features.csv"
    with table.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    _, reread = read_rows(table)
    assert len(reread) == 32421
    for expected, actual in zip(output, reread):
        assert all(actual[k] == str(expected[k]) for k in fields), "Export round-trip changed a value"
    for source, name in [(audit / "source-id-map-snapshot.csv", "source-id-map.csv"), (audit / "outcome-ledger.csv", "outcome-ledger.csv"), (quarantine, "source-supervision-quarantine.csv"), (source_policy_path, "source-supervision-policy.json"), (audit / "OUTPUT_DISPOSITION-snapshot.json", "service-outcome-policy.json")]:
        (out / name).write_bytes(source.read_bytes())
    report = {"rows": 32421, "model_feature_columns": 120, "numeric_prediction_rows": summary["numeric_prediction_rows"], "chemistry_eligible_rows": summary["chemistry_eligible_rows"], "fresh_supervision_eligible_rows": sum(r["fresh_supervision_eligible"] for r in output), "service_rejected_rows": summary["service_rejected_rows"], "unresolved_service_structure_rows": summary["unresolved_service_structure_rows"], "lossless_csv_round_trip_verified": True, "smiles_rewritten": False, "numeric_values_imputed": False, "source_audit_manifest_sha256": sha(audit / "audit-artifacts-sha256.json"), "source_quarantine_sha256": sha(quarantine), "exporter_sha256": sha(__file__), "files": {x.name: sha(x) for x in sorted(out.iterdir()) if x.is_file()}}
    (out / "README.txt").write_text("ADMETlab model predictions, not experimental labels.\nThe table retains every requested outcome, including rejected and excluded rows.\nUse only the 120 ADMETLAB:: base columns as model features; status fields are audit metadata.\nMissing rejected values are intentionally blank; do not interpret them as zero activity.\nchemistry_eligible means the declared output/feature policy passed; inspect service_structure_relation for recorded standardization. It does not mean identical molecular microstates or biological accuracy.\nfresh_supervision_eligible additionally applies the reviewed external-source quarantine.\nIt does not certify all original assay annotations or override the separately qualified legacy native-expert policy.\nSMILES and numeric text were copied without normalization or imputation and round-trip checked.\nOriginal raw responses, categorical flags and full audit remain in the immutable audit directory.\n")
    report["source_policy_sha256"] = sha(source_policy_path)
    report["files"]["README.txt"] = sha(out / "README.txt")
    (out / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--source-quarantine", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.audit, args.source_quarantine, args.out), indent=2))
