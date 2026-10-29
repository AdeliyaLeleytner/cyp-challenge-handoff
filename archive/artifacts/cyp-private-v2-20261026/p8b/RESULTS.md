# P8b — separate nonlinear basis from ridge shrinkage

**The unpenalized three-knot spline predicts held-out screen values better than the affine model in all60 paired inner comparisons. The alpha1 penalty worsens both bases.** This resolves P8a’s specific confound: its adverse spline result did not establish that a nonlinear relationship was unhelpful. It still does not establish improved direct-pIC50 predictions or a kinetic mechanism.

Private local ORX sibling experiment8a10e50b-669b-46ae-8f07-1c34a081630f; runbe3f0cce-e023-441f-a9a0-c16e61bd1682; source970c6ad; fixed `bash run.sh`. CPU execution3.19seconds, ORX5seconds. No GPU, acquisition, cost or public writes. P8a remains unchanged.

## Fixed factorial and observations

The candidate set was frozen before launch: mean reference; affine and identical three-quartile-hinge spline, each at alpha0 or alpha1. Same mean-MSE penalty convention, unpenalized intercept, training-only normalization/knots, P8a original-group cross-fit and strict chemical purges. Membership CSV is byte-identical to P8a. Alpha0 uses `np.linalg.lstsq` on the design, avoiding singular normal-equation inversion; rank is recorded. Every observed affine design has rank2 and spline design rank5.

Held-out screen MAE in native log2FC units:

| CYP | Mean | Affine alpha0 | Affine alpha1 | Spline alpha0 | Spline alpha1 |
|---|---:|---:|---:|---:|---:|
|1A2|0.5153|0.2275|0.3285|**0.1651**|0.3198|
|2C9|0.3679|0.1839|0.2518|**0.1235**|0.2232|
|2D6|0.6598|0.4151|0.5008|**0.3173**|0.4386|
|3A4|1.2079|0.5342|0.7518|**0.3069**|0.6016|

These pooled descriptions repeat molecules across outer training partitions and are not independent replicate estimates. They were **not used for global map selection**. All complete per-outer/per-inner outcomes remain in metrics.csv and factorial-paired-comparisons.csv.

- At alpha0, the spline improves MAE in60/60 comparisons. Mean inner differences(spline−affine) are−0.0622/−0.0606/−0.0979/−0.2276 for1A2/2C9/2D6/3A4.
- Alpha1 worsens each basis relative to its own alpha0 in60/60 comparisons. This fixed penalty is too restrictive for these paired relationships under the specified scaling; no broader alpha optimum is claimed or searched.
- At alpha1, spline beats affine in59/60 comparisons; one adverse difference is+0.000379. Preserve that case rather than claiming universal superiority under every penalty.
- P8b mean, affine0 and spline1 saved predictions exactly reproduce P8a’s corresponding outputs. The new outcome comes from the newly authorized matched penalty contrast, not a changed sample.

## Strictly local selector and frozen maps

For each of the five outer folds and each CYP independently, aggregate its three inner validation groups’ absolute errors with weight proportional to their paired row counts. Select only from the five committed candidates; exact ties follow mean,affine0,affine1,spline0,spline1. Refit the chosen map on **that outer fold’s full post-purge paired training set**, re-estimating the same training-only transforms and quartile knots. No outer stopping/test outcomes or global pooled candidate scores enter this decision.

All20 local selectors chose spline0. They made20 separate local decisions even though the selected label agrees. Save these fitted maps rather than replacing the protocol with a single globally fitted spline. The selected inner MAE is a criterion used for choosing the map, **not an unbiased estimate of the selector’s performance**. We have not evaluated these selected maps on outer stopping/test outcomes.

Artifacts:

- `results/selected_maps.json`, SHA256 `be16dd34c6776312e73707acd0c0e0dff1823c32267b20f76af8263f3c6aa9d8`:20frozen coefficients, knots, scales, train ranges, local candidate scores and membership digests.
- `results/selector_membership.csv`, SHA256 `c35da59a6d34041e74c57dea996d7395e3022669bb102d2fc121162a834aab64`:exact training IDs/request aliases used for each refit.
- `selector-verification.csv` and `VERIFICATION.json`:independent local-choice recomputation, transform checks and least-squares residual verification without refitting.

## Shape, extrapolation and contrary cases

Fifty-nine of60 inner unpenalized splines are decreasing on all segments. One2D6 inner map(outer3, held original group1) has a small positive low-potency-tail slope0.0134 log2FC/pIC50, followed by negative slopes. No monotonicity was forced or repaired. All20 selected full-training maps happen to have decreasing segments.

Only12/10/12/19 repeated validation occurrences for1A2/2C9/2D6/3A4 fall outside the corresponding inner-fit active range (~0.26–0.35%). For these sparse tail occurrences, spline0 MAE is0.141/0.140/0.355/0.480. The3A4 alpha1 spline does better in that tail(0.295), despite being worse overall. These few, repeated cases do not establish reliable general extrapolation. All errors and exact identities are retained in predictions.csv.

Across an outer-training-only common physical potency grid, maximum separation among its three inner spline0 maps reaches0.144/0.126/0.237/0.560 log2FC respectively. The strongest3A4 average improvement coexists with the largest tail/map variation. Saved grid values and coefficients permit inspection; these ranges are descriptive sensitivity, not credible intervals.

The paired subset is selected: most screen rows do not have measured active pIC50 for that CYP. The small measured-range extrapolation rate does not describe the unpaired molecules or blind750. A future graph model would supply **predicted** active potency to this map, whereas P8b supplies measured/fitted active potency; prediction error and distribution compression can change the map’s behavior. P8b has not tested that transfer.

## Consequence and limits

This result supports retaining a nonlinear **empirical** active-condition→screen observation map as a feasible candidate for an explicitly authorized condition-routing experiment. It does not select a new direct-inhibition model, establish causality or justify immediate20-fit spending. The free-head/no-active-label, free-head/active-label, active-route and wrong-direct-route contrasts remain necessary to separate label coverage, generic regularization and condition specificity.

No Hill equation, inferred IC50 bound, nonnegative condition-shift rule, Emax inversion or kinetic-rate claim was introduced. Signed screen values and missingness remain intact. Nuisance training is strictly outer-local and uses the same experimental source purges. The unchanged$10 campaign cap applies; graph fits remain unapproved.

## Verification and source evidence

VERIFICATION.json checks all result and input hashes; identical P8a memberships; no inner fit/validation equivalence overlap; every row inside its permitted outer training partition; all recorded MAEs reconstructed from saved predictions; all20selector decisions recomputed from their own inner errors; final refit scales/knots/ID hashes and normal-equation residuals verified. Both effective configuration and final summary are present in the copied ORX log(line22 final summary).

Challenge-audit’s prereun review requested stable alpha0 least-squares with rank reporting and a fixed pooled-MAE selector; both were incorporated before commit/run. No extra candidates or knots were added. Full300cross-fit maps+20selected refits are saved; original P8a files and answered experiment histories remain immutable.
