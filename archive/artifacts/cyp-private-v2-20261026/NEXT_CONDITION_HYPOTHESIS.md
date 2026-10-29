# Next condition-aware auxiliary experiment — proposed, not launched

**Question.** Does routing the released +NADPH screen through a separately supervised active-preincubation potency improve prediction of −NADPH direct potency, beyond the information supplied by adding active-condition labels to ordinary free heads? The alternative is that a free multi-task model already handles the condition difference, or that assay efficacy/measurement variation makes a potency-only screen link too restrictive.

This is an empirical condition-routing test. It cannot identify metabolic turnover, irreversible inhibition, Ki, efficacy, or a kinetic rate from the released summaries. No acquisition, fitting, paid resources or public writes are authorized by this proposal.

## Fixed data and actual new supervision

Use the existing31,641-row P7 common table, its29 exclusions and repaired rotating folds (manifest SHA436ec6c3895a3e937ae9fa3debc464b75a9e8dbcf36a7f526da67b74fbad599c). Keep every existing18 target column unchanged. Add only the four `cyp{1a2,2c9,2d6,3a4}_pic50_tdi_condition` columns from saved `original_full/raw/tdi.csv`, joining by exact molecule_name. Admit only IDs already in the common table and verify canonical isomeric source/model graph equality; the preparatory inventory found zero graph mismatches. Do not expand the cohort or bring in newly retrieved P4 records. The active table intersects4938 common IDs;4937 have at least one finite active target. Membership and hashes are saved in `biochem_sources/next-condition-active-membership.csv` and `next-condition-coverage.json`, with reproducible read-only script `next_condition_inventory.py`.

| CYP | Direct points | Active points admitted | Active point without same-CYP direct | Screen values | Active+screen pairs | Direct+active+screen |
|---|---:|---:|---:|---:|---:|---:|
|1A2|1412|1413|1|4375|1413|1412|
|2C9|1285|1285|0|4375|1285|1285|
|2D6|1493|1495|2|4375|1495|1493|
|3A4|2335|2378|44|4375|1815|1804|

Thus the experiment adds6571 measured/fitted active-condition target cells on existing rows, including47 cells without same-CYP direct values. It adds **zero molecules** to training. It does not automatically use every6145 TDI-file row. Some extra active-supervised molecules were already in the common union for other tasks. The current screen values equal source `log2fc_estimate` exactly for all4375×4 cells. The single-only ID absent from the common table remains absent. The530 direct IDs without released single records remain, rather than being imputed as screen negatives.

The empirical calibrator has, per fold,750–787 paired train examples for2C9,834–863 for1A2,848–960 for2D6 and1076–1101 for3A4 before any additional calibration subfold split. Counts are explicit in the coverage JSON, not guessed from total table size.

Do not add Emax, TDI boolean calls, plate Cohen’s d, CI width or pseudo-kinetic labels in this first experiment. This keeps the factor interpretable. Active pIC50 is a Bayesian fitted point, not a directly counted molecule binding event. The other raw tables remain available for diagnosis only.

## Why a direct-plus-delta head is not by itself a new biological model

If direct `d=w_d h+b_d`, delta `q=w_q h+b_q`, and active `a=d+q`, then active is simply another affine head with `w_a=w_d+w_q`. Every pair of free direct/active affine heads has an equivalent direct/delta parameterization. Without an explicit constraint, a different gradient/regularization prior, or a distinct observation pathway, this is a coordinate change—not evidence of metabolic mechanism. Applying unequal weight decay to these coordinates changes the prior; any benefit must then be described as regularization. Direct and delta losses would also reuse the direct observation inside its own difference, with unknown joint covariance.

Therefore use **separate free direct and active outputs**, allow signed differences, and do not train an extra delta target. The scientific intervention is a non-linear, frozen empirical observation map from a specified condition’s predicted potency to the measured screen readout. It changes the information route rather than renaming a linear head.

## One experiment, four matched arms

All arms share the same graph encoder, prediction capacity, initialization of common parameters, seed42+fold,18 existing labels, four allocated active heads, folds, optimizer, precision, primary loss, row order, epoch ceiling and direct-only stopping criterion. Choose one fixed background before launch; do not mix P3 loss variants or change the ADMET feature toggle between these arms. The simplest background is MAE/uniform without ADMET descriptors, so a second teacher interaction is not introduced. If root instead fixes the P7 descriptor background, use it identically in every arm and state that conditional scope.

