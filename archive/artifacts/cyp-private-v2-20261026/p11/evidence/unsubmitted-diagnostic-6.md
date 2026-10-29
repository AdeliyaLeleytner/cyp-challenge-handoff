# Source-feature/PCA128 bundle: fidelity correction did not rescue Atom-JEPA

The completed source-feature/preprocessing comparison still favors the frozen ADME600 encoder over Atom-JEPA on all five macro metrics in OOF and both development holdouts. Atom-JEPA improves on the two outer cohorts compared with our earlier post-normalization/PCA96 variant, but remains substantially weaker than its matched control and the preserved incumbent. No model was promoted, and no new nested blend was started.

This experiment matches the inspected feature/preprocessing bundle, not the author's entire ensemble or historical environment. It uses block8 **before** final normalization, 256 features; PCA128 directly on float32 inputs without an external StandardScaler; and a separate PCA fitted on each endpoint's actual labeled training context. TabICL2.2.0, two estimators, fixed seeds and safe CPU settings remain pinned. The control uses the frozen600-dimensional ADME encoder cache, **not** the120 ADMETlab descriptors.

## Raw results

Lower ST-RAE, MAE and RMSE are better; higher R², Spearman and Kendall are better. Macro values average the four CYPs.

| Cohort | Representation | ST-RAE | MAE | R² | Spearman | Kendall | RMSE |
|---|---|---:|---:|---:|---:|---:|---:|
| OOF4905 | ADME600 | .654982 | .518885 | .427601 | .640424 | .468545 | .710521 |
| OOF4905 | Atom-JEPA pre-LN256 | .783594 | .590111 | .280128 | .515376 | .363921 | .801719 |
| own750 | ADME600 | .672160 | .552948 | .417847 | .631297 | .463676 | .746121 |
| own750 | Atom-JEPA pre-LN256 | .790099 | .617196 | .288039 | .539103 | .384930 | .829810 |
| reconstructed briford529 | ADME600 | .686302 | .497010 | .344163 | .633562 | .463068 | .686404 |
| reconstructed briford529 | Atom-JEPA pre-LN256 | .762196 | .538225 | .246837 | .537200 | .379487 | .740104 |

Paired Atom-JEPA-minus-ADME ST-RAE differences with conditional95% scaffold-bootstrap intervals:

- OOF: +.128612 [.109574, .144620].
- own750: +.117939 [.064868, .166343].
- briford529: +.075895 [.006645, .141319].

All five macro metric intervals favor ADME in this fixed comparison. The main contrary case is briford CYP2C9: Atom-JEPA ST-RAE .586462 versus ADME .617393. This isolated endpoint result does not reverse the macro comparison. Per-CYP values and intervals remain in `full-results/aggregate-metrics.csv` and `paired-deltas.csv`.

## What changed relative to the earlier bundle

| Representation/cohort | Earlier postnorm/scaledPCA96 bundle | Source-feature/unscaledPCA128 bundle |
|---|---:|---:|
| ADME, OOF | .658351 | .654982 |
| ADME, own750 | .684078 | .672160 |
| ADME, briford529 | .703871 | .686302 |
| Atom-JEPA, OOF | .780516 | .783594 |
| Atom-JEPA, own750 | .822539 | .790099 |
| Atom-JEPA, briford529 | .773669 | .762196 |

These are ST-RAE point comparisons. Atom-JEPA improves all five macro points on both outer cohorts versus its previous variant, but OOF is mixed and ST-RAE slightly worsens. ADME's preprocessing change improves ST-RAE and MAE in all three cohorts; some other outer-cohort metrics move slightly in the unfavorable direction. Every metric difference is preserved in `SOURCE_VS_PRIOR_BUNDLE.csv`.

The bundle changed normalization position, external scaling, PCA dimensionality, PCA solver convention, and the PCA fitting population. These results cannot attribute an effect to any one of those changes. They also do not establish that the published full solution was reproduced: our folds, ADME control, explicitly pinned model/library environment and overall ensemble differ. The exact inspected source lines are documented in `../representation-prep/ATOM_JEPA_SOURCE_FIDELITY.md`.

The original incumbent remains stronger as a practical standalone reference: raw ST-RAE .626205 on own750 and .622655 on briford529. That historical ensemble uses different data/components, so this is not a matched-data architecture ablation. No final blind prediction fit, ensemble coefficient, calibration, publication or leaderboard submission was added here.

## Data boundaries and verification

The readout uses only observed official primary pIC50 labels. Scalers are absent from this source bundle; every PCA is fitted only on that endpoint's labeled training rows. All56 saved PCA context memberships and raw means were independently verified, together with original IDs, SMILES, target bounds and prediction hashes. All five official metrics plus RMSE were independently recomputed; maximum discrepancy was1.11×10⁻¹⁶. Both largest-context profile predictions replayed byte-for-byte in the full run.

There are40 OOF calls and16 genuine outer-query calls. The latter fit the actual excluded training pools, not slices of global OOF. The two development holdouts have been reused and overlap by143 molecules; their sparse assay/analogue regime differs from the blinded challenge set. Bootstrap intervals are conditional on these saved predictions, not independent confirmation or training-seed uncertainty. Compound-level overlap with frozen pretraining data remains incompletely known.

## Encoder bank and operational repairs

All5,655 original coordinate records were reused unchanged. No new conformer generation or CIP audit loop was run. Final selected bank: `bank-lean-results/last-pre-norm.npy`, SHA256 `108551d476f865611f3be9da90c46e7c4d18943d2ea365b80b7a8e95099d62ea`. IDs/SMILES/order and shard/final-array equality were verified. Its simultaneously computed post-normalization reference is exactly equal to the old bank on all5,655 rows.

The original batch8 attempt stopped at408 rows because three coordinates of one embedding exceeded the predeclared numerical tolerance. The batch1 probe restored exact parity, but observed throughput initially did not fit the allocation. That run was stopped and its partial output preserved. One final optional-output check captured only the declared block8 feature plus the reference, omitting unused intermediate-layer storage. Both captures were bit-identical in the probe. Throughput recovered, but the paired timing comparison did **not** show that omitting outputs caused the recovery; no such causal claim is made.

The final bank is a fresh run, with no partial-bank mixing and no tolerance relaxation. Conservatively accounted bank compute was4,805.3 seconds (~80.1minutes), including stopped attempts, within90minutes. The final run used3,351.3seconds and peak1.64GB RSS. The bank records no model-label use or chemical alteration.

## Run identities and decision

- Final encoder bank: node `844c8394-4f1c-4ca0-a043-632cff5690c0`, run `4a8f3cf4-d5fe-43a7-aa26-327c6304e210`, source `eaa4f2ec03cc4ee0216868b943bc9e01be946f17`.
- Largest-context readout profile: run `82c9c911-0491-4a07-9c2e-498b38da0bca`, source `b723cb3`.
- Full56-call comparison: node `ef79ef52-e1f4-40f4-bc2d-35e0365cc411`, run `47b1a3f2-8ace-45af-895c-3db45b92f9aa`, source `d514ac6eb058defac6d71d947e3b824e19c65128`.
- Full comparison runtime894seconds, peak3.38GB RSS; local CPU only, no paid resources.
- Evidence: `BANK_VERIFICATION.json`, `FULL_VERIFICATION.json`, `PROFILE_REPLAY_PARITY.json`, `PREPROCESSING_TESTS.json`, and the frozen run artifacts under `full-results/`.

The supported decision is not to promote this standalone Atom-JEPA bundle. It corrects the source-fidelity question without inventing a gain or erasing favorable contrary cases. Additional ensemble work would require a separate decision based on these measured results; none has been launched.
