# ADMETlab chemical identity and feature audit

The frozen snapshot contains **2,660 molecules**: 2,315 official training molecules and 345 blinded-test molecules. No identity corruption, invalid SMILES, feature-row mismatch, nonfinite feature, or unexplained structural change was found in this snapshot. Five service-side representation changes are documented below. The collection is partial; this is not a completion certificate for all requested data.

Snapshot manifest time: `2026-10-25T22:45:05.985514+00:00`. Audit time: `2026-10-25T23:01:41.522147+00:00`. The raw and numeric files were copied only after both hashes matched an unchanged manifest. No collection inputs or stored predictions were edited.

| Check | Observed result |
|---|---:|
| Raw rows / unique raw SMILES | 2,660 / 2,660 |
| Feature rows / unique request IDs | 2,660 / 2,660 |
| Numeric endpoint columns | 120 |
| Original official structure → requested structure | 2,660/2,660 same isomeric molecular graph |
| All source aliases represented by collected requests | 10,026/10,026 same isomeric molecular graph |
| Exact requested → service isomeric graph match | 2,655/2,660 |
| Documented neutralization changes | 4 |
| Equivalent sulfoxide representation normalization | 1 |
| Raw/feature identity mismatches | 0 |
| Reconstructed numeric-feature mismatches (1e-12 float tolerance) | 0 |
| Missing or nonfinite numeric values | 0 |
| CYP probability values outside [0,1] | 0 |
| Structural-alert atom indices outside service-graph bounds | 0 |
| Reported MW matching service exact mass rounded to2dp | 2,660/2,660 |
| Reported formal charge matching service graph | 2,660/2,660 |
| Duplicate isomeric graphs | 0 |
| Duplicate groups after removing stereochemistry | 1 |
| Identical complete120-feature profiles | 0 |

## Service-side changes

Four inputs are carboxylate anions. ADMETlab returned their neutral carboxylic acids, adding one hydrogen and changing formal charge−1→0. These are preprocessing differences, not lost or mismatched rows:

- `OCNT-2316697`
- `OCNT-2309736`
- `OCNT-2313271`
- `OCNT-2314452`

The fifth, `OCNT-2328911`, changes the sulfoxide representation from `S=O` to `[S+]([O-])`. Formula and net charge are preserved. RDKit functional-group normalization maps the two strings to exactly the same isomeric graph; the sulfur center is R in both normalized structures.

Preserve the requested/original structure for the primary model graph. Retain `service_smiles` so the teacher features are explicitly attributed to the structure ADMETlab processed. Do not replace the original experimental target or silently rewrite input SMILES to the service representation. The four neutralizations should remain flagged in training data provenance and be reviewed as part of the final full-data audit.

Detailed cases: [service-structure-differences.csv](service-structure-differences.csv). All row-level evidence: [molecule-audit.csv](molecule-audit.csv).

## Stereochemistry and deduplication

`OCNT-2535550` and `OCNT-2535296` are a retained enantiomer pair. Their request and service strings preserve opposite tetrahedral configurations. They are distinct molecules and must **not** be deduplicated by a stereo-stripped connectivity key. No request or service duplicate exists when stereochemistry is retained.

The separate input audit covers all5,655 official molecules, including those not yet labeled: all parse, all source→request isomeric graphs match, all request hashes match, and there are no exact isomeric duplicate groups. Six groups merge only after stripping stereochemistry; none crosses official train/test. This does not replace checking the frozen training/validation splits, which can divide molecules within the training pool.

See [chemical-duplicate-groups.json](chemical-duplicate-groups.json) and [whole-official-input-audit.json](whole-official-input-audit.json).

## Feature meaning and limits

All120 numeric columns were reconstructed from the original raw CSV and the recorded schema. Numeric values are preserved; structural-alert lists are represented by their match counts, with raw atom-index tuples retained in the raw snapshot. Atom indices were checked for bounds, not independently re-matched against proprietary SMARTS definitions.

The reported `MW` is empirically consistent with exact monoisotopic mass rounded to two decimals, rather than RDKit's average molecular weight, for every audited row. This is a representation/unit check; it does not verify the biological prediction endpoints.

ADMETlab values are **teacher predictions or computed descriptors, not experimental assay labels**. This audit cannot establish their predictive accuracy, calibration, or historical training-set membership. It does not establish freedom from teacher-data overlap with challenge compounds. Fit feature scaling/imputation only on each training fold, retain the frozen holdouts, and evaluate improvements using experimental CYP targets.

## Reproduce and finish the audit

Runtime: Python3.12.11, RDKit2026.09.1, pandas3.1.0.

```bash
/Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python audit_chemistry.py --reuse-snapshot
```

For a later collection snapshot, use a **new output directory** so the frozen evidence is not overwritten:

```bash
/Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python audit_chemistry.py --out /absolute/path/to/final-chemistry-audit
```

The final audit should verify the selected scope's coverage (5,655 official requests or the agreed larger pool), rerun the same row/chemical/feature checks, reconcile every mismatch rather than drop it, and preserve all source/request/service identities. Current source-map SHA256: `7849899d79cb16d17deac9ed854c000383275c75bac5ae61d5a5c9355e95f231`.

Machine-readable summary: [summary.json](summary.json). Reproducible script: [audit_chemistry.py](audit_chemistry.py). Frozen inputs: [raw-snapshot.csv](raw-snapshot.csv), [features-snapshot.csv](features-snapshot.csv), [collection-manifest.json](collection-manifest.json).


## Endpoint-type-aware probability checks

The reusable audit now uses a pinned [endpoint-type ledger](endpoint-types.json) derived from the cached official program-description tables and explicit API probability explanations. It checks0..1 bounds for64documented classification-probability columns only. Eighteen documented regression columns and38computed/rule/untyped columns do not receive generic probability bounds. All64checks pass on the same frozen2,660-row snapshot. Other columns retain finite-value and raw-to-numeric checks; molecular mass/formal charge and alert atom indices have their separate chemistry-specific checks. This update does not claim that the expanding collection is complete.
