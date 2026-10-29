# Independent Claude consultation

Round: 1

## User request
"а как получилось, что ты воспроизвел полностью briford, а мы все равно оказались сильно ниже в лидерборде? и сколько примерно считался наш сабмишен на лидерборд?"

Prior constraints: user authorized overnight experiments and one conditional challenge submission, already completed. Current request is explanation and factual timing, no new training/submission needed.

## Authoritative context and constraints
2026-10-24, Europe/Moscow. Scoped campaign root. User requires independent Claude advice for substantive diagnosis. Read-only, no secrets, no contact or compute launches. Codex owns conclusions. Keep response tightly scoped.

## Current state
We rebuilt four model families from public briford sources and selected a train-OOF positive affine stack. Live submission result .7521204949751441 versus published briford .4377997714479094. Macro Spearman ours .7563919429600394, briford .7515780014272241. Macro MAE ours .9284270399024772, briford .6331430020143404. There is no official scored submission of our unmodified reconstructed reference.

## Evidence and source map
- reference_audit/reference_recipe.json: matching architecture/defaults, plus explicit warning historical leaderboard calibration uses board-derived placement; local control instead uses training-only calibration.
- reference_audit/sources/8c72c7559471febaf0962fd551b4eaab8db3a136/docs/blogs/cyp_challenge.md lines39-65: author's placement/scaling correction; ST-RAE placement selected against leaderboard. Original source https://github.com/SuperCowPowers/workbench/blob/8c72c7559471febaf0962fd551b4eaab8db3a136/docs/blogs/cyp_challenge.md .
- Same source subtree ml_pipelines/OpenADMET/cyp/scripts/cyp_recalibrate.py: board moment constants and place() implementation; no need to fit/apply it.
- remote/results/FINAL_reference_seed42/union18/seed42/fold0/trial_metadata.json component.deviations: our official-only fold assignments with public rows in every fit vs author CV over merged union; recomputed task weights per fit; newer pinned data; normalized-parent exclusions for all official TRAIN/TEST. Source precision16-mixed and scratch init. Original historical checkpoints/OOF unavailable in our inspected sources.
- submission_package_v1/test_vector_comparison.json: our final stack vs reconstructed reference (not original briford) has per-target mean shifts max.0163,SD ratios.9934–1.0274,max individual difference.1387. This is only descriptive, not an official score control.
- gate_bundle_v1/certificate.json: averaged-vector local reference/candidate own750 .6042028704/.6023806342, briford529 .6289306012/.6267819269. Holds are reused, overlap143IDs; bootstrap intervals include zero. They are TRAIN subsets, not actual blinded TEST.
- official_results/20261024T084528Z/leaderboard.csv: latest fetched live metrics above.
- submission-ledger/attempts/f0e32b5fecab41d9a68c098e0ebe4b0d05cbc61760eb3dbd63c300382945e053/receipt.json: accepted at2026-10-24T00:10:09.925094Z; response says should appear within2hours, not actual completion time.
- official_results/20261024T001326Z/result.json: absent at00:13:26.642696Z.
- official_results/20261024T083317Z/result.json: first observed present at08:33:17.949612Z. No checks between these snapshots. Submitted column00:10UTC is submission time, not score completion. Moscow is UTC+3.

## Work already performed
Re-read source recipe, actual training metadata/deviations, original author's public explanation and all timestamped leaderboard checks. No controlled ablation of reproduction discrepancies and no fresh inference/training. Earlier advisor on pre-send gate noted calibration/selection caveats but actual public score was not yet available.

## Questions for independent assessment
1. What can be explained confidently about the reproduction discrepancy, and which causal interpretations remain hypotheses?
2. What timing statement is warranted by the sparse checks, and what should be corrected in how the earlier campaign was described?

## Known missing or inaccessible information
Original historical checkpoints and exact historical data/predictions, our reconstructed reference's official score, per-factor counterfactual results, backend scoring start/end timestamps. Do not infer any of these.

## Codex position
withheld for independent first-round assessment.

## Confidentiality check
Only project evidence and public sources; no secrets, credentials, private keys, .env contents or unrelated personal data.
