# Exact ST-RAE objective: native scratch and CheMeleon

This experiment tests the user's second direction on the same frozen 18/8/6/1 datasets and folds as the completed native control. Implementation does not run actual CYP benchmark training or submit predictions; only synthetic CPU functional training is used for verification. Default proposed config runs both initializations (80 models); `initializations` can explicitly select one 40-model arm. All outputs are separated under `scratch_exact_strae/` and `chemeleon_exact_strae/`.

## Objective

Let N be the number of fit rows, B the sampled minibatch size, J the number of primary heads, m the observed-label mask, and d(p,[l,u])=relu(l-p)+relu(p-u). Fit-only D_j=sum_i m_ij*d(mean_fit_y_j,[l_ij,u_ij]). The primary objective is mean_j(sum_i m_ij*d(p_ij,CI_ij)/D_j). With fit-center StandardScaler sigma_j and standardized network outputs, the exact uniform-row minibatch estimate is:

`L_primary_batch = N/(B*J) * sum_batch,primary m_ij * sigma_j/D_j * d(zpred_ij,[zlower_ij,zupper_ij])`.

No primary inverse-count factor is applied again. D, counts and scales are fixed from fit rows, never minibatches, validation, query labels or query predictions.

For auxiliary head a, `gamma_a = native_weight_a / sum(native_primary_weights)` and n_a is its observed fit count. The auxiliary loss is:

`L_aux_batch = N/B * sum_a gamma_a/n_a * sum_batch m_ia * abs(zpred_ia-ztrue_ia)`.

Total loss is their sum. Nominal auxiliary budgets are union18=1.05, mtaux8=0.30, 2d6isoform6=1.50, single=0. These preserve nominal author head ratios, not the previous realized label-frequency weighting. Thus this is an explicitly declared objective-and-checkpoint-selection change, not merely replacement of a scalar MAE formula.

Auxiliary-only minibatches are legal. Unknown entries contribute zero, including unknown interval coordinates. Unit per-row weights and uniform row sampling are required. Observed primary labels require finite ordered bounds. A missing primary target or nonpositive official denominator is an explicit preparation error; no epsilon substitution or nanmean target dropping occurs.

## Trainer/inference contract

- Vendor files remain byte-identical. Native model construction preserves architecture, FFN, normalization, optimizer/LR schedule, batch size, model precision and patience.
- Target StandardScaler is fitted to central fit labels only, as in native code. Lower and upper bounds use exactly that scaler; no three-independent-scalers mistake.
- `criterion_mode=exact_strae_v1` dispatches the explicit adapter from native worker. `native_mae` remains supported.
- RegressionFFN's raw FFN output is used directly for the loss, independent of output-transform train/eval mode. Forward stays16-mixed on GPU; interval arithmetic and reductions are FP32. Full validation ST-RAE is calculated with float64 scalar arithmetic from saved raw validation labels/bounds and accumulated physical-unit predictions.
- Checkpoint and early stopping monitor `val_primary_strae` over all inner-validation rows and all scored heads in the member, with validation's own official denominators. The auxiliary loss does not select checkpoints. Incomplete Lightning sanity-check prefixes do not produce a reported full-validation metric.
- The loss adapter adds no persistent state-dict keys and does not change native forward/inference; saved native model weights can still be loaded into the same native model architecture for inference. Normalization and validation details are saved in loss_metadata.json, histories in loss_history.json.
- Completed and incomplete fold attempts are bound to data/spec/query/vendor/experiment-module SHA256 identity. Prepared data/specs cannot be overwritten with different content. Same-identity incomplete attempts restart from initialization; they do not silently resume optimizer state. Fixed checkpoint names overwrite only the same-identity failed attempt.
- The assembly and published placement are unchanged. Both raw and placed outer scores are reported. Native published calibration is TEST-specific and need not transfer to these local holdouts.

## Four focused CPU tests

Command: `/Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python -m unittest night.test_strae_objective -v`.

1. Interval geometry, gradients, zero-width MAE equivalence.
2. Official-score parity, physical/scaled-unit invariance, center-only bound transform, all four nominal auxiliary budgets.
3. Full-batch versus partitioned objective and gradients, including auxiliary-only and short batches; FP32 reduction; unknown-coordinate masking; rejection of nonunit row weights.
4. Frozen fit statistics, zero-D/missing/reversed-CI guards, native forward/backward/state compatibility, and full-validation metric hook parity without Trainer.fit.

All four pass. Additional CPU preflight checked all80 proposed fit/validation fold configurations: every official primary denominator is finite positive. Both actual native700/norm and CheMeleon2048/mean18-head models passed unchanged-forward/state-layout and finite-gradient checks on three synthetic molecules, without optimizer steps.

CPU numerical environment: torch2.8.0, chemprop2.2.1, lightning2.5.5, pandas3.1.0, numpy2.5.4, sklearn1.9.1. Intended remote setup remains native pinned torch2.6.0/CUDA12.4, chemprop2.2.1/lightning2.5.5/pandas2.3.3/numpy2.2.6/sklearn1.7.2. No GPU run or measured scientific improvement is claimed by these CPU checks. A real authorized GPU training run remains necessary to establish scientific scores and exercise CUDA mixed precision. The complete Lightning lifecycle has now been tested on synthetic CPU data as described below.

## Provenance

Experiment child of completed native outer-holdout node1346e303-7733-44ce-b2d8-ffe26eab8a61. Local foundation/identity adapters imported from parent work-in-progress commitda6ed10; frozen vendor functions are unchanged. Prepared assets use the same manifest as that CheMeleon branch.

## Full synthetic CPU lifecycle test

One additional integration test, `night.test_strae_lifecycle`, exercises both the actual native700/depth5 encoder and pretrained CheMeleon2048/depth6 encoder with native FFN300x2. It uses 12 synthetic training molecules, eight synthetic validation molecules, and four synthetic query molecules; three epochs, warmup1 and batch4. CPU/32-true overrides are confined to the test fixture. No actual CYP benchmark labels are used.

Both cases passed real Lightning Trainer.fit, inherited on_validation_model_eval (four calls each, including sanity check; output_transform.training=True inside the inherited validation hook), val_primary_strae logging, best-checkpoint selection, checkpoint reload and independent ordinary-native-MPNN strict state reload. All physical-unit query predictions are finite and agree with explicit single unscaling. The CheMeleon fixture selected epoch0 despite completing three epochs, so this also exercises restoration of an earlier best checkpoint.

Command used: `CYP_TEST_FOUNDATION_CHECKPOINT=/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/stage/weights/chemeleon_mp.pt /Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python -m unittest night.test_strae_lifecycle -v`. Without that optional checkpoint-path variable, the mandatory scratch700 case still runs. One test, both encoders, passed in1.831s. Results: loss_lifecycle_test_results.json.

The proposed scientific config now targets GPU indices0–7 for the future80-model queue. No GPU run was launched by the helper.

Execution partition: this node runs40scratchmodels first; CheMeleonST will usea separatechild/outputafterthe precisiondiagnostic. Sharedhostfilelocks allowdiagnosticGPU0/1reservations and automaticuseofall8slotswhenreleased. No change to mathematicalobjective.
