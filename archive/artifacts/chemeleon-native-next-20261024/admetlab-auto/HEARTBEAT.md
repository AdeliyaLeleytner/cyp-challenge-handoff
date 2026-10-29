# Continue the authorized ADMETlab collection

User explicitly authorized finishing the remaining official batches with a ten-minute cooldown and longer waits/retries after HTTP429. Use ordinary user Chrome and genuine browser input clicks. No curl POST, injected JavaScript click/submit, new identities, parallel submissions, API feature=true, or VPN changes.

## Persistent files and commands

Source folder: `/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/admetlab-auto`.
Run with `/usr/bin/python3` and the absolute path to `scheduled_queue.py`.
Output folder: `/Users/adeliyaleleytner/Downloads/ADMETlab-Chrome-direct-500`.
Heartbeat ID: `finish-admetlab-batches`.

Start with `scheduled_queue.py status`. It reports the first incomplete batch, file path, count, state, and the next allowed time. If not yet due, make NO website requests and finish quietly. Do not sleep through the cooldown in an active turn. The heartbeat will wake again. Use persisted times, not a guessed ten-minute interval. Base wait is 600 seconds after adoption/download; consecutive429 waits are 20,40,80,160,320 minutes then six hours. Longer Retry-After overrides these waits.

The queue contains 5155 molecules and excludes the original500. Batches1–3 are complete (1500 queue rows); original500 is preserved as `original-500.csv`. Therefore total initially2000; eight remaining batches4–11 contain3655 molecules. Do not repeat completed batches. Last batch has155 rows.

## Browser interaction

Use `mcp__cua_repl` and its documented APIs. Read its documentation when necessary after compaction. The working Chrome browser ID is3, tab185442435 in window185442180. Resolve against current inventory if stale. This is the real user Chrome profile. Prefer reusing that tab; preserve unrelated tabs. Mark the collection tab as a handoff while work remains. Do not use old REPL helpers `prepareBatch`, `clickPrepared`, `finishBatch`, or `checkpoint`: they use the older timing-free helper. Use `scheduled_queue.py` below instead.

Before any due website access, run `scheduled_queue.py check-route`. It must confirm all ADMETlab resolved IPs route through Wi-Fi en0 and the default route uses utun VPN. If not, stop and notify the user; do not disable the VPN.

If a batch is already `submitting` or `uncertain`, NEVER send another POST. Inspect the controlled tab for its result/429/loading state. If the tab is lost without a result URL, notify the user; do not guess. If a `result_url` is saved, resume only that result/download after the saved cooldown; do not resubmit molecules.

For a due pending/rate_limited batch:
1. Navigate to https://admetlab3.scbdd.com/server/screening, inspect current DOM, select `Enter a list of SMILES`.
2. Read that batch's saved `smiles.txt` locally. Fill the visible textbox via the browser locator API. Read its value back and verify exact character-for-character equality and expected row count. Preserve stereochemistry, backslashes, salts, charges, and order. Save the verified input hash and preparation timestamp in the batch folder. No JavaScript submit-handler injection.
3. Leave at least35 seconds after preparation before clicking, in addition to the already enforced inter-batch cooldown. Bounded clock waits are fine for this short delay.
4. Immediately before clicking, run `scheduled_queue.py begin --batch N`. It checks the cooldown, route, and state; refuses uncertain/duplicate POSTs; saves the attempt. Click the visible Submit with `tab.playwright.getByRole('button',{name:'Submit',exact:true}).click(...)` or native browser input. Never use DOM `.click()` or `form.submit()` evaluation.
5. Navigation may take60–90 seconds. Browser inspection commands can time out during navigation; that does NOT mean submission failed. Do not click again. Inspect boundedly until a result URL or actual error is visible. If still running at the end of a turn, preserve the tab and state for recovery.

HTTP429: save response evidence and run `scheduled_queue.py reject --batch N`, adding `--retry-after VALUE` if an actual header is available. This persists the longer cooldown. End this wake without further site requests. Do not infer Retry-After from a generic error page. For other unexpected errors, preserve state and report if user action is required; no blind repeated POST.

Success: the result page must show the expected successes and no invalid molecules. Save its URL immediately with `scheduled_queue.py result --batch N --url URL`. Download CSV via the observed Download as CSV link in Chrome. A download event once returned a stale earlier file path, so never trust that path alone. The authoritative identity check is the script below. If an event points to the wrong file, inspect only matching result-task filenames in Downloads (observed naming is ADMETLab3_<result-task-id>.csv) and validate that candidate. Do not adopt an unrelated download or re-submit the batch to repair a download issue.

Run `scheduled_queue.py adopt --batch N --csv /absolute/download.csv --url URL`.
It checks all returned raw_smiles and required endpoints, saves the batch, updates the ten-minute cooldown, and merges all acquired data including original500. Only successful validation marks a batch complete. If a saved CSV genuinely mismatches, stop for investigation rather than dropping rows silently. Process at most one submission per wake.

## Outputs and finish

`results/admetlab_merged.csv` and `results/features.csv` cover the5155 queue.
`results/all-collected.csv` and `results/all-collected-features.csv` include original500 and all completed queue batches. These are the user-facing whole collection.
`results/all-collected-manifest.json` records hashes, schema and coverage.
Use `scheduled_queue.py merge` to rebuild these without network access if needed.

When status is complete, verify the combined manifest reports5655 unique rows,0 remaining,120 endpoint columns, and all11 queue batches are complete. Disable this heartbeat with automation_update (view existing fields, then update status PAUSED preserving the rest). Report the final raw and numeric file links. Stop the recorded task-owned caffeinate process if it is still running, after verifying its PID/command; do not stop unrelated processes.

Stay quiet during unchanged cooldowns. Notify on completion, a blocker needing user action, or a meaningful change in acquisition behaviour. Do not present scheduled work as already collected. No training or challenge submission is part of this acquisition task.
