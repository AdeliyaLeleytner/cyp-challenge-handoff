# Provisional final-fit CPU executor

Node90b061ad-4fd1-4564-8f8f-eb57ab83688c is a child of evaluated CPU portfolio ea7f1cb9, source6b3ff84. Fixed command remains `bash run.sh`. Only the new child is edited. No real model fit, frozen-encoder inference, purchase, publication or submission was performed during preparation.

## Implemented

`night.final_feature_run` validates immutable full-feature and final-native manifests, constructs the official train/test feature matrices using original request IDs and graph checks, validates full official folds, checks rowwise native OOF reconstruction and published-placement parity, runs the exact inherited CPU recipes, performs raw training-OOF selection, locks the selection, then performs one selected recipe refit per CYP and exports the750 predictions. Missing CYP training labels are masked per endpoint. No external experimental labels train these feature models.

The inherited eight CPU representation recipes and their existing two-setting grids are the only supported definitions. The same `predict`, `blend_weight`, `place` and five-metric scorer functions are retained and SHA-pinned. Selection is native versus each recipe's selected standalone/global/per-CYP blend, minimizing raw full-training OOF macro ST-RAE, deterministic name tie-break. All five metrics and per-CYP counts are preserved. Full-training OOF estimates are selection estimates, not new independent validation.

Final serving is locked to `native_published_placement` by the parent's prior decision, copied verbatim in SERVING_LANE_DECISION.json. Published constants/function are pinned. Raw predictions are also retained. Poor local placed diagnostics must remain disclosed; no new constants are fit from hidden or leaderboard feedback. Native-parity failure, undefined placement, or final export validation failure blocks the selected export; no raw fallback occurs.

The final fitter cannot accept partial18460 acquisition merely because all official rows are available. It additionally requires an independent full-goal approval bound to all32421 terminal outcomes, zero pending, all5655 chemically eligible official rows, all input/audit/fold hashes, and completed approved native companion8421e31b. Explicit service failures and finite-but-chemically-excluded external vectors are retained as different categories; neither becomes fabricated model features.

## Feature folds already prepared without fitting

`../inputs/full-official-folds.json`, SHA256 `cc471dcf9b632e61d197a4d2a497b3932766b90b201e2946fe630981d8c9d680`, freezes five981-row validation folds using the exact evaluated scaffold-greedy seed42 assignment with normalized-parent and audited strict train-side exclusion. Training sizes are3922/3923/3924/3924/3923, with four total removed training-row occurrences. Original official/map/strict-pair input hashes are embedded. Native component folds differ; native OOF is joined by ID and is never described as sharing these feature folds.

## Remaining launch gates

- The shared outcome-core implementation is included by exact source hashes; pin the full32421 chemistry-approved snapshot. The adapter `validate_feature_snapshot(cfg)` is shared with the evaluation node, while this child separately enforces final-only completeness. Current inputs are intentionally null and training_enabled=false.
- Populate `finalfit_manifest.template.json`, `full_goal_approval.template.json`, and `native_fullfit_approval.template.json` from actual completed/audited files. Native run_complete must certify10 refits/10 verified reuses; all expected OOF/raw/placed/placement manifests must be hash-bound to that completion and independent native approval. Prepared placeholders are not accepted as real outcomes.
- Keep the eligible portfolio and the raw-OOF selection procedure locked. Commit the input hashes and training_enabled=true only after the parent's budget/runtime/input review. Actual execution is through ORX, not a background ad hoc command. `--preflight` checks gates without loading/fitting models.
- If TabPFN wins the separate comparison and is selected for final fitting, this CPU executor explicitly rejects it. Implement/launch the already pinned separate TabPFN runtime adapter in a reviewed child; never replace it silently with a CPU learner or run it in the native Torch2.6 environment.
- The node does not publish a report or submit. A later explicit publication/submission step must use the existing account, actual reachable HTTPS model_tag, correct cooldown, validated CSV hash and sanitized report. All needed output receipts are local.

## Resumption and evidence

Run identity includes exact config/input/source pins and package versions. A different runtime/input cannot resume the same output. Completed per-endpoint predictions are context-hashed, with atomic array writes and checksummed receipts. Selection is saved before blind prediction; a separate final-query-started receipt records actual execution without rewriting the selection lock. Existing completed output is immutable.

Fifteen synthetic tests exercise ID alignment, duplicate/SMILES errors, exact750 export plus official validator, missing-target masking, train/query leakage, locked selection/lane integrity, all-five-metric retention, full-goal completion versus early evaluation, explicit failure accounting, unsupported TabPFN, and parent overlap. Their predictor callback computes deterministic synthetic values and fits no model. The null-input preflight exits2 with fits_started0. The actual18460-outcome early-evaluation snapshot was additionally rejected by the final wrapper with “Final use requires all32421 terminal outcomes,” fits_started0. Real full-snapshot, native-parity and CPU final training are intentionally unexecuted.
