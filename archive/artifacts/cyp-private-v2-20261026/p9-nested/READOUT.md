# Nested ensemble test: small, inconsistent changes; no promotion

The three-expert blend gives small raw ST-RAE point improvements over the original incumbent on both development cohorts, but the uncertainty intervals include zero, the own750 secondary metrics deteriorate, and Atom-JEPA's incremental effect differs between cohorts. This does not demonstrate a stable replacement gain. The tested post-normalization/PCA96 branch stops here without promotion or further tuning.

The result is not evidence that Atom-JEPA can never help: adding it improves briford529 relative to the predeclared native+ADME control, while hurting own750 relative to that same control. The materially different published pre-normalization/PCA128 route remains untested; see `../representation-prep/ATOM_JEPA_SOURCE_FIDELITY.md`.

## Raw results

Lower ST-RAE, MAE, and RMSE are better; higher R², Spearman, and Kendall are better. Macro values average the four CYPs.

| Cohort | Arm | ST-RAE | MAE | R² | Spearman | Kendall | RMSE |
|---|---|---:|---:|---:|---:|---:|---:|
| own750 | Unchanged original native | .626205 | .524829 | .468910 | .670769 | .491380 | .712273 |
| own750 | Native + ADME | .622072 | .525819 | .465279 | .669707 | .491565 | .714698 |
| own750 | Native + ADME + Atom-JEPA | .624848 | .528245 | .461262 | .666618 | .489184 | .717357 |
| briford529 | Unchanged original native | .622655 | .471782 | .390653 | .650512 | .477510 | .659825 |
| briford529 | Native + ADME | .627927 | .473704 | .392669 | .655793 | .480698 | .659588 |
| briford529 | Native + ADME + Atom-JEPA | .619194 | .471393 | .396957 | .656604 | .481750 | .657335 |

Three experts minus incumbent, raw macro ST-RAE:

- own750: −.001357, conditional 95% interval [−.017500, +.015225]. All four other official macro point metrics worsen.
- briford529: −.003461 [−.024908, +.021340]. All five official macro point metrics improve slightly, but all five intervals against the incumbent include zero.

The incremental Atom-JEPA comparison is three experts minus the native+ADME boundary control:

- own750: ST-RAE +.002776 [−.001053, +.006208]. MAE, R², and RMSE also worsen; their conditional intervals exclude zero in the unfavorable direction.
- briford529: ST-RAE −.008733 [−.014624, −.003620]. This is positive evidence of complementarity in that particular reused cohort, not a general improvement established across both regimes.

All per-CYP metrics and paired intervals are retained in `results/blend-metrics.csv` and `blend-paired-deltas.csv`. The small favorable ST point changes against the incumbent are not being relabeled as zero, nor are they sufficient evidence here to replace a known successful artifact.

## How coefficients were learned

The two outer-training pools contain 4,155 and 4,375 molecules. The run generated 80 new conditioning/prediction calls: two representations × two outer-training pools × five fixed inner folds × four primary CYP targets. Every new inner fit excludes the full outer query, and train-side normalized-parent/connectivity/audited strict-equivalence exclusions were checked. Scaler/PCA fitting uses only actual inner-training rows. No global OOF predictions were substituted for this nested stage.

The same fixed PCA96 and two-estimator TabICL settings were used for ADME600 and the post-final-normalization Atom-JEPA256 bank. Only official primary pIC50 labels enter the readout objective; missing primary labels are not negatives. The 16 previously frozen full-context P9 outer-query vectors remain the deployment route for these development cohorts.

For each CYP, a linear program learns nonnegative weights summing to one, with no intercept, from that outer-training pool's OOF predictions and experimental intervals. It minimizes mean distance outside the interval; the training ST-RAE denominator is constant for that CYP, so the minimizers are the same. The native+ADME boundary face was declared before fitting as a control. There was no coefficient grid, negative cancellation, or outer-driven column selection. Weights were saved before query truth was selected for scoring.

Atom-JEPA receives the following learned weights, expressed as a fraction of the three-expert mixture:

| CYP | own750 training pool | briford529 training pool |
|---|---:|---:|
| 1A2 | .10748 | .10475 |
| 2C9 | .00456 | .01606 |
| 2D6 | .11152 | .11779 |
| 3A4 | .00777 | .05213 |

The full coefficients and training objectives are in `results/{own750,briford529}-weights.json`. These coefficients are not causal feature importances.

## Fixed serving-map diagnostic

The same previously frozen original affine map and floor were applied to every arm, without recomputing maps from candidate predictions or query outcomes. Incumbent identity against the old served vectors was verified.

| Cohort | Incumbent | Native + ADME | Three experts |
|---|---:|---:|---:|
| own750, served diagnostic ST-RAE | 1.062888 | 1.083805 | 1.075729 |
| briford529, served diagnostic ST-RAE | 1.069202 | 1.066152 | 1.042340 |

These values are **not faithful estimates of deployment performance**: the published blind-population placement is being applied to training-derived local cohorts with different target distributions. This was established in P1. The lane is retained to expose operator sensitivity, not to claim a leaderboard gain or fit a new calibration.

## Verification and limits

The original native expert was not retrained or replaced. Its preserved outer-training component OOF banks and original query vectors were audited before fitting; all 40 component-fold prediction receipts were verified, and query aggregation matches the historical reference. Exact original native predictions are unchanged in the baseline arm. See `NATIVE_PROVENANCE.md` for the retained public-source association, strict-tautomer, and differing component-fold limitations. Clean nesting of the new readouts does not retroactively certify the historical expert as perfectly leakage-free.

Independent verification checked all 20 saved PCA training/validation memberships, confirmed outer-query exclusion, reconstructed the query blends, rescored all five official metrics plus RMSE in both lanes, and checked the real two-expert LP objectives against their weighted-median solution. Maximum metric discrepancy was 2.22×10⁻¹⁶. Positive/negative synthetic tests also check simplex constraints, missing-label handling, and row-permutation objective invariance.

The 1,000-replicate paired scaffold bootstrap holds the fitted coefficients fixed. It describes conditional query-sampling uncertainty, not coefficient-estimation uncertainty, new training seeds, or future datasets. Both outer cohorts have already been reused, overlap by 143 molecules, and differ from the dense blinded analogue regime. No hidden labels were accessed.

## Execution and artifacts

- ORX node `84ed9b4e-a1db-4dc4-851c-21da05b59842`.
- Run `f23c6d16-ebcb-47e4-aaf0-43feb78f69df`.
- Source `8f4e87ab0b19869349f4b13be52f20a550cceb02`.
- Runtime 992 seconds on local CPU; peak RSS 2.59 GB, below the available-memory guard. No paid resources.
- `VERIFICATION.json`, `BLEND_TESTS.json`, `stage/manifest.json`, and `results/BLEND_COMPLETE.json` preserve the checks and provenance.
- `results/` contains all 80 inner predictions, assembled inner OOF banks, exact coefficients, and raw/fixed-map query vectors.

No final blind fit, new submission, publication, or additional experiment was launched after this result. The incumbent remains protected.
