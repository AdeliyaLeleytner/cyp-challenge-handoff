# Monitor the active full-pool ADMETlab acquisition

Current goal scope is all32421 unique requested molecules, including official5655 and26766 external molecules. Acquisition is only one stage of the active goal; chemical audit, model comparison and an authorized leaderboard submission still follow. Read the root goal PLAN/GOAL_STATUS for goal coordination.

## Live state and ownership

Read `/Users/adeliyaleleytner/Downloads/ADMETlab-Chrome-direct-500/continuous-state.json`, `worker-settings.json`, `results/all-collected-manifest.json`, and the active batch's saved state/events. Check the recorded PID and command. A running flag alone is insufficient. The worker holds the main collector lock; do not start a duplicate collector or use another Collector-based status CLI while it runs. Native-model/GPU work is separate and must not be altered by this monitor.

Acquisition supervision is delegated to the challenge_audit agent. Parent coordinates the overall goal and snapshots reviewed collector changes. Do not restore an older source file or batch-size rule merely because a previous note mentioned it.

## Current policy

Stay at100-molecule batches (`auto_increase=false`). Do not restore200 based on recovery of the older400-molecule set: a later external200 batch lost three uploaded responses, and its two100-molecule halves subsequently succeeded. This is reliability evidence, not proof of a fixed service-size limit or chemical invalidity.

Use onlyweb_default120; no API substitution. Preserve exact input SMILES and request hashes. Shifter curl uses user-authorized fresh sessions, serial requests and at least4seconds between HTTP starts. AcceptedCSV retrieval uses directWi-Fi; do not recompute an accepted job because downloading failed. Honor actualRetryAfter and keep credentials private.

The existing unknown-response policy allows at most two explicit, provenance-preserving reissues of a cache-missing batch when a POST uploaded but its response was lost. Original outcomes remain unknown and repeated server computation is possible. After this cap, `split_unknown_batch` may archive a still-unknown200/100 set and reduce subsequent cache-missing sets to100/50. It never applies to known resultURLs, explicit429s or pre-origin failures, and never splits below50 automatically. The original input and HTTP evidence remain in place, with an uncertain-submissions registry entry. Do not call these archived jobs rejected or not submitted.

No saved molecule is relabeled: the remaining index is rebuilt from all validated caches before each new batch. Historical unknown-job inputs may be covered by later authorized reissues; cached label coverage and original server execution are separate facts.

## Completion and failure

Use manifest `rows`, `pool_size`, and `remaining_total`. `remaining_official` refers only to5655 and the old fixed5155 queue state is archival. Completion requires32421 unique rows,0remaining,120 endpoint columns, matching hashes and a final chemical/output audit. Actual unsupported/partial service outputs must be preserved and reviewed; never fabricate numericzeros or silently discard failures.

Stay quiet while progress is normal. On a concrete blocker, preserve the active result/state and notify goal coordination. A known resultURL permits GET-only recovery. An unreviewed unknown POST must not be blindly reset or repeated. `invalid_result` requires inspecting the saved CSV and identity/schema evidence; preserve supported rows only with explicit, auditable partial-result handling.

For a clean six-hour/1000POST budget stop, confirm the worker has exited and inspect the active folder. Recover any accepted result first. A pending/rejected batch with no unknown execution may resume under current settings. An `unknown_archived_for_split` disposition is already explicitly authorized and preserved; it does not mean the original job was known not to run. Do not restart a needs_attention run without resolving its concrete cause.

If all32421 labels are verified, pause acquisition heartbeat `finish-admetlab-batches` and hand the immutable snapshot to the active goal's chemical/model stages; do not mark the overall goal complete. On final acquisition completion/blocker, stop only recorded task-owned caffeinate processes after checking their commands. No emails, newGPU rentals, training or leaderboard submissions are authorized by this monitor alone.
