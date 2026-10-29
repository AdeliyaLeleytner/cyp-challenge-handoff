# P3 matched loss-by-weighting factorial: private result

Plain MAE with uniform weights has the best pooled point estimate for every official macro metric in this bounded experiment. The interval objective does not improve the observed ST-RAE; its small difference from MAE is uncertain. The tested CI-derived row-weight proxy is substantially worse in both loss settings.

| Training cell | ST-RAE ↓ | MAE ↓ | R² ↑ | Spearman ↑ | Kendall ↑ |
|---|---:|---:|---:|---:|---:|
| MAE + uniform | 0.656206 | 0.529876 | 0.397040 | 0.620209 | 0.450378 |
| Interval L1 + uniform | 0.661896 | 0.547327 | 0.373964 | 0.610350 | 0.440853 |
| MAE + CI-weight proxy | 0.700939 | 0.582588 | 0.297749 | 0.604256 | 0.434427 |
| Interval L1 + CI-weight proxy | 0.701533 | 0.588248 | 0.287883 | 0.601004 | 0.432858 |

The pooled scores were calculated after joining every official molecule to its out-of-fold prediction, not by averaging fold scores. All 4,905 official IDs and original target values match the pinned input; all 20 prediction tables match the exact fold ID order. A separate agent independently reproduced every per-CYP metric to less than 1e-12. Pearson is retained only as an additional diagnostic.

For ST-RAE, interval minus MAE under uniform weights is +0.005690, with a descriptive paired 95% interval of [−0.007038,+0.018474]. This does not establish equivalence or a definitive worsening, and it provides no observed improvement to promote. The interval cell also worsens MAE by 0.017450 and R² by 0.023076 in the point estimates. All detailed metrics and intervals are retained.

The CI-weight proxy increases ST-RAE by 0.044733 for MAE (95% interval [+0.028988,+0.060405]) and by 0.039637 for interval L1 ([+0.024685,+0.054293]). Under uniform weights, the interval effect is adverse in each CYP point estimate. A contrary case appears within the weighted arms: interval L1 improves CYP2C9 ST-RAE by 0.016770 relative to weighted MAE, but its interval [−0.042360,+0.011427] is wide. The strongest weighting degradation is CYP3A4. These cases remain visible in the per-CYP CSV.

The ST-RAE difference-in-differences is −0.005096, interval [−0.023233,+0.012662]. Therefore the strong objective-by-weighting interaction reported by the motivating public recipe is not demonstrated in our data/protocol. This is not a refutation of that author’s experiment: we use the audited common 18-head table, training-only weight preprocessing, a common checkpoint metric and frozen fold IDs, rather than claiming exact reproduction of its 22-head score.

All four cells share 31,641 curated rows, 18 real targets, eight identical masked bound-carrier outputs, width 2,048/depth 4 scratch message passing, a 1,024×2 FFN, dropout 0.2, batch 128, float32 precision, seed 42+fold, optimizer schedule and stopping rule. Initial parameter hashes and batch-normalization buffers match within each fold. Four stopping rows equivalent to test molecules were removed under the already approved structural policy; training and test indices were unchanged. Bound carriers have zero gradient and are excluded from the loss denominator. All primary and auxiliary labels remain separate tasks.

The interval objective is the exact raw-unit L1 distance to the experimental confidence interval divided by the training target SD, with per-target MAE fallback when bounds are absent. It is not the full macro ST-RAE training objective: task weights remain 1 for all 18 real heads, observed-label counts determine the loss denominator, and per-CYP raw-unit coefficients include 1/trainingSD. The weighted arms additionally multiply each molecule by the CI-derived row-weight proxy. Median imputation, normalization and 99th-percentile cap are fitted only on training rows. The width/3.92 construction with sigma floor 0.02 is a proxy, not an independently measured experimental variance. All coefficients and fitted statistics are saved in initial.json.

The common stopping criterion is unweighted raw primary macro ST-RAE on a separate stopping cohort. Maximum training length is 200 epochs with patience 30. One interval/CI run (fold 3) reached the 200-epoch cap, with best checkpoint at epoch 179; it must not be described as having fully satisfied the patience rule. The other 19 runs stopped by the prescribed rule. The confidence-weighted cells generally required more epochs. No setting or epoch budget was changed after inspecting outcomes.

Uncertainty uses 1,000 paired Bemis–Murcko scaffold-group resamples within frozen folds, seed 20261026, identical draws across all cells and endpoints, with percentile 95% bounds. It is descriptive conditional-OOF uncertainty. The experiment uses one seed per fold and reused development data; the intervals do not capture all training-seed variability or certify performance on the blind challenge set. No blind-population placement, new stacking weights or leaderboard feedback was fitted.

Execution: node ca918225-680e-4ede-9961-aa11f6507a0c, run 5e13d499-82c9-4445-86ad-6814b90bf5ce, source 562d9b6, fixed command `bash run.sh`. Runtime: Torch 2.6.0+cu124, Chemprop 2.2.1, Lightning 2.5.5; the full package freeze and image digest are retained. The 20 full checkpoints and 102 result files are locally hash-verified against the remote manifest: 2,902,493,397 bytes, zero mismatches. Both task-owned GPU instances are now confirmed absent; unrelated instances were unchanged.

Evidence: `readout/READOUT.json`, `readout/point-metrics.csv`, `readout/paired-deltas.csv`, `independent-model-agent-pooled-check.json`, `RECOVERY_CERTIFICATE.json`, `remote-file-manifest.json` and the original stage/source manifests. Every model and adverse case is retained privately.

Decision for this experiment: retain MAE/uniform as the reference; do not promote the tested interval or CI-weight variants. P7 likewise did not improve its matched control. These are bounded negative results, not proof that all metric-aware losses or direct descriptor integration must fail. Further experiments require root’s adjudication within the remaining campaign scope; no publication or submission has occurred.

Resource incident: final reported charges are approximately $4.03, including $2.181 on the first failed host that I did not successfully cancel promptly. Both leases are now independently confirmed destroyed. See `compute/TEARDOWN_INCIDENT.md` and `compute/BUDGET_FINAL.json`; the earlier first-host cost estimate was corrected.
