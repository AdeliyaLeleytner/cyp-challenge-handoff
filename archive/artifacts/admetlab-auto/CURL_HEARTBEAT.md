# Authorized isolated curl trial and conditional continuation

This supersedes the Chrome submission instructions in HEARTBEAT.md. User asked: try the next pending batch through curl after its saved cooldown, without concurrent Chrome submissions; if successful, use curl for the remaining batches.

Folder: `/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/admetlab-auto`.
Output: `/Users/adeliyaleleytner/Downloads/ADMETlab-Chrome-direct-500`.
Automation ID: `finish-admetlab-batches`.

Run `/usr/bin/python3 <folder>/curl_queue.py --status` first. The initial trial is batch4. No Chrome automation or manual page interaction is needed for this workflow. Do not launch collect.py, chrome_routed.py, run.sh, or any browser-submit helper. Do not rotate IPs/proxies, change User-Agent, weaken TLS validation, or bypass the stored cooldown. Direct curl uses the same text form method2, a fresh form CSRF token and its own cookie jar, with sockets bound to Wi-Fi en0. Data remains the web_default endpoint set.

When `next_allowed_at` is still in the future, end quietly without website requests. When due, execute `/usr/bin/python3 <folder>/curl_queue.py` once. The runner holds the shared collector lock throughout the network operation, preventing concurrent workers, and processes at most one batch. If a live worker already holds the lock, leave it running rather than starting another or clearing the lock. If exec returns a session ID, keep checking that session in bounded waits; do not launch the command again. Calculations can take over a minute. Do not abandon a running process or assume a timeout in the tool interface is an HTTP failure.

The first curl trial must validate exact raw_smiles and required endpoint columns. If it succeeds, the runner sets `curl-control.json` to curl_only, saves the result, and merges both raw and numeric features including original500. Report this meaningful transport change once, then continue future batches on later wakes. Keep the ten-minute post-download cooldown and increasing waits for HTTP429. Longer Retry-After takes precedence. The runner never repeats an uncertain POST.

If the first curl trial fails (control mode trial_failed), pause this heartbeat and notify the user with the actual response and elapsed cooldown. Do not resume Chrome or try another transport automatically. If a later curl_only batch gets429, the runner schedules a longer wait (20,40,80,160,320 minutes, then a six-hour cap) and can retry after that deadline; stay quiet during unchanged waits. If mode/status is needs_attention, inspect saved logs read-only, preserve state, pause if necessary, and report the actionable issue. Never reset uncertain/submitting to pending merely to retry.

Saved result URLs allow download recovery without another submission. All raw headers/bodies are local evidence. Do not print cookies or CSRF values in chat. Current source mode must remain web_default. Use `scheduled_queue.py merge` to rebuild local combined files if necessary, without network requests.

Outputs:
- `results/all-collected.csv`: original500 plus every validated queue batch.
- `results/all-collected-features.csv`: numeric feature matrix.
- `results/all-collected-manifest.json`: provenance, hashes, coverage.
- `last-curl-outcome.json`, `curl-control.json`, and `schedule.json`: durable state.

Completion requires5655 unique official molecules,120 endpoint columns,0remaining, and all11 queue batches complete. Then pause automation ID finish-admetlab-batches via automation_update, preserving its other fields, and report final file links. Stop only the recorded task-owned caffeinate PID after verifying its command. Never claim acquisition complete based only on a scheduled job. Keep quiet when simply waiting; notify on trial outcome, completion, or a blocker requiring user action.
