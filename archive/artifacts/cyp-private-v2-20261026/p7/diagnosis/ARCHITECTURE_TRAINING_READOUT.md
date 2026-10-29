# Why P7 fusion worsened: measured evidence and remaining uncertainty

The direct-target deterioration is already present on training molecules. It is not the simple pattern of better primary training fit followed by worse held-out accuracy. The selected fusion checkpoints also depend strongly on their descriptor inputs. This does not establish that the graph encoder itself lost information: the head and encoder were trained together and the ablations shift their joint input distribution.

| Primary macro metric | Control train | Fusion train | Control test | Fusion test |
|---|---:|---:|---:|---:|
| ST-RAE ↓ |0.435664|0.519426|0.674456|0.702571|
| MAE ↓ |0.409749|0.459405|0.537914|0.556678|
| R² ↑ |0.605384|0.508068|0.394981|0.346449|
| Spearman ↑ |0.794669|0.728158|0.612770|0.572605|
| Kendall ↑ |0.611266|0.547410|0.442479|0.410951|
| RMSE ↓ |0.585861|0.658550|0.731901|0.761447|
| Bias |0.080154|0.080540|0.058628|0.069152|
| Prediction SD |0.646584|0.569918|0.603961|0.547384|

Stopping-cohort ST-RAE is also worse:0.698523 versus0.661283. Fusion predictions have less spread on both training and test molecules; the average target SD is about0.955. Training/stopping observations repeat across the five fitted outer models and are not independent samples. Exact paired IDs/masks, every per-CYP result and all other declared interventions are retained in `full-results/metrics-byfold.csv` and `metrics-pooled.csv`.

## Task-specific evidence

Saved full-pool OOF predictions improve only the five PubChem `max_response` tasks. The four direct targets, four organizer screen targets and five ChEMBL potency tasks all worsen in MAE. Across the five training partitions, observed-label exposures are: PubChem49.95%, ChEMBL35.16%, organizer screen10.85%, direct4.04%. Every real head has coefficient1 in the standardized masked-MAE loss. These are exposure counts, not measured gradient shares; coefficients and label masks are identical between the paired arms. The selective benefit is consistent with task competition or a shift in what the model optimizes effectively, but does not prove causal negative transfer or teacher-training overlap.

## Dependence interventions on the frozen fusion model

| Descriptor coordinates replaced by their saved training mean | Test ST-RAE |
|---|---:|
| None (original fusion) |0.702571|
| All120 |0.967681|
| CYP13 only |0.734256|
| Non-CYP107 only |0.890474|
| Vol/Dense2 only |0.703678|

Removing all descriptors reduces prediction SD to0.113343. The learned fusion function relies on descriptors; it does not become the separately trained zero-control model when they are removed. CYP versus non-CYP ablations differ in block size, redundancy and input shift, so they are not per-feature importance estimates. The Vol/Dense frozen mask does not rescue performance. This does not rule out an effect of the proven unit/scaling defect during training, but it prevents claiming that defect explains the entire failure.

## Architecture and training facts

Graph pooling is followed by learned batch normalization, then concatenation of120 training-standardized descriptors. Therefore “raw features were simply on a larger unnormalized scale than the graph” is not established. Message-passing dropout affects the graph pathway; the concatenated input has no separate input-dropout layer, while FFN dropout acts after the first mixing layer. Adam used its default zero weight decay. These facts permit optimization/regularization hypotheses; weight norms alone do not diagnose them.

The feature-input weight block began at exactly zero in both arms. Initial predictions, parameter hashes and batch-normalization states matched. Real-batch gradients reached the graph in both arms and the feature block in fusion. All five fusion checkpoints subsequently learned nonzero descriptor weights; all five zero controls retained zero descriptor weights. Thus the outcome is not an unused-input implementation bug. Median selected epoch was10 for fusion versus17 for control, but no train-loss history was retained in the original logger-disabled run. Earlier stopping alone is not evidence of overfitting; the new fitted-data inference supplies the actual primary training errors above.

## Competing explanations

1. **Head/optimization and task allocation:** descriptors help the highly represented PubChem response tasks while direct potency remains less well fitted. This is consistent with the selective auxiliary improvement and poorer primary training error. Actual training-time per-task gradient alignment was not recorded.
2. **Conditional encoder/head coadaptation:** the fusion function needs descriptors, and its graph-only ablation is weak. That is functional reliance, not proof that the encoder representation is intrinsically degraded; an independent common frozen-representation readout would be needed to separate head compatibility from representation quality.
3. **Feature-quality distortion:** the independently established Vol/Dense unit defect damages the original standardization. A matched retraining comparison of original, masked and deterministically repaired inputs can test its contribution. The frozen mask alone provides no rescue and no causal proof.

The next authorized P7R trial isolates the third explanation with four fresh matched arms and no change to the other118 feature columns, labels, molecules or loss. It does not test every task-competition explanation. No broad sweep or unsupported “overfitting solved” claim follows from this diagnostic.

## Numerical and execution provenance

The original32-row all18 raw-unit CPU parity gate failed for one fusion `cyp3a4_max_response` value: absolute error1.907e−5 at training SD38.229 (4.99e−7 SD). Both primary4 gates passed, with maximum error4.77e−7. That failure remains preserved. Root explicitly retained the original primary atol/rtol1e−5 and approved an auxiliary absolute bound1e−5 training SD. All ten full-diagnostic checkpoint comparisons passed these bounds; no tolerance was silently changed.

Full local ORX node `dcc4bfeb-80f5-4bc5-b435-4f0139da5063`, run `19fbf09f-f792-436b-bc26-121d8f74b655`, source `b34d082`. It took184seconds, with zero fitting, optimizer steps or GPU rental. Graph embeddings were reused across frozen interventions. This diagnostic is private; no submission or public artifact was created.

### Existing activation summary (no new model execution)

The saved frozen-inference activations do not show universal descriptor-scale domination. On official test molecules, median descriptor contribution norm into the first linear layer is16.50 versus19.48 for the graph contribution; the median per-molecule ratio is0.92 (95th percentile1.70). The fusion graph-input norm is9.07 versus14.71 in the zero control, and its graph preactivation contribution is19.48 versus84.39 in that control. This describes different encoder/head coadaptation at the selected checkpoints. It does not measure retained predictive information, establish causal degradation, or separate earlier stopping from representation changes. Branch correlations/cancellation and subsequent nonlinear layers also matter. Exact per-role summaries are in `branch-contribution-summary.csv`; training/stopping rows repeat across models.
