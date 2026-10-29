# Full ADMETlab feature portfolio — provisional preparation

Parent experiment `a737cb1d-a441-4a26-bb48-6a0e7616fb4d` established a reproducible conservative OOF-blend procedure on the500-row feature pilot. This child expands coverage and compares a small prespecified representation portfolio. It does not claim the pilot is a verified full-data champion. The project run command remains **`bash run.sh`**. Parent/frozen branches are untouched.

This implements H1–H3 from the goal's TASK.md/PLAN.md. The final acquisition goal remains all32,421 terminal web_default outcomes. The parent explicitly approved this early evaluation on a frozen18,460-outcome snapshot because all5,655 official inputs are present, chemically reviewed and finite. It trains new tabular models only on official experimental labels and uses the corrected native expert conditionally under the reviewed legacy-source policy. It does not approve fresh external supervision or claim the full acquisition is complete. No full refit or leaderboard submission is implemented here; those are subsequent, separately pinned steps. Expensive jointGNN+ADMET fusion remains a competing next hypothesis.

## Fixed initial portfolio

Eight representation/model variants, each with two prespecified inner-OOF settings:

- LightGBM on ECFP2048+RDKit2D, on ADMET120 alone, and on their concatenation; plus the prespecified13CYP-only and107non-CYP teacher-feature groups. Those two feature-group arms use exactly the same inner settings/folds asall120. Grid: leaves/depth7/3 versus15/4; other pilot settings unchanged.
- Kernel ridge on ADMET120, alpha1 versus10.
- Frozen CheMeleon2048+Ridge, without/with ADMET120, alpha1 versus10. Blocks are standardized on training rows and normalized by their feature dimension before concatenation.

These give paired no-ADMET controls for the structure and frozen-encoder augmentations, plus the native reference and teacher-only comparisons. Frozen embeddings are inferred in a separate Python process from LightGBM, retaining the prior OpenMP-crash repair. They are not fine-tuned.

For every selected variant, compute both a one-scalar native blend and a per-CYP static blend. The latter is the capacity control needed before introducing a future molecule-dependent gate; no such gate is implemented in this child. Blend weights minimize exact training-OOF macro ST-RAE under convex constraints. The optimizer uses a weighted median of interval endpoints; synthetic tests check equality against the previous exhaustive-breakpoint method.

## Selection and evaluation boundary

Use the exact frozen own750 and reconstructed-briford529 IDs and stored inner-fold IDs. Reject parent/connectivity leakage; do not silently rebuild splits. **briford529 is a reconstruction**, not certified original author-persisted IDs. The two outer cohorts overlap143 molecules and have both already influenced prior development.

Hyperparameters, blend coefficients and the reported candidate choice are selected **independently within each outer-training pool**, using only its innerOOF predictions. Do not pool inner scores from both cohorts and then claim both outer cohorts remained untouched: each training pool contains some of the other holdout's rows. Save each cohort's selected family and parameters, including when selections differ.

Outer evaluation reports all five official metrics, macro and per CYP: ST-RAE↓, MAE↓, R²↑, Spearman↑, Kendall↑. Paired scaffold bootstrap reports macro uncertainty for every metric against native, conditional on the saved predictions. These are development diagnostics, not new independent confirmation tests.

Raw predictions are the selection lane. The unchanged published native placement is computed and reported in a separately named **diagnostic** lane, using trainingOOF correlation and query prediction moments only. Its public leaderboard-derived constants are explicit. The no-fit parity check reproduces the saved native placed vectors to floating-point precision; this does not approve the use of placement for a final submission or certify clean native training.

A final full-data fit must use the same prespecified inner selection procedure on all eligible official training rows, and must be implemented/pinned separately. No code here selects a final submission from outer scores or sends any upload.

## Scoped input gate and complete final-goal boundary

This provisional evaluation is pinned to `../official-snapshot-18460/manifest.json`, SHA256 `1ab25642a8ea19fc0663687dfdaba383498e5a099b00e9dcc6a24c82e342c9bd`. Model-input scope is all4905 official training+750 blinded structures; acquisition-goal scope is32421, with18460 outcomes in this snapshot and13961 still pending. That is a deliberate dependency optimization, not a reduced final goal.

`night/admet_outcome_contract.validate_feature_snapshot(cfg, require_full_acquisition=True)` is the shared, stage-neutral core. Its default requires complete32421 terminal outcomes and the full-output-v2 audit/ledgers. Only this evaluation wrapper explicitly passesFalse and requires `stage=evaluate` plus the independent official5655 certificate/membership and exact raw/numeric/queue/map hashes. The default final-fit gate rejects this snapshot. Source v1 is preserved separately.

The exact120 declared endpoint columns are model features. The120 `::category=Invalid%20Molecule` columns are retained status diagnostics, never predictors. They can occur only with the exact reviewed raw rejection row/hash and matching endpoint literals. Rejected base values stay blank; no imputation/fabricated labels. Any other unexpected endpoint, derived column, rejection or nonfinite numeric endpoint fails validation. The numeric-but-invalid Sb service graph remains explicitly excluded by its reviewed identity manifest. Neither exception affects any official row; missing or excluded official inputs stop the evaluator.

The corrected native reference is bound to certificate31f8a64a, its staged purge manifest and exact raw/placed/componentOOF hashes. Reuse is conditional on the legacy expert policy in DISPOSITION.json, not a blanket original-source chemical-purity approval. The source28 quarantine and feature-output exclusions remain separate policies for future fresh full-pool fits.

Future final refitting/submission still requires the complete32,421 outcome audit, reviewed failure/eligibility manifests and the correct full-fit native companion; the independent final executor owns that contract. No outer cohort's scores are reused as final-training OOF. No full refit or submission is implemented by this evaluator.

## Entry points and outputs

- `night/admet_full_contract.py`: standard-library snapshot gate.
- `night/admet_full.py`: preparation, inner selection, outer diagnostics and artifacts.
- `night/admet_full_models.py`: fixed learners; transforms fit within each training partition.
- `night/admet_full_math.py`: scalar/per-CYP blend optimization and diagnostic placement.
- `night/preflight_full_features.py`: read-only parity check of existing native vectors; no model fits or embedding inference.
- `tests/test_full_feature_preflight.py`: synthetic math/input-gate checks; no real model fits.

Outputs include raw/placed predictions, all candidate trainingOOF predictions, inner-selection.json, cohort-specific-selection.json, all-metrics.csv, per-cyp-metrics.csv, paired-bootstrap.csv, full input/config identity, and a completion record explicitly stating no full refit/submission.

Optional GPU budget remains unused. This child is intended for the local CPU baseline tranche. The full-pool GNN fusion hypothesis needs its own node and a resource estimate before using the≤5USD GPU tranche.

The CYP-only/non-CYP arms are predeclared regularization alternatives and mechanism controls motivated by the chemistry review and prior pilot, not feature subsets chosen after seeing new outer errors. Both remain eligible for inner-OOF selection under the same procedure. The columns are selected by their fixed endpoint names and their counts are asserted13/107; all120raw features remain in the input snapshot and primary arm.
