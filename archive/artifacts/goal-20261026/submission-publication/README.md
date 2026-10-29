# AdeliyaLL-CYP: Direct Inhibition method report

This report describes the prediction file identified below for the OpenADMET CYP Direct Inhibition challenge. The model combines the briford-style native Chemprop ensemble with one LightGBM regressor per CYP. Each added regressor receives 600 frozen ADME encoder coordinates from the Jeremy public recipe and 120 ADMETlab web-default properties. No blinded challenge labels were accessed.

The native expert uses the historical four-component, fivefold recipe with 18/8/6/1 tasks. Its public auxiliary supervision and legacy source-representation limitations are retained explicitly. Strict train-side identity/tautomer exclusions were applied to the validation references and full-data companion. A public Veith auxiliary-assay overlap with one blinded structure is retained under the external-data policy. This is a controlled use of the fixed expert, not a claim that its historical external supervision has been fully re-curated.

The added heads use only observed official experimental pIC50 labels from the 4,905-molecule training set. LightGBM uses 220 trees, L1 regression loss, learning rate 0.03, minimum child samples 10, L2 regularization 5 and seed 42. Full-training fivefold OOF selected **15 leaves and maximum depth 4** from the two evaluated settings (7/3 and 15/4). A median imputer is fitted only within the corresponding training partition; tree inputs are not standardized. The final heads are fitted on all available labels for their endpoint. Experimental confidence bounds are used for ST-RAE selection, never as input features.

For each CYP, the raw prediction is `(1-w) × native + w × LightGBM`. Four convex weights are fitted using training OOF predictions and the exact interval-distance ST-RAE objective. The final values are:

| CYP | Observed training labels | LightGBM share w |
|---|---:|---:|
| CYP1A2 | 1412 | 0.556672269914 |
| CYP2C9 | 1285 | 0.399600002649 |
| CYP2D6 | 1493 | 0.262281173926 |
| CYP3A4 | 2335 | 0.405995316174 |

The ADME encoder is frozen. The original 4,905-row embedding cache is retained exactly. Before generating the 750 query embeddings, the entire training cache was replayed with the same checkpoint and fingerprint routine: all values passed fixed absolute/relative tolerances of 10⁻⁵, with maximum absolute difference 5.96×10⁻⁸. Replayed training values were not substituted into the cache. The four final heads, fitted preprocessors and feature order were saved; independent reload produced exactly the same 750 head predictions without refitting.

ADMETlab acquisition covered **32,421 unique requested structures**: 32,419 returned complete 120-value vectors and 32,418 passed the declared feature policy. Two external requests (`Cl`, `N`) were explicitly rejected by the service and remain missing. One external antimony output was excluded because its returned graph could not be validated. A separate exact internal proton-transfer convention was documented and accepted as a feature representation; it does not establish the original assay microstate or equilibrium. Requested and returned structures are both preserved, with no identity merging or fabricated numerical values. All 5,655 official train/test inputs have complete eligible features. Separate source-supervision flags are retained for problematic external records; those records do not train the added heads.

Collecting 32,421 property outcomes does not mean the new regressors trained on 32,421 experimental labels. ADMETlab and ADME-encoder pretraining membership are unknown. The report does not redistribute participant checkpoints or claim that their pretraining was independent of every evaluation structure.

Development used our frozen 750-molecule cohort and a reconstructed 529-molecule briford cohort. They overlap by 143 molecules and have been reused during development. The reconstruction is not the author's recovered original split, and neither cohort is an independent post-selection confirmation set. Each cohort's hyperparameters and blend weights were fitted only inside its training pool. Final OOF uses a frozen fivefold partition of all official training molecules with the declared scaffold/parent/strict-equivalence exclusions; native components retain their separate fold assignments.

Raw macro results before the fixed serving placement:

| Cohort | Model | ST-RAE ↓ | MAE ↓ | R² ↑ | Spearman ↑ | Kendall ↑ |
|---|---|---:|---:|---:|---:|---:|
| own750 | Corrected native | 0.620777 | 0.523427 | 0.470486 | 0.673245 | 0.495502 |
| own750 | ADME + ADMETlab blend | 0.615706 | 0.528984 | 0.455165 | 0.673106 | 0.494468 |
| briford529 | Corrected native | 0.642309 | 0.475777 | 0.384635 | 0.653092 | 0.477189 |
| briford529 | ADME + ADMETlab blend | 0.579888 | 0.460875 | 0.416476 | 0.671114 | 0.493706 |

