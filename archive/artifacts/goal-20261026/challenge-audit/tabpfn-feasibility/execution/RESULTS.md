# Completed ADMET120 TabPFN evaluation

ORX experiment4d577549-bb84-4f99-abc4-3c2d6bb9d530, run d582f716-e4e2-43c3-a4cf-fed02a9d39f0, immutable commit4f2a84cc99a3a0868541b3b63446cb275fe74c29. Run completed with exit0 in6m01s; evaluation body213.17s. Exactly48 endpoint calls completed, summing111.64s in fit/predict timing. Runtime: Python3.11.13, Torch2.8.0+cu128, TabPFN9.2.0, NumPy2.2.6, sklearn1.7.2, pandas2.3.3, RDKit2026.9.1, one RTX3090/24GB, driver595.71.05.

Inputs are the certified complete official5655 ADMET subset of the frozen18,460-outcome snapshot. Models use only the4,905 official experimental training labels, isolated outer-training pools and their frozen fivefold splits. This does not claim completion of32,421 acquisition. Native31f8a64a is the qualified fixed historical expert, with its original-source limitations preserved. Checkpoint, raw snapshot, official role membership, all12 native vectors and source policies are hash-bound.

| Model | Own750 ST-RAE | Briford529 ST-RAE |
|---|---:|---:|
| Corrected native |0.6207769340|0.6423089039|
| TabPFN ADMET120 |0.7033324334|0.7320679607|
| Native blend, one global weight |0.6212457535|0.6256434671|
| Native blend, per-CYP weights |0.6194895270|0.6268672953|

Each cohort's training OOF independently selected the per-CYP blend, before that model's outer diagnostic was used. OOF ST-RAE is0.6205735185 for own750 and0.6201802472 for briford529. TabPFN coefficients in CYP1A2/CYP2C9/CYP2D6/CYP3A4 order are own `[0.54054429,0.34404849,0.08766131,0.24758938]`; briford `[0.39760287,0.36066264,0.11521252,0.31942046]`. These are development-cohort choices, not a globally chosen final submission recipe.

The selected blend's other raw macro metrics:

| Cohort/model | MAE | R² | Spearman | Kendall |
|---|---:|---:|---:|---:|
| Own native |0.52342721|0.47048599|0.67324469|0.49550220|
| Own per-CYP blend |0.53173592|0.46336222|0.66786405|0.48915906|
| Briford native |0.47577742|0.38463520|0.65309186|0.47718871|
| Briford per-CYP blend |0.47346760|0.38791078|0.65282301|0.47580430|

Thus the small own-holdout ST-RAE change comes with worse MAE/R²/ranking; briford shows better ST-RAE/MAE/R² but slightly worse ranking. Standalone ADMET120 is weaker than native on both cohorts. Paired scaffold-bootstrap95% intervals for selected-blend minus native ST-RAE are own−0.00128741 `[−0.017398,0.012738]`, briford−0.01544161 `[−0.036448,0.002036]`,1000 valid resamples each. They are conditional on these fitted predictions, not training-seed uncertainty, and the reused cohorts overlap143 molecules. Published-placement outputs remain diagnostic and are preserved separately.

All140 recovered files (6,283,437bytes),48 prediction-cache receipts/arrays and remote ORX log were SHA-verified. Eight saved raw metric rows were independently rescored against the original official truth/CI columns with zero numerical difference. `recovery-certificate.json` binds the evidence; `recovered/results/all-metrics.csv`, `per-cyp-metrics.csv`, `paired-bootstrap.csv` and all prediction/OOF files preserve adverse outcomes as well as improvements. No weights were tuned on outer scores, no full refit occurred and nothing was submitted.

After verified recovery, the parent authorized a separate H5 child on the same instance and unchanged1.10USD/120min lease, testing frozen ADME600 versus ADME720. This completed node remains immutable. Instance57759747 is retained only for that bounded authorized continuation; shared teardown/accounting will be recorded when it finishes.
