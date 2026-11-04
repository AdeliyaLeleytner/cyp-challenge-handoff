# Direct CYP Inhibition: Model Methodology

**Author:** Adeliya Leleytner  
**Track:** OpenADMET CYP Challenge, Regression Prediction  
**Documentation date:** 4 November 2026

## Scope and artifact identity

This report describes the selected four-endpoint model for CYP1A2, CYP2C9, CYP2D6 and CYP3A4. The output is direct-inhibition pIC50 for each of the 750 blinded query molecules. The owner confirmed that the selected file was resubmitted before the challenge deadline. This is a retrospective methodological description, not a claim that the report itself was present before the deadline.

The exact prediction artifact is identified by SHA256:

```text
9e234a1335d43337692f0517af4323303c0d9a39454d073e3c5dfb2ace85b153
```

The report concerns this frozen artifact. Subsequent experimental CYP1A2 and CYP3A4 overlays are not part of it. No checkpoint files are included in this documentation update. Data sources and assay distinctions are detailed in [Data description](DATA_DESCRIPTION.md).

## 1. Endpoint-specific ensemble

The four endpoints use different combinations of models. Selecting a single model by the macro-average would discard components useful for an individual isoform.

| Endpoint | Selected predictor |
|---|---|
| CYP1A2 | Equal-weight combination of two five-fold directed message-passing ensembles: an 18-task model and an 8-task model |
| CYP2C9 | Weighted combination of separately optimized 18-task and 8-task five-fold directed message-passing ensembles |
| CYP2D6 | A standardized four-family molecular ensemble, combined with a five-fold screen-informed support-vector regressor |
| CYP3A4 | Equal-weight combination of the two five-fold directed message-passing ensembles used for CYP1A2 |

The 8-task model predicts four official direct-inhibition endpoints and four official single-concentration screening readouts. The 18-task model adds five ChEMBL CYP endpoints and five PubChem/Veith CYP screening endpoints. External assays are separate auxiliary outputs, rather than pooled as interchangeable direct-inhibition labels. Missing outputs are masked.

For each family, predictions are first averaged across its five trained folds. CYP1A2 and CYP3A4 then use weights 0.5/0.5 across the two task sets. The CYP2C9 weights are **0.8656802700078715** for the 18-task family and **0.1343197299921285** for the 8-task family. These nonnegative, sum-to-one weights were selected using development out-of-fold predictions and frozen for production inference. The final choice of endpoint columns also used feedback from scored submissions; it is not an independent validation procedure.

## 2. Molecular graph models

The graph models use Chemprop-style directed bond message passing followed by molecular aggregation and a feed-forward readout. Shared molecular representations support separate assay heads. Primary and auxiliary supervision retain their own masks and weights.

The optimized CYP2C9 components use the following selected settings; these settings should not be attributed to the older CYP1A2/CYP3A4 components.

| Setting | 18-task CYP2C9 component | 8-task CYP2C9 component |
|---|---:|---:|
| Message-passing hidden dimension | 384 | 768 |
| Message-passing depth | 5 | 3 |
| Aggregation | Normalized sum, normalization 100 | Mean |
| Readout hidden dimension | 192 | 300 |
| Readout layers | 1 | 3 |
| Dropout | 0.3085583 | 0.1741306 |
| Batch size | 128 | 32 |
| Optimizer | AdamW | AdamW |
| Peak learning rate | 0.0008777288 | 0.0003647454 |
| Weight decay | 0.01713628 | 0.000008448673 |
| Warm-up epochs | 5 | 7 |
| Maximum epochs / patience | 160 / 25 | 160 / 25 |
| Screening auxiliary weight | 1.0 | 0.6 |
| External auxiliary weight | 0.3 | Not applicable |

Both use cosine scheduling, gradient clipping at 1.0, mixed precision, seed 42 and five scaffold folds. Checkpoint selection uses primary-task ST-RAE. The selected loss is interval MAE: distance outside a supplied target interval, with zero error inside it. This distinction matters because minimizing ordinary point MAE or MSE is not equivalent to optimizing an interval-aware score. Historical components use their own fixed recipes; the entire ensemble was not jointly optimized under one common loss.

## 3. CYP2D6 molecular base ensemble

The CYP2D6 base contains four families: two separately trained single-target graph-regression recipes, a 13-head multitask graph model, and a four-target Uni-Mol2 model. Each family supplies a five-fold average prediction. The four vectors are standardized separately across the 750 query molecules, averaged equally, and standardized again.

The graph components combine molecular graph features with molecular descriptors. Their fitted target and descriptor scalers are inverted or applied consistently at inference. Molecular preparation and historical preprocessing limitations are described in the data report.

The three-dimensional component fine-tunes a publicly pretrained **Uni-Mol2 84M** molecular model using generated conformers. It uses four masked regression outputs, masked MAE, batch size 8, learning rate 1e-4, five scaffold folds, an epoch cap of 40 and patience 8. Generated conformers cover all 4,905 official training molecules and all 750 query molecules. No experimental test-set protein–ligand coordinates or measured query responses are used by this component.

Let `z(x) = (x - mean(x)) / sd(x, ddof=1)`, where statistics are computed over the complete query vector. If the four family predictions are `p1,...,p4`, the molecular base vector is:

```text
g = z((z(p1) + z(p2) + z(p3) + z(p4)) / 4)
```

## 4. CYP2D6 screen-informed regression

