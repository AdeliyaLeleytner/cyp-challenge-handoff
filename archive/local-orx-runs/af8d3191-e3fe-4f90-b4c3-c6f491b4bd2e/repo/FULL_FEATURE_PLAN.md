# Full ADMETlab feature portfolio — provisional preparation

Parent experiment `a737cb1d-a441-4a26-bb48-6a0e7616fb4d` established a reproducible conservative OOF-blend procedure on the500-row feature pilot. This child expands coverage and compares a small prespecified representation portfolio. It does not claim the pilot is a verified full-data champion. The project run command remains **`bash run.sh`**. Parent/frozen branches are untouched.

This implements H1–H3 from the goal's TASK.md/PLAN.md. The latest agreed acquisition scope is the complete32,421-request web_default pool. This evaluation trains new tabular models only on permissible official experimental labels, while reusing native full-pool predictions. No full refit or leaderboard submission is implemented here; those are subsequent, separately pinned steps. Expensive jointGNN+ADMET fusion remains a competing next hypothesis.

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

## Hard input gate

`full_feature_config.json` deliberately has null snapshot manifest and SHA256. Running `bash run.sh` or the no-fit `--preflight` currently stops with `input_contract_blocked`, before any model fit or embedding inference.

Before enabling a run:

1. Finish and chemically audit all32,421 exact request identities. Freeze immutable copies of raw122-column CSV, numeric120-feature CSV, queue, ID map, and supporting assets. Do not point a pinned manifest at a live growing collection.
2. Populate `full_snapshot_manifest.template.json` into a new draft with those immutable paths. Set collection_complete only after verifying exact coverage. Existing static hashes must not be silently refreshed.
3. Produce the independent chemical audit in the schema illustrated by `chemical_audit_contract.example.json`: approval, zero unresolved identity errors, full audited coverage, and hashes tying it to raw/numeric/queue/map/cohort inputs.
4. Resolve the native-reference exclusion review. New chemistry checks found neutralized-parent/tautomer and stereochemical aliases; the old narrower purge audit alone is not enough. `native_reference_outer_purges_approved` must be true only after review, with hashes of the exact native OOF/raw/placed assets approved. If a reference retraining is required, replace the static assets deliberately on this provisional child and document it; do not silently reuse contaminated predictions.
5. Run `tools/pin_full_snapshot.py --draft ... --output ... --config full_feature_config.json`. It validates the complete collection/audit before changing the config. Commit the child, then launch via ORX only.

The contract independently checks hashes, unique queue IDs, SHA256-to-exact-SMILES identity, exact32421-row raw/numeric coverage,120 endpoint columns, and provenance. Model preparation checks official4905/750 identity mapping and structures, confidence bounds, native prediction coverage, fixed folds, and train-only transforms. Nonfinite ADMET features stop the run rather than being silently fabricated; a justified missingness policy requires a separate declared change. Historical ADMETlab teacher training membership remains unknown.

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
