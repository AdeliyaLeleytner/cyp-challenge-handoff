LATEST USER CHANGE: use a fresh Shifter session ID for every HTTP request. ShifterDirect now defaults to rotate_per_request=True. The normal50/100 automation remains paused after the rotating50 trial returned HTTP429. Do not resume or silently revert to sticky sessions. See probes/shifter-rotating-50-20261025/RESULT.json.

# Shifter transport tests authorized by the user

This replaces the prior direct-curl and Chrome instructions for this automation. The user supplied Shifter credentials and requested curl requests through that proxy, after requesting50 molecules then100 if50 succeeds. Run only those bounded tests for now. Main collection remains paused.

Run `/usr/bin/python3 /Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/admetlab-auto/shifter_probe_queue.py` once per wake. It reads `/Users/adeliyaleleytner/Downloads/ADMETlab-Chrome-direct-500/shifter-tests.json`. Before its next_allowed_at, it returns waiting without any website requests. End quietly in that case.

The runner holds the main collector lock, uses only still-unlabeled molecules, and uses curl via Shifter on local Wi-Fi en0. Default VPN routing stays unchanged. Credentials reside in a private0600 file outside project artifacts; never print, copy into prompts, or log them. It uses one sticky session for the form, POST, result and CSV sequence. Do not rotate sessions after a429, create parallel workers, weaken TLS checks, change user agents, or add proxy retries.

First run:50 molecules. Only after validated success does the next stage become100 molecules, with a ten-minute cooldown after the first completed download. Every successful result is saved and merged into `results/all-collected.csv`, `all-collected-features.csv`, and the manifest. Exact raw_smiles and endpoint schema are checked before completion. No already-labeled molecules are selected.

If exec returns a live session, wait on it in bounded calls rather than invoking another worker. A calculation may take over a minute. Never repeat an uncertain POST. A recorded result URL permits download recovery only. If a process returns an error/status needs_attention, inspect local evidence and notify the user; pause this automation instead of automatically switching transport or identity.

A connectivity test through Shifter on Wi-Fi succeeded HTTP200. A subsequent same-session check returned504; reliability is not established. Earlier attempts through the VPN failed. Keep this distinction; do not claim proxy reliability or that it fixes ADMETlab until actual predictions succeed.

After both50 and100 succeed, or after a failed test requiring attention, pause automation ID finish-admetlab-batches with automation_update, preserving other fields. Report counts, actual HTTP outcomes, and the final merged file links. Do not send email or submit challenge predictions. No Chrome interactions are needed. Do not restore prior Chrome/direct-curl automation automatically.
