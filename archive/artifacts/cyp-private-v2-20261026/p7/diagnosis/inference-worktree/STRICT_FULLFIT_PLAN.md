# Corrected full native fit/OOF companion — preparation only

Parent3218eedb-29ef-4af5-8c82-c166279d0bf3 established the20-model full-native recipe atd4c1a31. Its verified serving-precision child38fe110 produced the submitted349165... CSV. This child preserves the parent data/model contract and ports that serving-precision implementation, then adds only train-side strict tautomer exclusions inside the original five folds. No outer rows are removed and no blinded challenge labels are loaded. Legitimate published Veith overlap with a blinded test structure is retained and disclosed.

Use the13 chemistry-audited stereo-preserving equivalence groups, excluding broader stereo-related analogs. Preserve source tables, target values, native hyperparameters/task weights, validation IDs/order and original fold IDs. Remove a training row only if its certified strict group intersects that fold's validation group; record every removed row and endpoints. Refit union18 and2d6isoform6 when affected. Reuse mtaux8 and2d6single only after exact unchanged data/spec/fold/source/package/checkpoint/OOF/query proofs.

Prepare a new immutable staging manifest, verify deterministic replay and mathematical full-source native aggregation provenance, and leave the node unrun. Parent decides timing and budget. The fixed project command remainsbashrun.sh; all actual training must be a later ORX run of committed code/config. This is not a new leaderboard submission or a claim of improved score.

## Prepared inputs and read-only checks

The immutable stage is87files/208,336,685bytes, manifest SHA256`5ca02769cea1f2471c16d903dd87120af3b10da24eb30e73e69d9b38f07c85f4`. Independent replay into a temporary directory reproduced the same manifest hash. No fits or model inference occurred.

Full rows are unchanged: union1831,670; mtaux84,905;2d6isoform623,264; single1,493. The strict policy removes32 fold-training row occurrences (union1812;2d6isoform620), with no outer removals and no validation reassignment. Reuse checks passed for10 mtaux8/single folds; those members have0 inner removals. The exact VEITH alias of blindedOCNT-0496981 remains in both relevant component pools with public auxiliary values and missing hidden challenge primary values.

Historical serving arithmetic is explicitly checked against `remote/finalized/`: reconstructed raw vectors have maximum absolute difference0 for every CYP, and the historical placed CSV hashes to349165... . The older3cc5... artifact is not used as the submitted reference.

`strict_fullfit_config.json` deliberately has `training_enabled=false`. It targets an8GPU runtime only as a prepared plan; no device is reserved. A parent must approve the budget/timing, enable this flag on the still-provisional node, and commit before `orx exp run`. `--preflight-only --stage /local/stage` is a read-only check, not an experiment run. Stage/outputs use separate `/workspace/cyp-strict-fullfit/` paths so a sequential run can share an existing lease without touching the corrected outer node.

The runner schedules only10 affected folds through the native worker. It preserves historical reused job.json and complete hashes, then calls the verified native collector on corrected specs. Outputs include per-component OOF/test vectors, `native_official_training_OOF.csv` for all4905 official IDs, raw and placed750-row blind prediction files, and source/data/reuse manifests. No upload occurs and no blind truth is available or scored.

## Timing and cost sizing

The original full fit used20 models on4GPUs and took28m12s. Metadata sum:1.73825GPU-hours for all20; the10 affected union/specialist fits account for1.50465GPU-hours, with longest individual fit893.24seconds. On8 comparable GPUs, five union jobs plus three specialist jobs can start immediately; the last two specialists fit in the second wave. Historical durations suggest about15minutes of idealized scheduling before staging/collection/recovery overhead. Allow roughly20–25minutes overall on comparable hardware, with a25–30minute lease margin; this is not an upper bound because changed training/early stopping and host contention can increase runtime. Do not start close to a hard provider teardown deadline.

At the historical full-fit lease rate$1.19556/hour, the original20-model run represented about$0.56 compute wall cost. Reusing an existing8GPU lease can avoid another setup charge and suggests a sub-$1 incremental compute segment if comparable timing holds; the parent must use the actual active lease price and remaining cap. No new spending is authorized by this estimate.