| Arm | Active supervision | Screen prediction used in the existing screen loss | Interpretable contrast |
|---|---|---|---|
|A: free screen, no active labels|Masked|Free screen head|Fresh coverage control|
|B: free screen + active labels|All admitted finite active cells|Free screen head|B−A measures additional active-condition supervision on the same molecules|
|C: active-route screen|Exactly the same labels/masks as B|Frozen empirical map `g_e(a_e)`|C−B tests the constrained observation route, with coverage held fixed|
|D: wrong-condition route|Exactly the same labels/masks as B/C|The **same** map `g_e(d_e)`|C−D distinguishes active versus direct routing under identical screen-map capacity|

Retain the allocated free-screen output parameters in C/D for initialization/parameter accounting but do not give them a screen bypass; otherwise an unrestricted residual could absorb the link and make the contrast uninformative. They are unused for the screen loss in C/D. Explicitly report that B has an unconstrained screen function whereas C/D constrain it: C−B alone mixes routing and observation-model regularization. **C−D is the capacity-matched condition specificity test.** Do not call all four effective function classes identical merely because allocated parameter counts match.

Keep each existing loss coefficient fixed; do not renormalize primary loss when A masks active labels. Use a common fixed22-task coefficient denominator (18 existing +4 active), with missing cells masked and no per-batch rescaling by the number of observed endpoints. The four screen terms are replaced, never duplicated, in C/D. Keep active coefficients identical in B/C/D and loss/scale conventions unchanged across arms. B−A isolates added active supervision but does not separate extra47-cell coverage from the other6524 paired active observations; that narrower question would require a separately justified coverage-mask factor, not an unsupported claim from this experiment.

## Empirical observation map: explicit, modest and fold-local

For each enzyme and training fold only, fit screen `log2fc_estimate` against measured active pIC50 on their paired training rows. A concrete low-capacity map is a piecewise-linear spline with hinges at the training active-potency25th/50th/75th percentiles: intercept +linear term +three ReLU hinge terms. Standardize input/output using those training pairs; ridge-penalize non-intercept coefficients with fixed alpha1 under mean squared error. The knots, coefficients, scales and training IDs are saved and frozen before neural training. Linear tails are explicit; report extrapolation outside the paired training range, rather than clipping predictions silently. Do not tune knots, penalty, monotonicity or a Hill exponent on stop/test outcomes.

This non-linear mapping is **not a dose-response law**. No inhibition sign, efficacy ceiling or monotonicity is imposed. The3A4/1A2/2C9 and2D6 observation readouts differ, so each enzyme gets its own map. D deliberately applies the active-calibrated map to predicted direct potency; refitting g on direct labels in D would change both calibration and route, obscuring the primary contrast.

Before any expensive neural fit, an authorized cheap training-only cross-fit should compare this calibrator’s held-out screen error with a training-mean screen predictor and an affine active-potency map. Use the five existing original-fold groups within the current training partition; no new scaffold shuffle or holdout peeking. Inspect its shape, residuals and out-of-range fraction. This checks whether there is an observable empirical relationship worth coupling; it does not prove usefulness for direct potency. If the active map is mostly flat, unstable, or systematically fails compared with these controls, report that evidence and reconsider the routing test rather than automatically spend on20 fits. No invented numeric success threshold is imposed.

The same frozen g and its calibration evidence are attached to B/C/D, but B does not consume it in the screen loss. Fit target scalers and any feature transforms on training rows only. No measured active or screen value is an input at validation/test time: predictions derive solely from molecular representation. Calibrators never see stopping/test auxiliary labels, and do not adapt on blind750 structures or predictions.

## Biological boundaries, missingness and purges

The official screen uses +NADPH preincubation; the requested direct target uses −NADPH preincubation. The released4.95049505e-05M is recorded assay metadata, not an established reaction-concentration/nominal100µM equivalence. The current log2FC normalization and negative Emax scale are not a verified remaining-activity fraction or0–1 efficacy. Therefore do not invert screen/Emax into IC50 or infer bounds from missingness. Emax can vary across compounds and the screen can have effects beyond potency; failure of C would refute this small observation model, not all possible condition-aware learning.

