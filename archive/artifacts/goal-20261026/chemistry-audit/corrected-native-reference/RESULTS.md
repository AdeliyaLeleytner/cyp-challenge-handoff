# Corrected native reference: completed and recovered

The strict-tautomer corrected reference is now fitted and available for fair comparisons with ADMETlab-feature candidates. It is not itself a feature-augmented model or a new leaderboard submission.

ORX experiment `31f8a64a-174d-4f92-95e8-2ada73c2176d`, run `ea091487-5145-4ddf-9a54-9d2240281aa6`, commit `c7d9be7a5afa2162be9b97b56cdd64b5929af2d7`; fixed command `bash run.sh`. ORX reports done in47m20s. The source branch is now frozen.

Exactly12approved outer-training component rows and62inner train-side equivalents were excluded. All outer query/truth IDs and surviving validation-fold assignments were preserved. Native model hyperparameters, task weights, training/assembly source and source data values stayed unchanged.20affected folds were retrained;20unaffected folds were reused after data/spec/fold/checkpoint/prediction verification. The broader4stereo-related analog rows were retained.

## Verified macro metrics

| Cohort | Output | ST-RAE↓ | MAE↓ | R²↑ | Spearman↑ | Kendall↑ |
|---|---|---:|---:|---:|---:|---:|
| own750 | raw | 0.620777 | 0.523427 | 0.470486 | 0.673245 | 0.495502 |
| own750 | native_published_placement | 1.058445 | 0.734638 | 0.127505 | 0.673245 | 0.495502 |
| briford529 | raw | 0.642309 | 0.475777 | 0.384635 | 0.653092 | 0.477189 |
| briford529 | native_published_placement | 1.087466 | 0.636389 | 0.057263 | 0.653093 | 0.477213 |

Raw ST-RAE changed from0.626205→0.620777 on own750 and from0.622655→0.642309 on briford529. Thus the point estimate improves slightly on own750 and worsens on briford529. The correction is required for the comparison protocol; it was not selected to improve scores. It also changes training batches/optimization trajectories, so the score difference is not an isolated causal measurement of leakage benefit.

Paired scaffold-bootstrap95% intervals for corrected-minus-historical raw ST-RAE are:
- own750: delta-0.005428, interval[-0.016807, +0.006848], 665scaffold groups, 1000valid replicates.
- briford529: delta+0.019654, interval[+0.005306, +0.035572], 474scaffold groups, 1000valid replicates.

These intervals condition on the fitted single-seed models and do not measure training-seed uncertainty. The two frozen outer cohorts overlap and are not independent replications. All per-CYP metrics, historical comparisons and uncertainty details are in [verified-scoring.json](verified-scoring.json). Local rescoring matches the remote metrics to1e-12.

## Runtime, recovery and teardown

Recorded fit time for the20newfolds sums to **4.8615GPU-hours**. No training-log traceback, runtime-error, NaN or OOM markers were found. Every model's hyperparameters, fold row counts, source hashes and recorded primary package versions match the prepared protocol. The full environment comparison found one incidental HTTP-library difference: multidict7.2.0historically versus7.2.1now; it is recorded rather than hidden.

Recovered **291files / 745,693,142bytes**, including40checkpoint archives,40fold-completion records and100readable CSVs. All remote hashes match; the remote tree was stable across final recovery; the ORX main log hash also matches. A gateway SSH transfer failed, so final recovery used the same verified instance's direct SSH endpoint through Wi-Fi. No scientific work was rerun.

Instance **57740054 was destroyed and verified absent at 2026-10-26T01:28:09.187314+00:00**. No other instance was modified. The quote-based lifetime estimate is **$1.8201**, below the$2.50phase cap; this is not an itemized invoice or a balance-delta attribution. The parent budget guard's lease record is marked destroyed.

## Artifacts for the next model comparison

- [REFERENCE_CERTIFICATE.json](REFERENCE_CERTIFICATE.json): exact corrected prediction/OOF hashes and protocol scope
- [verified-scoring.json](verified-scoring.json): independently recomputed metrics and paired uncertainty
- [postrun-model-audit.json](postrun-model-audit.json), [fold-results.csv](fold-results.csv)
- [recovery-certificate.json](recovery-certificate.json), [resource-cleanup.json](resource-cleanup.json)
- [runtime-package-comparison.json](runtime-package-comparison.json), [reuse-peer-review.json](reuse-peer-review.json)
- [orx-run.log](orx-run.log)
- [recovered-output/own750/results/](recovered-output/own750/results/) and [recovered-output/briford529/results/](recovered-output/briford529/results/)

The prepared full-fit companion was not launched on this lease. No further experiments, GPUs, feature-model fits or challenge submissions were performed by this helper.
