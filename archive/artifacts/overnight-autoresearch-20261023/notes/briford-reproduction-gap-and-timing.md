# Reproduction scope and submission timing — 2026-10-24

The campaign did not reproduce the complete leaderboard-producing briford pipeline. It rebuilt its four model families and principal hyperparameters, using an adapted training/data/CV/calibration procedure. Local improvement against that adaptation does not establish improvement against the historical .4378 submission.

Verified differences:
- Original historical cyp_recalibrate.py uses target centre/spread and correlation adjustments derived from prior scored submissions. Our pipeline fits calibration and weights using TRAIN OOF only. These are different algorithms, not interchangeable implementations.
- For CYP2D6 the original STRAE_MOMENTS specifies mean3.57 andSD0.90. Our final750-row CSV has mean4.6954764 andSD0.3452698. These are prediction-distribution quantities; neither row in this comparison is a measurement of the hidden labels.
- Our folds partition official TRAIN while external auxiliary rows are included in each fit. The author's inspected training routine uses CV over the merged union. Task weights were recomputed per fit, data snapshots differed, and external normalized-parent exclusions were applied. These differences are recorded in actual trial_metadata.json, component.deviations.
- Original historical checkpoint/OOF artifacts were not available in the inspected sources. Our scored CSV additionally averages two seeds and applies the selected positive affine stacking procedure.
- Only our candidate was submitted. The retained reference_comparator_NOT_SUBMITTED.csv has no official score. We cannot numerically apportion the .7521-vs-.4378 gap to calibration, data, splits, randomness, or an implementation issue without appropriate comparisons.

Observed macro Spearman is .7564 for us versus .7516 for briford, while MAE is .9284 versus .6331. This makes scale/offset a plausible contributor and is consistent with the known calibration difference. It does not prove that calibration explains the entire gap or that all four targets have comparable ranking.

Timing on2026-10-24, Europe/Moscow:
-03:10:09.925: server accepted the CSV and stated that it should appear within2hours.
-03:13:26.643: our last early check found no visible leaderboard result.
-11:33:17.950: our next check found the scored entry.
There were no intervening saved checks. The observable time-to-visibility was more than approximately3minutes and at most8hours23minutes. This broad window is not a measured processing duration. The2hour statement is the server's expectation, not a verified completion time. The leaderboard Submitted timestamp records upload time, not scoring completion.

Sources: reference_audit/reference_recipe.json; reference_audit/sources/8c72c7559471febaf0962fd551b4eaab8db3a136/ml_pipelines/OpenADMET/cyp/scripts/cyp_recalibrate.py; remote/results/FINAL_reference_seed42/union18/seed42/fold0/trial_metadata.json; submission_package_v1/test_vector_comparison.json; gate_bundle_v1/certificate.json; official_results/20261024T084528Z/leaderboard.csv; submission-ledger/attempts/f0e32b5fecab41d9a68c098e0ebe4b0d05cbc61760eb3dbd63c300382945e053/receipt.json; official_results/20261024T001326Z/result.json; official_results/20261024T083317Z/result.json.

Advisor claude-fable-5, consultation20261024T085754Z-cbe4dace, attributed nearly all of the gap to calibration. Codex verified the calibration difference and timing, but does not adopt that full causal attribution: similar macro rank correlations and a transferred-moment R2 approximation do not substitute for a controlled comparison on the same scored predictions/subset.