P6 observed signed shifts, with sizeable positive interval separation for3A4/2D6 and some negative cases. Marginal interval nonoverlap is not a joint difference interval. Direct is part of active−direct algebraically; shift/direct correlation is not causal. A signed unconstrained active/direct pair preserves these cases. Do not infer turnover or irreversible inactivation from an improved routing model.

All new active labels follow the same whole-row train exclusions against stop/test as every other task, including exact aliases and previously approved stereo-preserving equivalence groups. Use repaired P7 stopping sets so stop/test equivalence is absent. No duplicate direct columns from TDI are added as extra supervision. External aliases may not restore heldout labels. Missing active/screen values remain missing; no False-from-missing TDI calls, no pseudo-negatives, no new CI from cross-assay SD. One missing3A4 active value remains missing even though its direct value exists. Nuisance fitting must use the **post-purge training indices**, not all nominal training-fold molecules before exclusion.

## Readouts and competing predictions

Use identical direct test IDs/masks and allfive official metrics, macro and per enzyme, on the five rotating folds. Raw prediction effects are primary; any serving transform is a separate frozen diagnostic. Keep unchanged incumbent predictions as an external reference, not a matched control trained under these new conditions. Report active/screen losses as auxiliary diagnostics only; a better screen fit with worse direct potency does not justify promotion.

- B better than A, with C no better than B: the new active-condition labels help, but the free head is sufficient.
- C better than B **and** D on direct predictions, especially in enzymes with observed condition differences: evidence for this empirical condition route, not kinetic identification.
- C and D move similarly: generic regularization or shared-potency signal is more plausible than condition specificity.
- C harms direct accuracy despite improving screen fit: the imposed link likely transfers screen-specific/efficacy effects into the wrong quantity.
- Improvement confined to broad/weak curves or plate-associated slices: preserve that pattern; do not present it as proof of metabolic fate. Any outcome-defined slice is diagnostic, not a selection set.

## Minimal informative test and cost, without new authorization

A single fold/three-epoch run is an implementation smoke only: confirm missing-label masks, active-route vs direct-route gradients, no use of hidden labels, finite spline derivatives and parameter initialization. It is not a scientific comparison. The minimum comparison answering both coverage and routing here is **four arms×five folds=20 fits** with one seed and the existing stopping protocol, after the cheap fold-local calibration check. No extra seeds, feature branches or kinetic heads.

Current recovered P3 MAE/uniform jobs took418–732seconds/fold (42–62epochs), roughly10–12seconds/epoch on RTX3090. The four extra output heads/small spline should have little FLOP cost, but changed early stopping is unknown. Twenty jobs at the observed MAE/uniform durations are about2.8GPU-hours, approximately0.7hours on4GPUs; at the saved4×3090 quote$0.6943/hour, raw training is roughly$0.49, before setup, recovery and idle time. At the existing200-epoch ceiling and12seconds/epoch,20jobs are about13.3GPU-hours/3.33four-GPU-hours, roughly$2.31 before overhead. These are planning bounds from the actual P3 runtime, not a guaranteed price or fresh rental quote.

The20 tiny nuisance spline fits and bookkeeping should be minutes on local CPU; that estimate has not been benchmarked and no fit is run now. A CPU frozen-feature readout would be cheaper but answers a different model question and is not silently substituted for the shared graph contrast. Root must inspect current spend/remaining campaign balance and authorize any fit; the existing$10 total cap is unchanged. If the remaining cap cannot cover the conservative bound with recovery margin, defer this graph experiment or explicitly choose a narrower scientific question—do not launch an underpowered one-fold “result.”

## Evidence

Biological facts: saved official challenge announcement and BIOCHEM_DATA_AUDIT.md. Signed shifts: p6/RESULTS.md with receipt/script. Actual admitted cells: biochem_sources/next-condition-coverage.json and next-condition-active-membership.csv. Fixed common data/folds: P7 audited join and revised-fold certificates. Runtime estimates: p3/recovered/full-results/*/complete.json and the saved replacement lease quote; no additional provider query. This file is a proposal only, not an experiment manifest or spend authorization.