The additional CYP2D6 predictor transfers information from the official single-concentration **+NADPH log2FC** screen. The screen outputs remain distinct from direct-inhibition pIC50. In particular, query screen responses are predicted from structure, not obtained from experimental query measurements.

### Screening teachers

Four RBF support-vector regressors predict screening responses for CYP3A4, CYP2C9, CYP2D6 and CYP1A2, in that order. Inputs are a frozen 600-dimensional ADME molecular embedding, standardized and reduced to 128 principal components without whitening.

Each teacher uses `C=1`, `epsilon=0.05`, and `gamma=1/trace`, where `trace` is the training PCA feature variance trace. Its response is standardized using fitting rows and converted back to screening units after prediction. ADME600 denotes a learned embedding, not 600 experimental ADMET measurements.

### CYP2D6 student

The student uses a separate ADME-adapted CheMeleon representation of 2,048 dimensions. StandardScaler and PCA128 transform this molecular block. The four teacher predictions are standardized separately, then multiplied by `sqrt(trace/4)` with block multiplier lambda=1. The two blocks are concatenated.

An RBF SVR predicts raw CYP2D6 pIC50 with `C=0.1`, `epsilon=0.05` and `gamma=1/trace` of the molecular PCA block. The student target is not separately standardized. The exact adapted embedding matters; an arbitrary checkpoint with the same feature dimension is not an equivalent replacement.

### Cross-fitting

The production recipe has five fixed outer folds. Within each fold, three identity-group cross-fitting contexts generate teacher features for student-training rows. A fourth teacher context fitted on the outer training partition predicts the held-out and query rows. This produces 4 screening heads × 4 contexts × 5 outer folds = **80 teachers**, plus **5 students**.

Scalers and PCA are fitted within their corresponding fitting contexts. The student therefore does not train on in-sample predictions from teachers fitted to the same rows' screening outcomes. The selected recipes were frozen before production fitting. Production uses the permitted labels from the full official training pool, with the fold exclusions above. The new production OOF outputs were not used for another hyperparameter search. Serialized model/preprocessor reloads were checked against their original predictions.

## 5. Export and output calibration

The exported values include distribution placement, so raw model outputs alone do not specify the submission. Normalization is transductive: it uses the prediction distribution of the full 750-molecule query batch. It does not use query labels. Predicting a different batch and independently normalizing it can give different values.

For CYP1A2, CYP2C9 and CYP3A4, a raw ensemble vector `r` is transformed as:

```text
output = max(1.0, mu + s * z(r))
```

| Endpoint | mu | s |
|---|---:|---:|
| CYP1A2 | 4.412 | 1.2154686960285146 |
| CYP2C9 | 4.830 | 0.9854274458993569 |
| CYP3A4 | 4.880 | 1.1162238151378616 |

These fixed values combine historical distribution-placement constants with component-specific OOF correlation calculations. Their historical derivation used leaderboard feedback. They must not be described as independently learned from training labels alone or as guaranteed population parameters for unseen data.

For CYP2D6, let `u` be the average raw prediction from the five screen-informed students and `g` the standardized molecular base defined above. The exact final operation is:

```text
m = 0.75 * g + 0.25 * z(u)
CYP2D6 = 3.648902397881585 + 0.8632893050271784 * z(m)
```

This operation uses sample standard deviations (`ddof=1`) and **no floor for CYP2D6**. The 25% student contribution and serving formula were frozen before generating the new query predictions. The fixed location and scale also retain their historical leaderboard-informed origin; no new hidden labels were fitted for this overlay.

The final assembly preserves the CYP1A2, CYP2C9 and CYP3A4 columns exactly while replacing CYP2D6. The stored CSV was checked for 750 unique molecule IDs, exact identity/SMILES alignment, finite values and the official required columns, and passed the official submission validator. The saved-component reconstruction of its CYP2D6 column was exact in the recorded verification.

## 6. Validation and interpretation

Development included scaffold-separated evaluation and identity-grouped hit-expansion views intended to examine transfer to nearby analogues. Some hit-expansion views overlap and were reused during model development. They are repeated development views, not independent test sets. The challenge query selection also differs from the training distribution: hit expansion was driven by CYP1A2, CYP2C9 and CYP3A4, not CYP2D6.

MA-ST-RAE is the macro-average of the four endpoint ST-RAE values. Local comparisons distinguish raw predictions from the exact exported mixture and normalization. Endpoint selection and historical calibration used leaderboard feedback, which creates additional adaptation to the public evaluation subset.

The exact final molecular base did not have matched held-out predictions for every local screen-student comparison. Comparisons against other local references therefore do not constitute an independent evaluation of the final exported ensemble. Some historical base components also fitted scaling transforms before CV; downstream cross-fitting does not remove those upstream limitations. The molecular base and the newer teacher–student component should not be treated as having one uniformly leakage-free development protocol.

The model's performance on the final hidden evaluation must be assessed by the organizers. Successful file validation, exact inference replay, or local selection results do not establish that result.

## 7. Software and model families

The implementation uses RDKit molecular processing, Chemprop directed message-passing models, Uni-Mol2 three-dimensional molecular representations, pretrained ADME/CheMeleon representations, and scikit-learn scaling, PCA and support-vector regression. This report describes their application and ensemble assembly; it does not claim invention of these underlying methods.

This documentation update includes methodology only. It does not distribute trained weights, serialized models, private runtime configuration or raw prediction arrays.
