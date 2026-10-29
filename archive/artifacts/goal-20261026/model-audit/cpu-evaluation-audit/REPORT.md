# Completed official-only ADMET feature evaluation

The first complete official-input comparison supports ADMETlab features as a complementary expert, but does not establish a uniform improvement. The predeclared selection procedure reduced raw ST-RAE on both frozen diagnostic cohorts. On own750, its other four metrics worsened and the paired ST-RAE interval includes zero. On reconstructed briford529, all five point estimates improved and the ST-RAE interval excludes zero. These observations do not select a final submission model; final selection must repeat the same training-OOF procedure on the full official training set.

Run `d8ab78b2-2ca8-482f-8706-6d48b128a33a`, experiment `ea7f1cb9-544a-41ec-b0a8-0c7aa7630d86`, source `437cf5e8c403a7fd87ba8b211ee1c4c24d847c07`; fixed `bash run.sh`, local CPU, about5m20s wall time. No paid GPU, final refit or submission. The answered experiment is frozen.

## Inputs and validation

The hash-pinned18460-outcome snapshot contained all4905 official training molecules and750 official blind query molecules, with120 reviewed finite features each and zero official exceptions. Only official experimental targets were used for new supervised fits. External acquisition remained incomplete in this snapshot (13961 pending of32421); no partial-scope completion claim is made. The fixed corrected native expert is reused under the explicit conditional legacy-source policy, not represented as a newly curated full-pool model.

Eight predeclared model/feature variants each had two inner settings, five fixed inner folds, four CYP targets and two separate outer-training pools:640 inner and64 outer scalar-target fits. CheMeleon was used as a frozen encoder, not fine-tuned. Target transforms and preprocessing were fit on training rows only. Native and candidate OOF vectors were aligned by moleculeID; native component fold numbers are not claimed to be a common split.

Independent no-fit verification in [verify_cpu_portfolio.py](../verify_cpu_portfolio.py) checked37 pinned input files,100 prediction files, all2500 reported outer metric cells,32 inner-OOF variants, hyperparameter selection, and both selected-procedure scaffold bootstraps. Macro rescore discrepancy was exactly0; per-target discrepancies were below1e-12. All1000 bootstrap samples per comparison were valid. Details and prediction hashes are in [verification.json](verification.json).

## Procedure selected within each training pool

|Cohort / model|ST-RAE↓|MAE↓|R²↑|Spearman↑|Kendall↑|
|---|---:|---:|---:|---:|---:|
|own750 fixed native|0.620777|0.523427|0.470486|0.673245|0.495502|
|own750 selected procedure|0.617396|0.532639|0.456588|0.669965|0.491058|
|briford529 fixed native|0.642309|0.475777|0.384635|0.653092|0.477189|
|briford529 selected procedure|0.599983|0.466403|0.406892|0.657540|0.479999|

Own750 selects structure+ADMET LightGBM,15leaves/depth4, with four static native-blend weights for the candidate:0.5283/0.2809/0.1467/0.2441 (CYP1A2/2C9/2D6/3A4). Briford529 selects ADMET-only LightGBM with the same tree setting and weights0.4231/0.3043/0.1741/0.2969. Selection and weights use each outer-training pool's own OOF predictions. No cross-cohort aggregation of OOF scores was used.

Paired scaffold95% intervals for candidate-minus-native ST-RAE:

- own750:−0.003381 [−0.020724,+0.011998].
- briford529:−0.042326 [−0.069672,−0.020305].

All five selected-procedure intervals are in [selected-procedure-bootstrap.csv](selected-procedure-bootstrap.csv). They are conditional on fitted predictions, exploratory, and uncorrected for model selection or multiple comparisons; these intervals are not newly independent confirmation after repeated cohort reuse.

## Same predeclared arm across both cohorts

The primary simple all120 LightGBM plus one global native-blend scalar achieved raw ST-RAE0.613328 on own750 and0.598232 on briford529. It existed before evaluation, so reporting it does not require inventing a post-hoc variant. Its hyperparameters and scalar were still learned separately within each cohort's own training pool; this is a common procedure, not one universal coefficient vector. It is not relabeled the winning final recipe because of outer results.

Its ST-RAE deltas and scaffold95% intervals were−0.007449 [−0.024230,+0.006771] and−0.044077 [−0.071008,−0.021146]. Own750 MAE and R² still worsened slightly, while rank correlations improved. This arm therefore also fails to demonstrate a uniform gain across all metrics on own750.

## Representation and endpoint findings

|Standalone variant|own750 rawST|briford529 rawST|
|---|---:|---:|
|Structure LightGBM|0.745674|0.722026|
|ADMET120 LightGBM|0.695940|0.716642|
|Structure+ADMET120 LightGBM|0.695639|0.692248|
|CYP13 LightGBM|0.805074|0.871211|
|Non-CYP107 LightGBM|0.747974|0.778189|
|ADMET120 kernel|0.758969|0.747309|
|FrozenCheM Ridge|0.787701|0.767966|
|FrozenCheM+ADMET120 Ridge|0.752799|0.718004|

Adding ADMET improves the standalone structure and frozenCheM controls on both cohorts. All standalone candidates remain worse than the fixed native expert. Their useful signal is complementary: several blends improve ST-RAE. CYP-only features do not explain the full effect; the107 non-CYP features also contribute complementary signal, especially on briford529. These bounded comparisons support testing feature fusion if warranted by the broader experiment budget, but do not establish that a fresh jointGNN would improve. FrozenCheM+ADMET blends did not improve own750 and are not a confirmed next champion.

## Raw and published-placement lanes

The source's published native placement is a separate diagnostic, not independent calibration evidence. Placed nativeST was1.058445/1.087466; the selected procedures gave1.093546/1.099036. Thus the selected raw improvement does **not** survive that placement procedure. Raw-vs-placed provenance must remain explicit in any final model/submission discussion. The full100-row [independent metric table](independently-rescored-metrics.csv) retains all adverse cases.

## Limits and next handoff

Both frozen cohorts are reused development diagnostics and share143 molecules. Briford529 reconstructs the public recipe; it is not certified as the author's original exact holdout. The retained fixed native expert carries disclosed public-source parent/assay representation limitations. The teacher's original training membership is not established by these feature tests.

Collection of all32421 outcomes, full versioned chemistry/output audit, and final fit remain separate outstanding work. The provisional final executor must retain the full-scope gate and independently repeat inner-only selection on all4905 official training rows using its own frozen folds. No extra fitting or compute was launched after this run.