The selected recipe gives a modest ST-RAE gain on our cohort and a larger gain on the reconstructed briford cohort. Our other four metrics worsen. Paired scaffold-bootstrap 95% intervals for selected-minus-native ST-RAE are **[-0.025605, 0.012218]** and **[-0.091215, -0.036987]**, respectively. These intervals condition on saved predictions and do not account for model selection or training-seed uncertainty. The simpler ADMET-only global blend remains better on our cohort alone. Adding ADMETlab beyond the ADME encoder has a modest, cohort-dependent effect; the entire gain over native cannot be attributed to ADMETlab labeling. The final recipe was selected as a development tradeoff, without claiming uniform dominance.

The submission retains the published native population-placement procedure, fixed before the new feature results. It uses published leaderboard-derived population estimates, training-OOF statistics and the moments of the query predictions. No new constants were fitted to this submission's leaderboard feedback. This is a competition population assumption, not independently validated local calibration. Its adverse local diagnostics are preserved:

| Cohort | Model | ST-RAE ↓ | MAE ↓ | R² ↑ | Spearman ↑ | Kendall ↑ |
|---|---|---:|---:|---:|---:|---:|
| own750 | Corrected native | 1.058445 | 0.734638 | 0.127505 | 0.673245 | 0.495502 |
| own750 | ADME + ADMETlab blend | 1.102332 | 0.753154 | 0.101054 | 0.673106 | 0.494468 |
| briford529 | Corrected native | 1.087466 | 0.636389 | 0.057263 | 0.653093 | 0.477213 |
| briford529 | ADME + ADMETlab blend | 1.059550 | 0.628311 | 0.083221 | 0.671114 | 0.493706 |

Full-training OOF for the selected final model is ST-RAE 0.615078, MAE 0.504636, R² 0.443286, Spearman 0.663043 and Kendall 0.487661. These are selection estimates, not independent test results. The exported file has exactly 750 official IDs/SMILES and four finite pIC50 columns, passes the official validator and stricter identity/order/spread checks, and reconstructs exactly from the saved heads and native predictions.

Final source revision: `7a62af907462847097a9ce4cf05921af404f6776`.
Prediction-file SHA256: `91fa8bf0870f68071b04183166b1507c20001d04f3ae3fb5f4d055618fff98c7`.
Frozen feature-snapshot SHA256: `eddc54fa54df33f0e766295b362d5488000c3697553beac1430ac6ae82f5a553`.
ADME encoder SHA256: `b8137a0d202669baa9747f21eac4ef78b000afe68a3f100d25c849c41ad8a3d5`.
Final CPU versions: NumPy 2.5.4, SciPy 1.18.1, pandas 3.1.0, scikit-learn 1.9.1, LightGBM 4.6.0, RDKit 2026.9.1, PyTorch 2.8.0 and Chemprop 2.2.1. Encoder generation used its separately verified CUDA runtime.

References: [official challenge](https://huggingface.co/spaces/openadmet/cyp-challenge), [official dataset revision](https://huggingface.co/datasets/openadmet/cyp-challenge-train-test/tree/d7eb3c973dca01aad8e33c91c29e5123fd925d8f), [official scoring repository](https://github.com/OpenADMET/CYP-Challenge-Tutorial/tree/832ae6d6447b07c2c71059de34d07f1130388247), [briford method](https://supercowpowers.github.io/workbench/blogs/cyp_challenge/), [Jeremy recipe](https://github.com/jeremycheminf/openadmet_scripts/tree/d3a5549e0c98167435cbf8f5115c68a9a184ed7a/CYP_Challenge), [ADMETlab service](https://admetlab3.scbdd.com/).


**Observed live leaderboard result, 26 October 2026.** The submission was processed successfully and the report link is valid, but performance worsened on every displayed metric. The live board covers a subset of the hidden test set; these are not full-test results.

| Entry | MA-ST-RAE ↓ | MAE ↓ | R² ↑ | Spearman ↑ | Kendall ↑ | Observed rank |
|---|---:|---:|---:|---:|---:|---:|
| Previous native submission | 0.4425 | 0.6365 | 0.6171 | 0.7546 | 0.5775 | 24 |
| This ADME + ADMETlab submission | 0.4616 | 0.6479 | 0.6044 | 0.7482 | 0.5698 | 38 |

The local validation improvement did not transfer to the live leaderboard. This was not a leaderboard ablation of adding features to the exact previous predictor: ten of the twenty native models were also refitted after stricter fold exclusions, while ten were reused. The refitted native ensemble alone has not been scored on the leaderboard, so the deterioration cannot be attributed solely to ADMETlab or the added readouts.

The API accepted the file at 07:10:52 UTC, with a 2.83-second transport call. The new scored row was first observed at 07:27:59 UTC and reconfirmed at 07:49:06 UTC. These observation times do not measure the server's exact processing duration. The original report version and submission file remain archived; no additional submission or restoration was made as part of this report update.
