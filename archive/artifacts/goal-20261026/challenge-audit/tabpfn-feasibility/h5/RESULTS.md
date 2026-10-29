# H5 completed: matched ADME600 versus ADME720

ORX experimentaa7502ba-6e5b-4f7f-80d1-006d4ed10139, runa3b8945f-f37f-48f8-a776-845bc95749e5, immutable source704407a62fa9824a741dbde359c6103bc56de0ef. Exactly96 endpoint calls completed (48/view), summed fit/predict time633.31s; evaluation847.20s, ORX wall15m01s. No OOM, PCA, setting changes or extra model family. Same original lease/runtime as the parent ADMET120 experiment.

The frozen ADME600 cache has4905 official training structures only, verified exact original ID/SMILES/order and checkpoint/producer/runtime hashes. ADME720 appends the declared120 ADMET endpoints. Both use identical seed42, eight estimators, frozen inner/outer splits, endpoint-observed training labels and train-only preprocessing. Native is the same conditional historical reference; pretraining membership of the frozen encoder/teacher remains unknown. Official5655 teacher features are complete in the frozen18460 snapshot; this did not imply full32421 acquisition completion.

| Method | Own750 ST-RAE | Briford529 ST-RAE |
|---|---:|---:|
| Native | 0.62077693 | 0.64230890 |
| ADME600 | 0.65271220 | 0.66610532 |
| Native + ADME600, global | 0.61451354 | 0.62636886 |
| Native + ADME600, per-CYP | 0.61512083 | 0.63213366 |
| ADME720 | 0.65560943 | 0.66325227 |
| Native + ADME720, global | 0.61535236 | 0.62417566 |
| Native + ADME720, per-CYP | 0.61533309 | 0.62795667 |

Each cohort's training OOF chose the ADME720 per-CYP native blend: OOF ST-RAE0.6071877409 (own) and0.6102209886 (briford). Outer values did not select its weights or variant. The selected model's other macro metrics are:

| Cohort | MAE | R² | Spearman | Kendall |
|---|---:|---:|---:|---:|
| own750 | 0.52585654 | 0.47137845 | 0.66977950 | 0.49223460 |
| briford529 | 0.47157608 | 0.39169160 | 0.66095756 | 0.48661649 |

Relative to native, selected720 improves ownST-RAE/R² but worsens ownMAE and ranking; on briford it improves allfive macro metrics. However, the matched question is720 versus600: adding teacher features worsens ownST-RAE andMAE for standalone/global/per-CYP recipes, while improving both on briford. This is cohort-dependent benefit, not uniform improvement. `paired-view-metric-deltas.csv` preserves allfive paired point differences for allthree recipes.

Selected720-blend minus native ST-RAE is−0.00544384 onown, scaffold-bootstrap95% interval[−0.024593,0.013555]; briford−0.01435224,[−0.037302,0.009820]. All1000 resamples valid. These intervals compare withnative, not directly720with600, and are conditional on fitted predictions. Reused development cohorts overlap143 molecules; neither is independent confirmation.

All259 recovered files/12,100,824bytes and96 caches were verified. Fourteen saved raw metric rows independently rescored with zero difference. `recovery-certificate.json` binds outputs/logs; full raw/placed metrics, per-CYP results, OOF predictions, weights and bootstrap evidence remain in `recovered/h5-results/`. Parent full-data selection is separate; no finalrefit/submission happened here.

Follow-up frozen-encoder inference reproduced all4905 cached vectors at the prespecified tolerance before creating750 blind vectors; see `../blind-bank/REPORT.md`. No H5 training input was replaced. Shared instance57759747 was subsequently destroyed and absence verified04:49:28UTC. Posted matched charges for allthree runs total$0.274; see `../execution/invoice-verification.json`.
