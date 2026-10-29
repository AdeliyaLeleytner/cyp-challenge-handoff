# Why the fixed P7 fusion run is worse

The matched fusion model makes a narrower range of predictions and also orders compounds less well. A simple change of scale cannot repair its rank loss. This is an observed failure pattern, not proof that any particular ADMET endpoint caused it. No new model was fitted, no checkpoint inference was run, and no calibration was estimated from held-out outcomes.

This is one paired five-fold experiment on the official primary assay observations. The 31,641-row mixed assay pool supplied the original training; the diagnostic readout contains all 4,905 official molecules and 6,525 observed primary target cells. Missing experimental cells remain missing. Test-fold outcomes were not used for checkpoint selection; stopping rows are also excluded from the labeled-neighbor support calculation. The models share their initial parameters and batch-normalization buffers. Zero descriptors is the same-capacity control; this is scratch Chemprop, not CheMeleon fine-tuning or a reproduction of the original native leaderboard ensemble.

## Overall errors and useful units

Macro values are the arithmetic mean of four per-CYP metrics, not a pooled-cell score.

| Metric | Zero descriptors | ADMET fusion |
|---|---:|---:|
| ST-RAE ↓ | 0.674456 | 0.702571 |
| MAE, pIC50 ↓ | 0.537914 | 0.556678 |
| R² ↑ | 0.394981 | 0.346449 |
| Spearman ↑ | 0.612771 | 0.572605 |
| Kendall ↑ | 0.442480 | 0.410951 |
| RMSE, pIC50 ↓ | 0.731901 | 0.761447 |
| Within factor 2 of point IC50 ↑ | 39.74% | 38.58% |
| Within factor 10 of point IC50 ↑ | 85.62% | 85.24% |
| Prediction inside experimental pIC50 interval ↑ | 31.30% | 29.82% |
| Mean distance outside interval, pIC50 ↓ | 0.293473 | 0.306442 |

The factor-2 and factor-10 readouts use absolute pIC50 errors ≤log10(2) and ≤1, respectively. They are regression accuracy descriptions, not invented inhibitor/non-inhibitor classes. Interval coverage is coverage of the experimental parameter interval, not a predictive uncertainty interval.

The previously frozen, paired, 1,000-replicate scaffold-within-fold bootstrap gives macro fusion-minus-zero ST-RAE +0.028115, conditional 95% interval [0.011602, 0.043123]; MAE +0.018764 [0.010893,0.026176]. These quantify conditional variation of this saved OOF comparison. They do not include new training seeds, alternative splits, hidden-test shift, or all previous development selection. CYP1A2 ST-RAE worsens in all five folds; other CYPs have mixed fold signs. The pooled increase is +0.062681 for 1A2, versus +0.012042/+0.023601/+0.014135 for 2C9/2D6/3A4. Only 1A2's individual ST interval excludes zero in the existing bootstrap.

## Dispersion and ordering both change

| CYP | SDpred/SDtruth, zero → fusion | Spearman, zero → fusion | Bias, zero → fusion |
|---|---:|---:|---:|
| 1A2 | .569 → .494 | .552 → .476 | +.0637 → +.0967 |
| 2C9 | .695 → .660 | .679 → .666 | +.0614 → +.0610 |
| 2D6 | .462 → .366 | .427 → .372 | +.0254 → +.0242 |
| 3A4 | .789 → .758 | .793 → .777 | +.0841 → +.0947 |

Both models already under-disperse relative to observations, especially for 2D6; fusion accentuates this. This is compatible with stronger shrinkage toward typical assay values, but does not establish a teacher-shortcut cause. Observation noise also contributes to the truth SD, so unity is not an asserted optimal SD ratio. The Spearman/Kendall declines independently demonstrate poorer ordering, which any strictly increasing affine serving map preserves. No outcome-fitted rescaling is performed here.

Using population moments, the identity is

MSE = bias² + (SDpred − SDtruth)² + 2 SDpred SDtruth (1 − Pearson).

The main run and a separate verifier reconstructed it for every CYP/fold and pooled endpoint; maximum numerical error was 4.44e−16 in the run. Fusion-minus-zero decomposition:

| CYP | ΔMSE | Δbias² | Δsquared SD gap | Δcovariance term |
|---|---:|---:|---:|---:|
| 1A2 | +.116486 | +.005284 | +.074369 | +.036834 |
| 2C9 | +.017065 | −.000039 | +.013939 | +.003165 |
| 2D6 | +.026570 | −.000058 | +.094304 | −.067676 |
| 3A4 | +.029587 | +.001904 | +.016655 | +.011028 |

These are numerical terms, not percentages of causation. In particular, 2D6's covariance term decreases while its Pearson correlation worsens: the term is multiplied by the shrinking prediction SD. It would be wrong to call this improved ordering. Bias changes are small compared with the dispersion/covariance changes.

## Is the problem confined to a source or neighborhood?

The 530 molecules absent from the released single-concentration table have only 3A4 primary outcomes. In this stratum, MAE worsens .4221→.4505 and ST-RAE .4483→.4961. Among the other 1,805 measured 3A4 observations, MAE also worsens .5468→.5583, while ST-RAE changes .4893→.4944. Thus the source-coverage stratum contributes, but is not the only affected group. These are observed release-coverage strata; no unverified reason for missing assays is assigned.

Nearest support means a molecule with the SAME measured CYP target in that fold's actual training rows. The original fingerprint convention is Cleanup+FragmentParent, Morgan radius2/2048bit/no chirality; the pinned 4,905×4,905 matrix was independently spot-checked at 576 entries. Most observations have low measured structural support: only 1/0/4/27 molecules reach Tanimoto≥.7 for 1A2/2C9/2D6/3A4. This is a scaffold-heldout, sparse-assay readout, not the dense catalog-analogue test regime.

There is no universal rule that fusion hurts only the least supported compounds. For 1A2 it worsens MAE in both large support bins below .4 and .4–.6. For 3A4 the .4–.6 bin worsens .4902→.5160 (n=1,188), whereas the .7–.8 bin improves .4685→.3901 (n=22). The tiny ≥.6 bins for some CYPs also contain improvements, but cannot establish a reliable gating rule. All exact strata and counts, including empty strata and label patterns, are retained in `results/metrics-by-stratum.csv`.

## Close analogues: limited support and contrary cases

Pairs must be distinct official molecules, both in the same test fold, with both measured at the same CYP and Tanimoto≥.7. These are co-held-out pairs, not query-versus-training pairs. There are only 120: 11 for1A2, **zero for2C9**, 12 for2D6, 97 for3A4. The pairs are dependent and do not constitute a new dense benchmark.

- 1A2: close-pair delta MAE improves .402→.376 and sign concordance stays8/11, contrary to its overall deterioration. Only16 distinct molecules support these11 pairs.
- 2D6: sign concordance drops7/12→4/12, and delta MAE .505→.579; only16 distinct molecules. This supports checking local ordering but is too small to generalize broadly.
- 3A4: sign concordance drops74/97→72/97; delta MAE .389→.396. Among59 pairs with non-overlapping experimental intervals, delta MAE slightly improves .457→.450 even while sign concordance falls49/59→46/59.
- Point-estimate ≥10fold contrasts number2/0/2/11. Requiring the entire experimental intervals to be separated by ≥1pIC50 leaves0/0/1/5. All six of these CI-supported strong contrasts retain the correct direction in both models; their difference magnitudes remain imperfect. This is insufficient evidence that fusion universally destroys activity-cliff recognition.

`results/close-pairs.csv` preserves all IDs, original SMILES, predictions, signed differences and intervals. Chemistry peer analysis can join teacher outputs by these exact IDs without changing the pair definition. No arbitrary binary activity threshold or pair-independence inference is introduced.

Fusion improves absolute error on 3,109 of6,525 measured cells (~47.65%), despite worsening the macro metrics. Saved post-fit examples include improvements for1A2 OCNT-2328824 (truth5.3786; zero3.6980; fusion5.2350),2D6 OCNT-2318399 (4.6169;6.0001;4.4770), and3A4 OCNT-2312856 (2.9370;4.3821;3.0543). Equal numbers of the largest improvements and deteriorations, with exact SMILES, are in `results/paired-error-examples.csv`; these are illustrations, not selection evidence.

