# Completed campaign comparison

Snapshot: 2026-10-24T00:06:31.319549+00:00. Lower ST-RAE is better. This report recomputes saved prediction scores and does not fit models or select a new recipe.

Completed: **48 base configurations**, **8 post-processing methods**, plus the derived reference ensemble: **57 named methods** in total. There are **122 completed method/cohort/seed evaluations** (114 four-target and 8 CYP2D6-only diagnostics), backed by **500 distinct completed fold-worker jobs**. Seed42 comparisons include four configurations evaluated only on briford529. Duplicate local mirrors, failed attempts and discarded host1seed142 partial jobs are excluded from these counts.

All saved metrics reproduced from predictionCSV files; maximum absolute discrepancy=0. Full configurations, raw/calibrated scores, endpoint results and evidence hashes are in [campaign_comparison_completed.json](/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/notes/campaign_comparison_completed.json); flat comparison table: [campaign_comparison_all_scores.csv](/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/notes/campaign_comparison_all_scores.csv).

## What the gated candidate actually does

`reference_reweight_affine` is **calibration-only on own750 for both seeds**, but **component reweighting plus affine placement on briford529 for both seeds**. The observation that all extra weights were zero in own750seed42 must not be generalized to the other cohort. All16 target/seed/cohort parameter sets were inspected, and their prediction vectors reconstructed from the source components with maximum error1.78e-15; every gate-copy prediction matches exactly.

| Cohort | Seed | Selected regularization | Mechanism |
|---|---:|---|---|
| own750 | 42 | positive_affine_l1_0.01 | raw-reference affine calibration only |
| briford529 | 42 | positive_affine_l1_0 | component reweighting plus per-target affine placement |
| own750 | 142 | positive_affine_l1_0.01 | raw-reference affine calibration only |
| briford529 | 142 | positive_affine_l1_0 | component reweighting plus per-target affine placement |

Own750 has coefficients only on the raw reference ensemble. Per-target slopes/intercepts are:

| Seed | Target | Slope | Intercept |
|---|---|---:|---:|
| 42 | CYP1A2 | 0.833051 | 0.906923 |
| 42 | CYP2C9 | 0.968844 | 0.240449 |
| 42 | CYP2D6 | 1.000000 | 0.030360 |
| 42 | CYP3A4 | 0.855914 | 0.721371 |
| 142 | CYP1A2 | 0.808824 | 1.061812 |
| 142 | CYP2C9 | 0.972368 | 0.217180 |
| 142 | CYP2D6 | 1.000000 | 0.037860 |
| 142 | CYP3A4 | 0.868172 | 0.717982 |

Briford529 uses the following raw component coefficients; the separate raw-reference coefficient is zero. Values need not sum to1, because their sum also sets an affine slope.

| Seed | Target | Union18 | MTaux8 | 2D6 single | 2D6 aux | Intercept |
|---|---|---:|---:|---:|---:|---:|
| 42 | CYP1A2 | 0.496431 | 0.260194 | 0.000000 | 0.000000 | 1.324925 |
| 42 | CYP2C9 | 0.530643 | 0.404544 | 0.000000 | 0.000000 | 0.357285 |
| 42 | CYP2D6 | 0.199869 | 0.148319 | 0.138860 | 0.494216 | 0.122981 |
| 42 | CYP3A4 | 0.489328 | 0.371590 | 0.000000 | 0.000000 | 0.739190 |
| 142 | CYP1A2 | 0.440309 | 0.350506 | 0.000000 | 0.000000 | 1.115491 |
| 142 | CYP2C9 | 0.563418 | 0.385046 | 0.000000 | 0.000000 | 0.319070 |
| 142 | CYP2D6 | 0.335623 | 0.129718 | 0.137767 | 0.320958 | 0.370897 |
| 142 | CYP3A4 | 0.502207 | 0.345282 | 0.000000 | 0.000000 | 0.804116 |

For CYP2D6 the normalized component proportions change from reference25%each to20.37/15.12/14.15/50.37% atseed42, and36.32/14.04/14.91/34.73% atseed142. This is a genuine redistribution. The current evidence does not isolate a causal contribution of calibration versus reweighting; no new ablation was run.

## Declared gate results

