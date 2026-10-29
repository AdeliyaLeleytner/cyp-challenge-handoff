# Corrected native full-fit companion completed

The full-data native companion is complete, recovered, and independently verified. It provides the native expert needed for later ADMET feature blending: out-of-fold predictions for all 4,905 official training molecules and raw plus published-placement predictions for all 750 blinded query molecules. No feature model was fitted and no submission was made in this phase.

- Experiment: `8421e31b-790d-4c13-9f29-d3b9bdc1ee59`.
- Successful run: `91132654-801e-4d65-af63-84e014955d15`.
- Frozen source: `ed1ab38328eb9d088d785f90d4f96b99d95712e3`.
- Fixed run command: `bash run.sh`, launched through ORX SSH.
- Run wall time: 23 minutes 28 seconds. The ten new fits used 2.461 aggregate GPU hours; the longest took 21.29 minutes.
- Provider instance `57760728` was destroyed and verified absent. The matched provider charges total **$0.881**, below both the original $1.10 allocation and the subsequently authorized $1.70 cap. The local lease guard and recovery monitor have exited.

## What was preserved and changed

The complete native pools remain unchanged: union18 has 31,670 rows, mtaux8 has 4,905, 2d6isoform6 has 23,264, and 2d6single has 1,493. There are no outer-holdout exclusions in this final fit. Within the original five folds, 32 training-row entries were removed solely because they were audited stereo-preserving tautomer counterparts of validation rows: 12 union18 and 20 isoform6 entries. Original validation assignments/order, model hyperparameters, task weights and the serving aggregation implementation were preserved.

Ten affected union18/isoform6 models were retrained. Ten unchanged mtaux8/single models were reused only after checking exact data, specifications, fold membership, source, runtime, checkpoints and prediction hashes. Their historical metadata and job files were retained.

This is a **qualified fixed legacy expert**, consistent with the corrected outer references. It deliberately retains the same legacy public-source parent/assay associations; it is not a newly curated full-pool feature model. The source-provenance quarantine of 28 records, plus the separate service-identity exclusion used for fresh feature-supervised models, was not silently applied here. The strict-equivalence policy covers the 13 audited groups, not an exhaustive claim about all possible tautomer or representation relationships. Legitimate public assay overlap with a blinded structure was retained; hidden challenge labels were not used.

## Runtime and operational repair

The image was pinned to `pytorch/pytorch@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`. Runtime checks confirmed Torch 2.6.0+cu124, Chemprop 2.2.1, Lightning 2.5.5, RDKit 2026.9.1, NumPy 2.2.6, pandas 2.3.3 and scikit-learn 1.7.2, matching the corrected native reference.

The first run, `e3272d02-19cd-4b6d-ac87-fdc822d8e3bb`, failed during dependency installation before any fits. The task container's DNS servers were unreachable; public PyPI subsequently timed out during TLS negotiation. Only that container's resolver was repaired, and the committed installer was changed to a reachable Tsinghua HTTPS package mirror. TLS verification and all pinned package versions were retained. The second ORX run succeeded. Neither Mac VPN/routes nor other instances were modified.

## Recovery and independent checks

The [recovery certificate](recovery-certificate.json) verifies 147 stable remote files totaling 374,952,675 bytes, including 20 complete checkpoint archives and 20 fold completion records. Every remote file hash matched its recovered local copy.

The [reference certificate](FULLFIT_REFERENCE_CERTIFICATE.json) binds the exact source, run, stage/purge manifests, runtime, component outputs and final predictions. Independent checks confirmed:

- Every fold's training and validation row counts, validation identities/order, hyperparameters, source and packages match the staged specification.
- Component OOF concatenation and the native float32 fold-mean reduction match recovered component outputs.
- Final raw native aggregation matches exactly: maximum absolute error **0**.
- The official training OOF aggregate matches within **1.78e−15**.
- OOF-derived Pearson factors and the published placement equations reproduce the placed output within **1e−12**.
- The 4,905 training and 750 query identities/SMILES align exactly, with all four prediction columns finite.

Native components have different fold assignments. The training OOF file is a valid rowwise aggregation of each component's own OOF prediction; it is not evidence of one shared fold map across components.

## Reusable artifacts

All prediction files are under [recovered-output/results](recovered-output/results):

| Artifact | SHA-256 |
|---|---|
| `native_official_training_OOF.csv` | `900bbcccd7fc79e87c28ed0a39f79925e72ca941c16a3d15d33a819eb44520e6` |
| `cyp-ensemble_activity_submission_native_raw.csv` | `a06808ca09635dcaeda471372c60da6f0db5821bff185fdde744ef873dddc199` |
| `cyp-ensemble_activity_submission_native_raw_native_strae.csv` | `95897f449e10899abc24c4c9c432a72b29e9a890b3208112e97cd9aa3006eaa8` |

The reference certificate also provides paths and hashes for all four component OOF and blinded-prediction tables. Its SHA-256 is `94ab14077f80747fbab9af41f4742612bd98219ef3436b8cd86f4ad3f2a3ef3f`.

The full official training OOF macro scores are ST-RAE 0.640804, MAE 0.510578, R² 0.436518, Spearman 0.648076 and Kendall 0.474205. These are training-selection diagnostics, not an independent holdout or leaderboard score; see [official-training-OOF-metrics.json](official-training-OOF-metrics.json).

Raw and placed predictions remain separate. The placement uses published leaderboard-derived constants and introduced two CYP1A2 floor ties; its existence does not establish better predictive performance. Final feature fitting and submission still require the complete 32,421-outcome acquisition and versioned chemical/output audit.

Billing evidence: [execution/BILLING_VERIFICATION.json](execution/BILLING_VERIFICATION.json). Exact successful run log: [orx-run.log](orx-run.log). Reproducible independent checker: [verify_recovered.py](verify_recovered.py).
