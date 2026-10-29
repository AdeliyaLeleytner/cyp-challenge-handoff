# P7R: matched Vol/Dense repair result

The deterministic unit repair gives a small improvement over the original fusion model in all five macro point estimates, but it does not close the gap to the fresh zero-feature control. The primary ST-RAE improvement is uncertain. This is not a new leaderboard result or a demonstrated route to top10.

| Arm | ST-RAE ↓ | MAE ↓ | R² ↑ | Spearman ↑ | Kendall ↑ |
|---|---:|---:|---:|---:|---:|
| Zero-feature control | 0.672018 | 0.535662 | 0.390662 | 0.612207 | 0.443153 |
| Original 120 fusion | 0.715618 | 0.561973 | 0.346646 | 0.578416 | 0.414355 |
| Vol/Dense masked | 0.712342 | 0.557689 | 0.349659 | 0.575823 | 0.412582 |
| Vol/Dense unit repaired | 0.707574 | 0.555577 | 0.357547 | 0.584240 | 0.418962 |

Repair minus original fusion: ST-RAE −0.008044, paired descriptive 95% interval [−0.020360,+0.004830]. Masking alone gives −0.003276 [−0.015049,+0.008438]. Repair minus masking gives −0.004768 [−0.016617,+0.007670]. These intervals do not support calling the small ST-RAE improvement definitive or equivalent to zero effect. The original fusion remains worse than the zero control by 0.043600 [0.027260,0.059544].

Repair is heterogeneous across CYPs: ST-RAE changes are−0.010002 for 1A2,−0.034318 for 2C9,+0.003206 for 2D6 and+0.008937 for 3A4. The 2C9 interval is[−0.063445,−0.005047]; other individual intervals span zero. The adverse 2D6/3A4 point estimates are retained. All metric/endpoint contrasts are in `readout/paired-deltas.csv`; no outcomes were hidden or used to alter the study.

Extended macro diagnostics:

| Arm | RMSE | Signed bias | Prediction SD | Target SD |
|---|---:|---:|---:|---:|
| Zero-feature control | 0.733843 | 0.073459 | 0.606993 | 0.955219 |
| Original 120 fusion | 0.762044 | 0.072436 | 0.581020 | 0.955219 |
| Vol/Dense masked | 0.759781 | 0.051149 | 0.575099 | 0.955219 |
| Vol/Dense unit repaired | 0.755371 | 0.036750 | 0.570174 | 0.955219 |

Repair reduces the signed mean bias relative to original fusion, while prediction spread becomes slightly more compressed. Bias and SD are descriptive diagnostics, not additional optimized objectives. Masking slightly improves error metrics but worsens the rank-metric point estimates; repair improves the rank points relative to both fusion controls. Pearson is retained as an extra diagnostic, not a replacement for official Kendall.

## What was held fixed

This is a fresh four-arm, five-fold comparison using 31,641 molecules, the same 18 experimental/auxiliary heads, eight identical masked bound carriers, the repaired train/stopping/test partitions, and the same initial parameter and batch-normalization states within each fold. It uses the P7 scratch 2048/depth 4 encoder, 2168-input 1024×2FFN, dropout 0.2, batch 128, standardized observed-label MAE, uniform row weights and the same raw primary ST-RAE stopping callable. Maximum 200 epochs/patience 30 was not shortened to fit the budget. All labels, IDs, SMILES and folds remained unchanged.

The original and repaired arrays differ in exactly 85 rows/170 raw numeric cells, only Vol and Dense. The remaining 118 raw columns and their training-transformed vectors are byte-identical. The repaired values reproduce the same empirical atom-additive formula with consistent units; they are not new measured or conformer-derived volumes. The raw service cache remains untouched. The masked arm is retrained with only those two standardized coordinates fixed to zero, unlike the prior frozen-head dependence ablation. Each arm fits medians/scales only on its training rows.

The unit error is real, but this trial does not establish that it explains the whole P7 deterioration. P7D showed poorer primary training fit, strong descriptor dependence and selective gains on PubChem response tasks; these optimization/task-allocation explanations remain unresolved. The existing loss/data regime was deliberately not changed here. No broadCDF transformation, extra targets, new features, seeds or hidden hyperparameter sweep was added.

## Validation and limits

The readout pools exact official out-of-fold predictions before scoring all 4,905 official IDs. Every per-fold ID/order/hash, original target value, observed confidence bound, initial parameter hash and BN state was checked. A separate agent independently reproduced all official and extended metrics: pooled maximum discrepancy 1.11e−16. The largest worker-versus-CSV difference 5.78e−8 was the declared float32-versus-float64 SD accumulation difference; official metric checks remained strict.

Intervals use the fixed 1,000 paired scaffold-group resamples within frozen folds, seed 20261026. They describe conditionalOOF uncertainty; they do not include all training-seed/hardware variability. There is one seed per fold, overlapping training sets and reused development data. Historical P7 scores were not substituted for these fresh matched controls or pooled with them. No claim is made about new independent dense-series or blind leaderboard performance. No serving placement, ensemble coefficient or submission was fitted or dispatched.

## Execution, preservation and cost

Full node `5b7e1c8f-ee3d-4eea-a971-2fb6adc561bd`; run `c95e19e7-e392-4a10-84c5-75d5af23f628`; source `8fad9cdf0aba0e1974eba3e7a8e11c6b3b42ce41`. All 20 models completed in 34–56 epochs; none hit 200. The sum of recorded worker wall times was 4.765 hours; this is not a GPU-utilization measurement. The four3epoch smoke models were used only to validate implementation/runtime. Torch 2.6.0+cu124/Chemprop 2.2.1/Lightning 2.5.5 were pinned.

All 20 full checkpoints and 142 output files (2,933,664,231bytes) were locally hash-verified, along with the four smoke checkpoints. The task-owned lease 57857438 was destroyed with explicit `--yes` and independently verified absent at 22:04:44UTC on 26 October; unrelated resources were unchanged. All owned guard/recovery/monitor/keepawake processes exited. No idle paid resource remains.

Vast currently reports $0.640 for this successful profile/full-comparison lease. Including prior P7R boot/transport diagnostics, the phase total is $0.713 against $3.20. The private campaign total is $4.741 against $10, leaving $5.259. These are rounded provider charges with a minor final-settlement caveat. Previous cancellation mistakes remain separately documented; this teardown was verified.

Evidence: `readout/READOUT.json`, `point-metrics.csv`, `paired-deltas.csv`, `INDEPENDENT_MODEL_AGENT_CHECK.json`, `RECOVERY_CERTIFICATE.json`, `PROFILE_RECOVERY_CERTIFICATE.json`, `compute/FINAL_TEARDOWN.json`, `compute/BUDGET_FINAL.json`, and the fixed input/repair manifests. All models and adverse results remain private.

Decision: do not promote this direct-fusion family over its zero-feature control from this evidence. The corrected descriptor version is scientifically preferable to the known unit defect when those descriptors are used, but its small observed gain is not evidence of a large performance breakthrough. Broader task-weighting/representation questions require a separately chosen experiment, not further unplanned repair sweeps.
