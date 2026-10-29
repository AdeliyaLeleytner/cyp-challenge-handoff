# Private incumbent-anchored H6 candidate — review only

The candidate is prepared and independently verified. It combines the **unchanged original native predictor** with the same frozen H6 ADME720-LightGBM heads, using four coefficients fitted only on their matching full-training OOF predictions. It uses the exact frozen original serving operator. No base model, feature value, or calibration was changed.

**It has not been promoted, published or submitted. Its leaderboard score is unknown. Explicit human approval is required before any public dispatch.** The exact incumbent CSV with SHA349165… remains untouched.

## Files

- `results/incumbent-anchored-H6-served-PRIVATE.csv` — the served candidate, SHA256 `6807263f0ccadcb31aa28a5c54653608e12271939a2490a2404d4353aeb0e16d`.
- `results/incumbent-anchored-H6-raw-PRIVATE.csv` — raw audit vector, SHA256 `df1fdf1edbbac6b6bc3319aa3ed30c63fc7240d054328621aa26136df098dd7a`.
- `results/lambda0-original-incumbent-CONTROL.csv` — byte-identical incumbent control, SHA256 `349165ecf50906e43a27f12dee97891a92cda59e798db614ef27a7c920c38a37`.

All 750 official IDs, exact SMILES and row order are preserved. Both candidate files pass the pinned official validator and explicit finite-value and sample-SD≥.01 checks. Source incumbent bytes are independently verified unchanged.

## What changed

The feature weights in `(1−w)*original_native + w*H6_feature_only` are:

| CYP | H6 contribution |
|---|---:|
| 1A2 | .515799 |
| 2C9 | .400598 |
| 2D6 | .262391 |
| 3A4 | .396168 |

They were fitted on all 4,905 official training molecules, using only observed labels and experimental intervals for each CYP. The H6 feature-only full OOF bank and query arrays match the frozen grid1 heads (15 leaves / depth 4); the four model/prediction receipts and historical H6 reconstruction were verified. The corrected-native banks appear only in historical reconstruction checks, never as the new candidate's base.

The fixed serving operator retains the original reference means, scales, offsets and floor. Nothing is estimated from the new candidate's predicted distribution. Lambda0 reproduces original served values to 3.55×10⁻¹⁵; a byte-identical control is retained separately. No per-row correction was added to force equality. The source P5 operator record also carries historical feature weights as provenance; only its reference means, scales, offsets and floor are applied here. The new coefficients are exclusively those in COEFFICIENTS.json.

This preserves the historical raw H6 feature semantics. It is not the P7 direct-fusion model or the later feature-unit repair.

## Evidence supporting preparation

P5b's refitted combination gives raw ST-RAE .620861 on own750 and .577113 on briford529, versus .626205/.622655 for the original native. Briford improves all five metrics with conditional intervals favoring the mixture. Own750 is mixed: ST-RAE improves as a point estimate, but its interval includes zero and MAE/R² worsen. Refitting is not consistently better than the fixed-P5 coefficients. See `../READOUT.md` for every metric and interval.

These are reused, overlapping historical development cohorts, not independent confirmation. The original native and H6 experts retain their documented source and pretraining limitations. Full-training OOF scores used to fit these final coefficients are meta-training evidence, not a new validation estimate.

## Comparison with the best and bad last submission

The recorded live scores were .4425 for the preserved incumbent 349165… and .4616 for the last H6 submission 91fa8b…. No candidate score has been measured. The following compares **predictions**, not errors against hidden labels:

| CYP | Mean absolute change from best | Mean absolute change from bad last | Candidate SD | Best SD | Bad-last SD |
|---|---:|---:|---:|---:|---:|
| 1A2 | .25232 | .22326 | .98194 | 1.21357 | 1.24658 |
| 2C9 | .15401 | .16160 | .83245 | .97488 | .99961 |
| 2D6 | .08459 | .09778 | .81192 | .90000 | .90000 |
| 3A4 | .15294 | .13374 | 1.00971 | 1.11622 | 1.12759 |

The candidate is narrower in every target. The same frozen operator does not enforce the same output means or spreads when its raw input changes. Overall mean absolute prediction differences are .16097 from the best and .15410 from the bad last submission. Proximity to either file does not establish better or worse predictive quality. All per-CYP means, correlations and differences are in `results/UNLABELED_COMPARISON.csv`.

## Execution and verification

- ORX node `a0bdeada-bc2d-41a3-b02e-83a62c0e13b5`.
- Run `ea18ec6c-3611-452b-bd03-fb4a9ec3edee`, source `d94b59cfd1a95fc00ed62c1de4a56bc8f7702f03`.
- Four scalar coefficients; zero base fits, feature changes, calibration fits or paid resources.
- Independent LP objective error ≤3.33×10⁻¹⁶; raw and served query reconstruction errors 0.
- `VERIFICATION.json`, `stage/manifest.json`, `results/{COEFFICIENTS.json,SERVING_OPERATOR.json,VALIDATION.json,LAMBDA0_CONTROL.json,COMPLETE.json}` pin the inputs, coefficients, scorer, operator and checks.

This artifact is a concrete candidate for private review. It does not silently replace the incumbent or imply top-ten performance.