| Cohort | Seed | Reference | Candidate | Delta |
|---|---:|---:|---:|---:|
| own750 | 42 | 0.608761984 | 0.607682125 | -0.001079859 |
| own750 | 142 | 0.604181250 | 0.602246309 | -0.001934942 |
| briford529 | 42 | 0.622740658 | 0.620723613 | -0.002017045 |
| briford529 | 142 | 0.641362686 | 0.639370678 | -0.001992008 |
| briford529 | averaged predictions | 0.628930601 | 0.626781927 | -0.002148674 |
| own750 | averaged predictions | 0.604202870 | 0.602380634 | -0.001822236 |

The saved gate certificate passes both paired-seed and averaged-vector criteria. Bootstrap intervals cross zero on both cohorts: this is a small observed improvement, not statistical proof. For averaged predictions, briford529 CYP2C9 worsens by+0.001907ST-RAE, while its other three targets improve; own750 improves on all four targets.

## Every completed method at seed42

Selected scores use development-selected calibration/post-processing, not a minimum chosen on outer labels. Raw scores and endpoint details remain in JSON/CSV. A dash means no completed cohort evaluation. A dagger marks a one-target CYP2D6 diagnostic. Monroe rows remain exploratory because supervised-pretraining membership is unresolved.

| Batch | Method | own750 | briford529 |
|---|---|---:|---:|
| B0_G0_structure | catboost_descriptors_mae | 0.770373 | 0.761864 |
| B0_G0_structure | extratrees_morgan_fcfp | 0.792830 | 0.816951 |
| B0_G0_structure | extratrees_path_atompair | 0.817609 | 0.814888 |
| B0_G0_structure | krr_count_a0.1 | 0.746904 | 0.732113 |
| B0_G0_structure | krr_count_a1.0 | 0.764822 | 0.738279 |
| B0_G0_structure | krr_count_a10.0 | 0.843758 | 0.832377 |
| C0_TabICL | tabicl_foundation_pca100 | 0.761817 | 0.741118 |
| C0_TabICL | tabicl_foundation_pca50 | 0.780603 | 0.758683 |
| C0_TabICL | tabicl_morgan_pca100 | 0.855593 | 0.829524 |
| C0_TabICL | tabicl_rdkit_pca100 | 0.752884 | 0.748449 |
| C1_C2_TFM | tabicl_molformer_pca100 | 0.793209 | 0.783105 |
| C1_C2_TFM | tabicl_monroe_pca100 | 0.680787 | 0.709003 |
| C1_C2_TFM | tabicl_monroe_pca50 | 0.676469 | 0.699610 |
| C1_C2_TFM | tabpfn_chemeleon_foundation_pca100 | 0.767982 | 0.740386 |
| C1_C2_TFM | tabpfn_chemeleon_foundation_pca50 | 0.780129 | 0.763578 |
| C1_C2_TFM | tabpfn_molformer_pca100 | 0.793271 | 0.775833 |
| C1_C2_TFM | tabpfn_monroe_pca100 | 0.677633 | 0.694711 |
| C1_C2_TFM | tabpfn_morgan_rdkit_pca100 | 0.735347 | 0.733648 |
| C3_feature_retention | tabpfn_foundation_pca1024_scale1 | 0.764073 | 0.743229 |
| C3_feature_retention | tabpfn_foundation_pca512_scale0 | 0.756799 | 0.762082 |
| C3_feature_retention | tabpfn_foundation_pca512_scale1 | 0.756453 | 0.732954 |
| C3_feature_retention | tabpfn_molformer_raw | 0.801249 | 0.772268 |
| C3_feature_retention | tabpfn_rdkit_raw | 0.749854 | 0.730187 |
| C4_clean_adapted_briford | adapted_official_aux_tabpfn_pca100 | — | 0.691417 |
| C4_clean_adapted_briford | adapted_official_aux_tabpfn_pca512 | — | 0.694870 |
| C4_clean_adapted_briford | adapted_tox21_tabpfn_pca100 | — | 0.684011 |
| C4_clean_adapted_briford | adapted_tox21_tabpfn_pca512 | — | 0.690901 |
| D0_D1_public_r1 | chemeleon_official_plus_bindingdb | 0.681272 | 0.683732 |
| D0_D1_public_r1 | chemeleon_official_plus_both | 0.673240 | 0.673753 |
| D0_D1_public_r1 | chemeleon_official_plus_tox21 | 0.671410 | 0.673662 |
| D2_patent | chemeleon_official_plus_patents | 0.677733 | 0.687571 |
| D2_patent | chemeleon_patents_interval | 0.674654 | 0.704203 |
| E0_A0_neural | chemeleon_all_official_aux | 0.678975 | 0.685359 |
| E0_A0_neural | chemeleon_aux_interval | 0.682438 | 0.708726 |
| E0_A0_neural | chemeleon_direct_interval_lowLR | 0.700930 | 0.737492 |
| E0_A0_neural | chemeleon_direct_mae_lowLR | 0.689341 | 0.707655 |
| E0_A0_neural | chemeleon_direct_mse_lowLR | 0.724937 | 0.716540 |
| E0_A0_neural | scratch_all_official_aux | 0.633568 | 0.657697 |
| E0_A0_neural | scratch_direct_interval | 0.678408 | 0.683352 |
| E1_metric_weights | chemeleon_aux_inv_interval | 0.684009 | 0.710039 |
| E1_metric_weights | chemeleon_aux_inv_mae | 0.681539 | 0.686419 |
| E1_metric_weights | chemeleon_aux_strae_interval | 0.684897 | 0.702327 |
| M0_structure_meta | population_krr_default | 0.764535 | 0.741573 |
| M0_structure_meta | stack_structure6 | 0.733864 | 0.716448 |
| M0_structure_meta | width_catboost | 0.772228 | 0.747273 |
| M0_structure_meta | width_krr_default | 0.750474 | 0.704910 |
| M1_reference_reweight | reference_plus_clean23_affine | 0.613258 | 0.631365 |
| M1_reference_reweight | reference_plus_tox21_affine | 0.610530 | 0.627248 |
| M1_reference_reweight | reference_reweight_affine | 0.607682 | 0.620724 |
| M1_reference_reweight | reference_reweight_simplex | 0.612659 | 0.646074 |
| R0_reference_seed42 | 2d6isoform6 † | 0.760758 | 0.802515 |
| R0_reference_seed42 | 2d6single † | 0.862441 | 0.896010 |
| R0_reference_seed42 | briford_reference | 0.608762 | 0.622741 |
| R0_reference_seed42 | mtaux8 | 0.640767 | 0.637321 |
| R0_reference_seed42 | union18 | 0.614420 | 0.618257 |
| U0_unimol2_controls | unimol2_rbf_krr_pca100 | 0.871716 | 0.866960 |
| U0_unimol2_controls | unimol2_extratrees_raw | 0.856570 | 0.875209 |