## Competing explanations and discriminating next evidence

1. **A scale/regularization change plus altered representation.** The numerical SD contraction is large, particularly2D6, while bias is nearly unchanged. A pure scale-only explanation is contradicted by the rank declines. Checkpoint inference that separates graph and descriptor contributions could show whether graph representations changed or whether the final head mainly contracts their outputs. Such interventions are not performed in this diagnosis and require care because setting standardized descriptors to zero need not represent a chemically plausible molecule.
2. **Teacher signal helps broad assay classes but fails quantitative local ordering.** ADMET teacher probabilities may contain useful global inhibition associations yet insufficient graded information for these pIC50 assays. Predicts weaker teacher-delta concordance inside chemically close, experimentally ordered pairs than global associations. The chemistry agent's fixed-pair analysis directly tests this descriptive prediction. It cannot infer teacher-training overlap or establish that saturation causes the model failure.
3. **Mismatch between sparse assay/fold support and where teacher features help.** Underrepresented assay strata and structurally remote measured support may change the feature/graph tradeoff. The current results partially support heterogeneity, but reject a simple 'only low-support molecules worsen' story. A prospective, predeclared validation regime or training-side gating study would be needed before applying a neighborhood-dependent rule; no outer-outcome-selected gate is authorized here.

The practical consequence is to retain the matched zero-descriptor baseline for this particular architecture/training recipe and not describe direct120-feature concatenation as an improvement. This negative run does not negate the earlier useful tabular-readout/ensemble route, which estimates a different model and combination. Other readouts or regularization changes remain hypotheses, not established fixes.

## Reproducibility and visual artifacts

- ORX node `16c9a928-373f-41de-94fc-d9a333534601`; run `07bd32c8-6e52-4139-90f1-e381b856c7fc`, statusdone.
- Committed scientific source `aaf0cee3d12c8ccd17fe04bc10d5a7326fe0beb8`; fixed `bash run.sh`; cached analysis runtime4.79s, no paid resources.
- `results/COMPLETE.json` and `VERIFICATION.json`: exact ID/SMILES/hash/initial-state, official metric parity and independent population-MSE/row/pair checks.
- `figures/{observed-predicted,paired-error,support-error}.{pdf,svg,png}`: rendering-only derivatives; render receipt pins input and rendering source. All three PNG previews were visually checked; all three style audits clean. The initial frozen run's wide exploratory layouts remain in results for provenance; the readable 6.75inch derivatives are the intended report figures.
- `render_diagnostics.py` and `verify_diagnosis.py` are reproducible private post-run rendering/verification, without model execution.
- P9 remains paused with its pinned Atom-JEPA staging preserved. Nothing was published or submitted.

Matrix precision note: six cached pair similarities encode exact0.7 as float32 value0.699999988. Independent fresh RDKit recomputation verified every one of the120pairs has exact Tanimoto>=0.7; no pair membership changed.

## Fixed-pair teacher readout added after peer analysis

The chemistry agent joined the same120 frozen pairs to the corresponding ADMET CYP-inhibitor probabilities (`teacher-close-pair-summary.csv`, `teacher-pair-receipt.json`). For1A2/2D6/3A4, the teacher signed-difference Spearman is .500/.762/.127 and correct point-estimate direction10/11,8/12,49/97. Exactteacher ties are0/0/6. These descriptive pair comparisons share the earlier small/dependent-support limitations.

This weakens a blanket 'the teacher contains no local information' explanation. In particular, the12 2D6pairs have substantial teacher ordering information, whereas the learnedfusion predicts the correct direction for only4/12. It does not identify why the trainednetwork failed to use it. Conversely,3A4teacher local deltaassociation is weak over97pairs despite a strong global teacher association. Allfive3A4 andone2D6 interval-supported≥10fold contrasts are ordered correctly by theteacher; the2D6probability difference is only.00102. Small or saturated probabilities therefore do not by themselves demonstrate lost ordering, although they may make quantitative use harder. Neither teacher probabilities nor their differences are calibrated pIC50 measurements. This evidence motivates separating information availability from how the fusion model uses it, rather than asserting a universal saturation cause.
