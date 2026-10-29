# Researcher Handoff

## Current state

The latest verified receipt in this snapshot records restoration of the original native submission on 27 October 2026 at 19:40 UTC. The observation at 19:50 UTC reported MA-ST-RAE 0.4425, MAE 0.6365, R² 0.6171, Spearman 0.7546, Kendall 0.5775, and rank 30. These are historical observations, not a claim about the current live rank.

Exact file: [native-csv.csv](../archive/artifacts/cyp-private-v2-20261026/p11/evidence/native-csv.csv). SHA256: `349165ecf50906e43a27f12dee97891a92cda59e798db614ef27a7c920c38a37`. [Restoration receipt](../archive/artifacts/cyp-private-v2-20261026/restore-20261027/processed-result.json).

Top-level STATUS, PLAN, and FINDINGS files sometimes lag behind the detailed receipts. For example, the private campaign's STATUS still describes the P5b submission, while `restore-20261027` records the subsequent return to native. Prefer the relevant prediction hashes, receipts, and readouts when establishing chronology. An early “not launched” statement in an append-only plan may precede a completed run documented later in the same file.

## Package contents

The package includes training and evaluation code, source snapshots, fixed folds and membership records, experimental labels and predicted features, selected models and fitted transforms, OOF/holdout/blind predictions, selection protocols, chemical audits, and run evidence. See [ARCHIVE_INDEX.md](ARCHIVE_INDEX.md). `manifest/files.jsonl` identifies the retained files and their Git or release storage; `manifest/exclusions.json` records packaging exclusions.

## Established findings

- Improving local ST-RAE does not guarantee a better hidden-test score. The four historical submissions illustrate this for specific related predictors; they do not establish a universal rule.
- H6 uses a separate LightGBM readout of 600 ADME coordinates and 120 ADMETlab properties, followed by convex blending. Its features were not fed into Chemprop. Direct end-to-end fusion was tested separately in P7 and underperformed its matched control.
- Vol/Dense contained a unit defect. P7R corrects 170 cells across 85 rows. The correction is justified, but it did not rescue the tested fusion recipe.
- P3 did not establish an advantage for interval loss or confidence-interval weighting over matched MAE/uniform training.
- Atom-JEPA/TabICL and nested ensembles produced small, inconsistent effects. A stable advantage over the original native ensemble was not established.
- External data mix assays, endpoints, and conditions. Screening, direct inhibition, +NADPH/active-condition measurements, and TDI must not be treated as interchangeable labels. Unknown teacher-pretraining membership cannot be declared independent of every evaluation structure.

## Recommended continuation

1. Restore and verify the artifacts. Preserve the exact incumbent CSV; a similar refit is not an identical replacement.
2. Read the [P11 protocol](../archive/artifacts/cyp-private-v2-20261026/p11/VALIDATION_PROTOCOL.json) and [P11 report](../archive/artifacts/cyp-private-v2-20261026/p11/report.html). Its provisional primary proxy is macro MAE on own750 before blind-population placement. This metric was chosen retrospectively. Retain all other metrics, the separate Briford529 stress cohort, and uncertainty estimates; do not interpret the proxy as a numerical leaderboard forecast.
3. Choose one specific experimental contrast after reviewing sources and splits. Keep the exact historical native reference and an appropriate matched control. Changing the base model, features, loss, and output transformation together does not identify which change caused an effect.
4. Fit preprocessing, calibration, PCA, and blend weights only inside the permitted training partition. Slicing an existing OOF bank does not create a new independent holdout if the underlying training procedure has already used those molecules elsewhere.
5. Before a new submission, preserve the candidate hash, complete evaluation report, training provenance, and fixed serving policy. Append the leaderboard result afterward. Do not fit a composite metric to the four already observed leaderboard points.
6. Agree new compute spending and publication with the owner. Archived leases, SSH records, and account state describe past operations; active credentials are not transferred.

Historical cleanup records document recovery of models and teardown of task-owned GPUs. This handoff involved no new model training or compute rentals. Check the actual cloud account separately before a future launch.