The two Uni-Mol2 controls are fixed seed42 evaluations: RBF-KRR uses train-only scaledPCA100,alpha0.1,gamma0.01; ExtraTrees uses raw features,400trees,max_features0.5,min_samples_leaf2. Both are worse than the qualified reference/candidate on both cohorts. This does not establish that all possible Uni-Mol2 learners are inferior.

## Failures, repairs and unfinished evidence

- The original public-data batch failed on an unparseable normalized external SMILES. Its three recipes completed in the repairedD0_D1_public_r1 batch; the failed attempt contributes no successful method/cohort result.
- Host1seed142 reference was cancelled for resource isolation after6completed workers. The fresh host2seed142 reference completed40workers; its successful outputs supply confirmation. Original partial outputs are not counted or reused.
- E0_A0 and E1 retain failed original orchestration records, even though all their worker predictions completed and later completed collection runs produced the scored summaries. The JSON preserves both the registry and the successful evidence.
- PCBA source transport failed twice before the range-download repair succeeded. Monroe remains exploratory and excluded from automatic promotion: raw supervised label overlap is established, but historical checkpoint membership/head retention is unresolved.
- OriginalCheMeleon, MoLFormer and Monroe extracted5655rows with zero failed rows; Uni-Mol2 also completed5655x768 features. Two fixed Uni-Mol2 controls subsequently completed on both cohorts locally, adding2configurations,4evaluations and20fold-worker jobs. Their scores are included above; neither is used by the qualified candidate.
- The saved project registry includes preparation/audit/repair runs and may lag current progress; it must not be reported as the count of trained methods.
- The two holdouts share143molecules and have been inspected during development. Neural OOF early stopping and non-nested calibration remain limitations. Historical leaderboard values are not numerically interchangeable with this reconstructed local reference.

## Production prediction snapshot

- FINAL_reference_seed42: 20/20fold completion markers; final aggregate marker=True. prediction artifact set complete.
- FINAL_reference_seed142: 17/20fold completion markers; final aggregate marker=False. not complete in inspected local snapshot; may lag remote progress.

ActualTEST labels are unavailable; production fits have no reported test score. Root owns final recipe application, submission and resource lifecycle.
