# P8a — training-only condition-map feasibility

**The active-potency/screen relationship is predictive within the paired subset, but the prespecified ridge spline is worse than a simple affine map in every inner comparison.** This does not establish any benefit for direct-pIC50 prediction or justify the20 graph fits yet. No new data, GPU rental or public output was used.

ORX experiment87fd60af-c438-4116-a7cc-0ca027f5985e, run0191f3b8-5d6b-4a7a-8a8d-8357345e02de, committed sourcec199c53. Fixed command `bash run.sh`, local CPU. Scientific execution2.12seconds; ORX reports5seconds total. The node is now frozen. Source and effective configuration are identified in `orx-run.log`, whose final summary is line22; exact log/output/input hashes and independent membership checks are in VERIFICATION.json.

## What ran

Five repaired P7 outer partitions; only each outer partition’s post-purge **training** rows were admitted. Each training set comprises three original fold groups. Leave each group out in turn, with approved chemical-equivalence counterparts purged from its fitting side. On each CYP’s paired active-pIC50/screen cells fit a mean, ordinary least-squares affine map, and fixed-quartile piecewise-linear ridge spline: alpha1 for mean standardized squared residual loss, unpenalized intercept, three inner-fit25th/50th/75th percentile knots. No hyperparameter search, monotonicity constraint or kinetic equation.

Total180 small fits=5outer×3inner×4CYP×3models. Knot/scaler/coefficient fitting used inner-fit rows only. Outer stopping/test outcomes never entered fitting, calibration, selection or diagnostics. All models used identical paired rows. The approved inner purge was checked but removed0 rows from these particular paired subsets; this is an observed count, not a disabled check.

The preparatory hypothesis had described20 full-training calibrators; cross-fitting requires60fit subsets per model rather than20. That expands bookkeeping, not the scientific model grid or paid scope.

## Held-out screen error

Native log2FC units. The pooled occurrences below repeat a molecule across eligible outer training partitions; they are **not independent replicates**. No significance or equivalence claim is made from their multiplicity.

| CYP | Unique paired molecules evaluated | Mean MAE | Affine MAE | Fixed spline MAE | Affine RMSE | Spline RMSE |
|---|---:|---:|---:|---:|---:|---:|
|1A2|1413|0.5153|0.2275|0.3198|0.3007|0.4025|
|2C9|1285|0.3679|0.1839|0.2232|0.2319|0.2611|
|2D6|1495|0.6598|0.4151|0.4386|0.5039|0.5147|
|3A4|1815|1.2079|0.5342|0.6016|0.6494|0.7319|

For each CYP, spline MAE is worse than affine MAE in15/15 inner comparisons. Mean spline-minus-affine differences across these comparisons are0.0925/0.0394/0.0236/0.0672, respectively; all individual differences are positive. The spline improves on the mean in every comparison. Exact fold/group readouts and adverse cases are retained in results/metrics.csv and paired-map-comparisons.csv.

This is a comparison of **OLS affine versus strongly regularized spline**, not a clean theorem that the relationship is linear. The fixedalpha1 penalty, hinge basis and model capacity differ. Do not tune alpha after this result and relabel the rerun a prespecified success. The result answers the planned feasibility check: the chosen nonlinear map has no empirical advantage over the simple comparator here.

## Shape, extrapolation and stability

All60 fitted spline maps were decreasing over all their piecewise-linear segments without an imposed monotonicity constraint. Raw segment slope ranges across fits are:

| CYP | Minimum slope | Maximum slope | Paired validation occurrences outside inner-fit active range |
|---|---:|---:|---:|
|1A2|−0.3711|−0.2316|0.283%|
|2C9|−0.3706|−0.1545|0.260%|
|2D6|−0.6442|−0.2248|0.268%|
|3A4|−0.9877|−0.3847|0.349%|

On each outer-training-only active-potency grid, the maximum separation among its three inner-fitted spline predictions was at most0.0902/0.0810/0.0753/0.1209 log2FC across the five outer sets. Saved grids and coefficients expose all tails; this is descriptive stability, not a confidence interval. Extrapolation cases are few and their errors remain in the outputs; no generalization claim rests on their average.

The paired subset is selected coverage. Most screen molecules lack active pIC50 for a given CYP. The low extrapolation percentages above concern **paired validation measurements**, not the unknown active-potency distribution of all unpaired screen molecules or the blind test set. Successful cross-fit does not validate this map for those molecules. The observed decreasing shape is an empirical relationship on released readouts, not a calibration of inhibition fraction or a proof of a Hill mechanism.

## Consequence for the next decision

A measured active-potency/screen association exists, so the routing idea is not based on a wholly flat nuisance relationship. However, the selected nonlinear spline offers no advantage and cannot yet support a costly condition-routing claim. The free-active-head versus no-active-supervision comparison remains a distinct potential test of added labels. A constrained affine observation model would test a different, simpler route and must be explicitly proposed/approved; it must not be silently substituted into the four-arm neural plan after seeing this result. Direct+delta affine heads alone remain a reparameterization, as explained in NEXT_CONDITION_HYPOTHESIS.md.

The fixed spline’s worse screen prediction does not prove condition-aware learning cannot help, and its better-than-mean screen error does not prove it will help direct prediction. The +NADPH/−NADPH distinction, missing efficacy information, uncertain log2FC/Emax normalization and selected paired coverage remain. No kinetic or causal inference is made.

**Stop this bounded diagnostic here.** No additional spline search, new data, graph fits or rental was performed. Root retains the next model/spend decision within the unchanged$10 campaign cap.

## Verification and peer review

Independent read-only verification recomputed every recorded MAE from saved predictions, checked every input/output hash, verified all inner validation groups were excluded from fitting and every used row belonged to its outer training set. No chemical-equivalence fit/validation overlaps remain. All predictions are finite.

Challenge-audit reviewed p8a.py/config/run.sh and found no material blocker: correct inner purges, training-only scaling/knots, identical comparator samples, and correct mean-MSE ridge. It emphasized OLS-versus-ridge and repeated-occurrence distinctions, plus the paired-coverage limitation, all retained above. Feedback arrived after the brief local run; it requested no repair or extra fits. The prior request for review and its timing are preserved in the task messages.

Files: results/{summary.csv,metrics.csv,predictions.csv,membership.csv,models.json,map_grid.csv,complete.json}; VERIFICATION.json; map-stability.csv; paired-map-comparisons.csv; orx-run.log; verify_results.py. Full scientific source and fixed config are preserved on the committed ORX node. Everything remains private.
