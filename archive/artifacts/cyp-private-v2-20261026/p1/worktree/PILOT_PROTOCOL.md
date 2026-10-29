# ADMETlab500 matched pilot — frozen protocol before outcome inspection

Question: Do the500 user-supplied web-default feature rows justify collecting more ADMETlab predictions for the CYP task?

The file contains500 unique request SMILES and120 actual endpoint identities.431 map to labeled official training molecules and69 to the blinded test, which is not scored. All supplied endpoints, including CYP inhibitor/substrate probabilities, are retained. This tests a feature-value pilot; it does not test full-data retraining of the20-member native ensemble with32,421 feature rows.

Primary practical comparisons use the covered portions of the frozen own750 and briford529 cohorts (60 and54 molecules). All training rows for these fits come from their respective permitted training IDs. Larger-pool native OOF and held-out predictions are reused only from the corresponding outer-purged native training run. Corrections use native OOF predictions to learn residuals; outer predictions are never used for fitting. These two old cohorts overlap and are not independent confirmations.

A separate diagnostic uses two fixed repetitions of five-fold scaffold-group CV on all431 labeled molecules. Stratification uses the label-availability pattern, not activity values. Acyclic compounds are grouped by connectivity instead of one all-acyclic supergroup. Same folds, target masks and training molecules for every paired feature comparison. This diagnostic can guide selection but is not fresh challenge-test evidence.

Learners are fixed in committed code: ExtraTrees, LightGBM, molecular-similarity kernel ridge, and ridge on a frozen CheMeleon encoder. No label-dependent embedding fine-tuning. The first three compare structure-only, ADMETlab-only and combined inputs; CheMeleon compares encoder-only and encoder+ADMETlab. A predeclared LightGBM control drops CYP-specific ADMETlab columns to describe where signal comes from. Hyperparameters are fixed before scores; no outer-label optimization, calibration or ensemble weight fitting.

Imputation and scaling fit only the current target's training rows. Official labels and confidence bounds are not features. Missing experimental labels are unknown. Structural features are Morgan2048/radius2 and RDKit2D descriptors. CheMeleon checkpoint identity is pinned. ADMETlab's historical training membership is unknown, so the external teacher's label independence is not certified.

Report official ST-RAE, MAE, R2, Spearman and Kendall per CYP and macro. For paired ST-RAE/MAE changes, use1000 scaffold-cluster bootstrap samples, retaining both methods on the same resampled molecules and recomputing reference denominators. Intervals are conditional on saved predictions and exploratory (no selection adjustment). Repeated-CV predictions are averaged over the two seeds. Preserve all adverse cases and do not invent a hard improvement threshold.

Keep the full-native reference separate from the models trained only on431 or fewer molecules. No leaderboard submission is planned. Initial execution is local CPU only. All model fitting executes via the existing fixed ORX command bash run.sh from an immutable source snapshot.
