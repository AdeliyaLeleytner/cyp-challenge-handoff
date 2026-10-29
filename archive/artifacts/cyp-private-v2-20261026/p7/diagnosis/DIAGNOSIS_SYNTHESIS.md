# Why ADMET fusion worsened this Chemprop experiment

Private diagnosis,26October2026. This concerns the matched P7 18-task graph component, not a causal reconstruction of the rank38 submission and not all possible uses of ADMET features.

## Measured failure

Five-fold pooled official OOF scores changed from control to fusion: ST-RAE0.674456→0.702571, MAE0.537914→0.556678, RMSE0.731901→0.761447, R²0.394981→0.346449, Spearman0.612771→0.572605 and Kendall0.442480→0.410951. Macro IC50 accuracy within a factor2 fell39.74%→38.58%; within a factor10 fell85.62%→85.24%. These additional bands correspond to0.30103 and1.0 pIC50 error; they are not new inhibitor-class thresholds.

Prediction dispersion shrank in every CYP and ranking worsened in every CYP. For2D6, predicted/observed SD fell0.462→0.366 while Spearman fell0.427→0.372. A simple affine adjustment cannot restore lost ordering. Individual outcomes are mixed:3,109/6,525 measured cells improved;2D6 within10fold and3A4 within2fold also improve slightly. Only120 same-fold measured close pairs exist, with none for2C9. This cannot establish universal activity-cliff failure.

## It is not the simple overfitting pattern

Frozen-checkpoint inference on matching training IDs gives primary MAE0.409749→0.459405 and ST-RAE0.435664→0.519426. Primary fitting is worse on training, stopping and test data. This argues against the simple explanation that the larger model memorized primary labels better and merely generalized worse. Earlier stopping or lower training accuracy does not uniquely identify the optimization mechanism.

In contrast, the same fusion checkpoints improve all five PubChem maximum-response tasks by about12–13% MAE. All four direct-potency, all four single-screen and all five ChEMBL-potency heads worsen. Around96% of observed training label terms are auxiliary; this is a count, not a measurement of gradient dominance. The pattern is consistent with task competition or a useful teacher signal being exploited for an endpoint different from the target potency. A matched routing/loss intervention is still needed to establish that cause.

Mean-zero frozen interventions establish dependence: all120 features removed increases test ST-RAE to0.967681; CYP13 removed gives0.734256; non-CYP107 removed gives0.890474. These inputs are distribution shifts and do not prove irreversible graph-encoder damage or predict retraining without a block.

## A real descriptor unit defect

The public Scopy radius table mixes H1.20/C1.70 with B192/Se190/etc in a formula documented in Å³. Radius errors of100 yield volume contributions a million times too large. The unrounded equation reproduces all85 extreme saved ADMET volumes and200 ordinary controls to floating-point precision. The deployed server revision remains unknown; the numerical formula match is verified. [Pinned source](https://github.com/kotori-y/Scopy/blob/ed2651583ee25c0a7f9767e3ed54452f81b3de79/scopy/ScoDruglikeness/molproperty.py#L842).

For CHEMBL113478 (MW315.9), Vol57,461,988.7 becomes222.12 under the unit-consistent version of the same approximation. Original training means were71k–118k versus ordinary medians357–362; the central98% volume range occupied only~0.0003–0.0004 standardized units. The earlier identity/finite-value audit missed feature physical plausibility.

The defect is not yet the explanation of the whole score loss. Switching Vol/Dense to their standardized mean after training gives ST-RAE0.703678, versus0.702571 unchanged. A training-time effect remains possible; post-training masking cannot undo it.

The derived repair changes only170 cells in85 rows, preserves118 other feature columns exactly, preserves every molecule/label/fold and retains the original cache. Corrected features remain an atom-additive approximation, not experimental or true3D volumes. See repair-stage/REPORT.md.

## Teacher information is useful but different

The120 columns mix structure-derived descriptors, alerts, modeled properties and13 CYP classifier outputs. Own-CYP inhibitor probabilities have Spearman associations~0.27–0.49 with direct pIC50. They are not measured IC50 or percent inhibition. Some confidence-supported large potency differences are ordered correctly even with near-saturated teacher probabilities, so a blanket “saturation destroys SAR” explanation is unsupported.

The ADMETlab3 paper retrieved through PubMed describes a multitask Chemprop/DMPNN framework with descriptor augmentation and mixed classification/regression endpoints. That gives context for correlated information, not proof of which current teacher records overlap our data. [Paper](https://doi.org/10.1093/nar/gkae236).

## Next discriminating intervention

P7R uses fresh matched controls: graph-only zero descriptors, original fusion, Vol/Dense masking and unit-repaired Vol/Dense fusion. All other features/data/training choices remain fixed. This estimates the unit defect's training effect before broad scaling or new architectures are blamed or promoted. P8/P9 are held. No public disclosure or submission.

Evidence: results/COMPLETE.json; full-results/metrics-pooled.csv; saved-oof-task-comparison.csv; FEATURE_SEMANTICS.md; volume-source/NUMERICAL_PROOF.json; repair-stage/FINAL_VERIFICATION.json. Full-checkpoint diagnosis ORX run19fbf09f-f792-436b-bc26-121d8f74b655 used10 checkpoints,184seconds localCPU, no optimizer steps or new provider spend. Primary numerical fidelity stayed within the original tolerance; the original too-strict raw auxiliary gate failure is preserved, with approved task-SD-aware checks documented separately.

