# P5b: the incumbent-anchored H6 signal persists; coefficient refitting adds little

Holding the original native expert and frozen H6 feature-only expert fixed, refitting the four blend coefficients on ORIGINAL native outer-training OOF yields raw ST-RAE .620861 on own750 and .577113 on briford529. Both point estimates improve over the original native reference. The briford improvement is consistent across all five metrics; own750 remains mixed, with worse MAE and R². Refitting does not consistently improve on the already-positive fixed-coefficient P5 combination.

No base model, feature value, or calibration was changed. The exact .4425 incumbent artifact remains untouched. This is a promising historical-expert combination for private candidate review, not a demonstrated new leaderboard score or independent fresh validation.

## Raw results

| Cohort | Arm | ST-RAE | MAE | R² | Spearman | Kendall |
|---|---|---:|---:|---:|---:|---:|
| own750 | Original native | .626205 | .524829 | .468910 | .670769 | .491380 |
| own750 | Fixed P5 coefficients | .619657 | .529176 | .454548 | .672807 | .492951 |
| own750 | Refit on original OOF | .620861 | .529889 | .454110 | .671215 | .492039 |
| briford529 | Original native | .622655 | .471782 | .390653 | .650512 | .477510 |
| briford529 | Fixed P5 coefficients | .577447 | .460236 | .414643 | .668099 | .492917 |
| briford529 | Refit on original OOF | .577113 | .460044 | .414620 | .669522 | .493767 |

Refit minus original, raw macro ST-RAE:

- own750: −.005344, conditional 95% interval [−.025537, +.011351]. MAE changes +.005060 and R² −.014799; their intervals also include zero.
- briford529: −.045542 [−.072880, −.021151]. All five metric intervals favor the refit mixture over original native in this particular cohort.

Refit minus fixed P5 is much smaller and inconsistent: own750 ST-RAE +.001204 [.000008, .002413], briford529 −.000334 [−.001922, .001046]. Thus the substantive signal is the existing H6 expert addition to the preserved original native, not a large gain from coefficient refitting.

## Matching inputs and fitting scope

The original native training OOF/query banks were independently reconstructed and pinned earlier; they are the ORIGINAL outer-refit recipe, not the corrected native or a global-OOF substitute. H6 matching feature-only OOF files contain exactly 4,155/4,375 training rows and the corresponding 750/529 query rows. Their observed-label masks match the official table. The frozen H6 selection is grid1, 15 leaves / depth 4 in each cohort, and its stored OOF scores reproduce independently. No H6 hyperparameter or feature was reselected.

For each CYP, one feature coefficient w in[0,1] minimizes the training-OOF soft-interval objective through the existing weighted-endpoint-median rule, choosing the smallest minimizer. The prediction is `(1−w)*original_native + w*H6_feature_only`. Coefficients were persisted before query scoring. Only the outer-training labels and intervals enter fitting.

| CYP | own750 refit w | briford529 refit w |
|---|---:|---:|
| 1A2 | .54952 | .53877 |
| 2C9 | .36711 | .38568 |
| 2D6 | .39423 | .32998 |
| 3A4 | .42020 | .38295 |

Original native and fixed-P5 control CSVs are retained byte-for-byte. Reconstructed mixtures and the frozen original operator match their controls within floating-point precision. An independent linear-program objective check agrees with the weighted median to 7.22×10⁻¹⁶, and all five query metrics independently reproduce within 2.22×10⁻¹⁶.

## Serving diagnostic and limits

The unchanged original full-context affine map/floor gives diagnostic ST-RAE .999281 and .897381 for the refit mixture, versus 1.062888 and 1.069202 for the native reference. No operator parameter was estimated from the candidate or query outcomes. These numbers are **not deployment estimates**: applying published blind-population placement to training-derived local cohorts creates the known P1 population mismatch.

Bootstrap uses the original P5 grouping convention: non-isomeric Bemis–Murcko groups, with acyclic compounds grouped by connectivity key; 1,000 paired draws, seed 20261026. It holds the fitted coefficients fixed. The two repeatedly used cohorts overlap by 143 molecules. Historical native source/purge limitations, differing component folds, and H6 development selection remain; neither the bootstrap nor this coefficient refit makes the evidence independent of that history.

## Artifacts

- ORX node `41f8cabc-a698-4cba-8270-f06f89f63cfc`, run `f77263cb-82ef-47ff-8ecd-0767aaf881dd`, source `82c2cc0bfe38314e8fa8d53b371f9da89ebcc456`.
- Runtime 14.84 seconds, eight scalar fits, zero base fits, zero paid resources.
- `VERIFICATION.json`, `stage/manifest.json`, `results/{metrics.csv,per-cyp-metrics.csv,paired-deltas.csv,IDENTITY_CONTROLS.json}` and both weight receipts preserve the evidence.
- No publication or submission occurred. Private candidate preparation is a separate, authorized step; it cannot silently replace the incumbent.
