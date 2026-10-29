# Cross-review of the initial feature-model portfolio

Reviewed: root `PLAN.md`, `model-audit/READOUT.md`, `model-audit/experiment-matrix.csv`, and the conditional-blend proposal in `FEATURE_HYPOTHESIS.md`. No fits, submissions, or spending.

The plan is directionally sound: reuse the native predictions, start with CPU models, retain all five metrics, and treat the reconstructed holdout and historical placement honestly. The main risks are an underspecified model-selection procedure and spending the GPU tranche before reserving the cost of the final fit.

## 1. Freeze the selection procedure before reading the new outer scores

The plan correctly says inner selection/outer diagnostics, but “choose the best supported recipe” and “favor fusion if it improves both holdouts” leave room for picking the winner from the outer table.

**Action:** predeclare one bounded candidate-selection procedure, apply it independently within each outer-training partition, evaluate its selected candidate once on that partition's outer cohort, and finally apply the same procedure to all official training molecules. Record if the two outer fits select different families; that evaluates a selection procedure, not one identical architecture winning twice. Per-candidate outer scores may still be reported diagnostically, but must not drive another hyperparameter/weight search.

Do not pool inner-OOF evidence from the two outer fits to select a global winner and then describe both outer cohorts as unseen. Each outer-training partition contains many molecules belonging to the other outer holdout. If a single globally frozen recipe is essential, a selector restricted to data excluding the union of the two holdouts is an alternative, but its base predictions must also be trained without that union; existing cohort-specific native OOF matrices do not automatically satisfy that stronger exclusion.

The earlier requirement to improve both holdouts can be a disclosed final qualification/veto, not a license to optimize repeatedly against them. In either case, these already-used cohorts remain development diagnostics.

## 2. Keep a small CPU portfolio; make the gate's decisive static control mandatory

I recommend the initial six fitted configurations already mostly present in the matrix:

- A1 ADMET-only LightGBM;
- A2 ADMET-only kernel ridge;
- A3 frozen CheMeleon Ridge with/without ADMET;
- A4 structure-based LightGBM with/without ADMET.

Keep C0 as the saved native reference. Do not add A5/ExtraTrees in this first portfolio unless the inner-OOF errors establish useful complementary signal. Avoid a broad new hyperparameter sweep.

For the inner-selected ADMET expert, evaluate B1 global static mixing, B2 per-CYP static mixing, and the conditional convex gate using the **same frozen expert predictions**. B2 should cease to be optional if the gate is tested: otherwise endpoint-specific calibration can masquerade as molecule-specific reliability. The shuffled-covariate gate is a small mechanism control, not another large base-model run. Fit all gate scalers, dimensionality reduction and weights within the permitted training data. Keep the pilot's negative unrestricted-residual result visible.

This is a genuine competing combination hypothesis: the gate changes which expert is trusted for each molecule while remaining inside their prediction interval. It is not another learner-depth or learning-rate variation.

## 3. Choose the calibration policy separately and prospectively

The raw/placed separation in READOUT is essential. Preserve it in executable manifests, not only prose. Compare feature models using the same raw evaluation lane and the same inner-only fitting budget for any learned calibration. Do not use the historical TEST-population placement on local holdouts as the selection criterion, and do not pick a placement policy after inspecting a new leaderboard response.

The final blind-set calibration policy should be written before submission generation. A static blend that changes prediction location/spread may interact with the native placement; that interaction must not be mislabeled as an architecture gain.

## 4. Budget the final fit, not only the GPU comparison

The optional GPU ceiling is **$5**, not the full account credit. G2's 40 outer fits are not its complete cost: a selected four-component, five-fold final ensemble requires another 20 fits, plus setup/inference/artifact recovery. Any representative runtime measurement belongs inside the same cap. A full G2 launch is defensible only if a fresh quote covers both evaluation and the final model, with teardown/recovery included.

Do not launch G1, G2 and G3 as one initial GPU portfolio. Choose at most one GPU route after the CPU comparison reveals a concrete remaining issue and the full cost fits. If G2 does not fit the budget, a targeted member-level G1 can answer a narrower question, but must not be reported as the full four-member feature-augmented reconstruction. G3 remains a later mechanism study; it is not required before a useful, validated submission.

## 5. Resolve one execution-dependency ambiguity

READOUT describes official5655 as an early modeling tranche, then says every new fit waits for the complete agreed scope. The user selected all32,421, so the final acquisition goal must remain full coverage. Root should state whether a chemically audited, immutable official tranche may support the CPU comparison while external labeling continues. That would not justify launching G2, filling missing external features with zeros, or declaring the acquisition goal complete early.

## Provenance language to retain

Use **“reconstructed-briford529”**, not “briford's exact holdout.” Retain the 143-molecule overlap and prior reuse of both outer cohorts. Keep briford/SuperCowPowers, stir_bar/lachrymator, and Jeremy distinct. The frozen historical native recipe is the control; current briford code and his latest live score are different artifacts. Nothing in this review supplies a new significance or effect-size cutoff, or treats unknown ADMETlab teacher training membership as resolved.
