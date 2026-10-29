# Active private P3 supervision

Sole launcher: child /root/challenge_audit. Do not launch a duplicate.

- Current P3 node: `ca918225-680e-4ede-9961-aa11f6507a0c`; run `5e13d499-82c9-4445-86ad-6814b90bf5ce`; source `562d9b6`; worktree `p3/full-worktree`.
- Host alias `cyp-private-p3-57807389`, task-owned Vast instance `57807389` (4×3090). Other instances must remain untouched. First failed bootstrap host57806735 was destroyed.
- Fixed ORX command `bash run.sh`. Never start raw SSH training. All20 P3 cell/fold jobs are already scheduled in the current run.
- Remote outputs `/workspace/p3/full-results`; immutable P7 outputs `/workspace/p7/full-results`.
- Local P3 incremental recovery `p3/recovered/full-results`, daemon PID in `p3/compute/p3-recovery-pid.json`, progress in `p3/recovery-progress.jsonl`. Interrupted rsync uses partial files and retries; do not confuse transfer failure with training failure.
- Guard details in `p3/compute/lease.json`, guard PID90798; deadline2026-10-26T18:44:28UTC. Worker deadline reserves15minutes. Own bounded caffeinate PID6896, no display assertion. Maximum7h lease compute+disk$4.905, first failed host~$0.08 plus small transfer charges; P3 subcap$6, campaigncap$10.
- `STATUS.json` is the heartbeat recovery entrypoint and is updated from actual worker logs.

P7 is complete and negative: ST-RAE0.674456 control vs0.702571 directADMET120 fusion; all five macro metrics worsen. Both arms/all10 full checkpoints are locally hash-verified against remote source: `p7/RECOVERY_CERTIFICATE.json` (72files,1,466,747,748bytes). Independent model-agent score verification passed. Do not retrain/promote fusion or introduce another feature architecture. Preserve both arms and adverse cases.

When P3 finishes:
1. Verify remote parent `complete.json` plus20 workercomplete files; recover all small prediction/metadata/log files without waiting for binary transfer if useful. All checkpoint originals stay immutable remotely.
2. Generate a remote SHA256/size manifest of all `/workspace/p3/full-results` files, save locally, and verify every local full checkpoint/result against it. P3 needs20 checkpoints. Do not destroy the lease before complete recovery.
3. Run the fixed independent readout (no model fitting/calibration):
   `/Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python p7/readout.py --results p3/recovered/metric-snapshot --stage p7/stage --output p3/readout --official /Users/adeliyaleleytner/autoresearch-runs/cyp-admet500-pilot-20261025/stage/official-train.csv --cells mae_uniform mae_ci interval_uniform interval_ci --bootstrap 1000`
   Use the actual recovered results directory if named differently. The repaired commonfold manifest is `p7/stage/fold-manifest.json`; P3’s older profile stage usesanotherfilename andmustnotbesubstituted.
4. Check all5official metrics, perCYP/macro pairedcontrasts and interaction intervals, matched initialparameter/BNstates, exactofficialIDs/bounds and sourcehashes. Bootstrap is fixedseed20261026,1,000 paired scaffold-group resamples withinfolds; conditionalOOF uncertainty, not new prospective confirmation. Pearson is extra. No blind-population placement or new stacking/modelselection fit.
5. Ask model_audit for independent pooled numerical confirmation (read-only), preserve allfourcellmodels and report every adverse case. Root decides later research direction; no additional family/search/publication is authorized here.
6. Recover receipts and actual lease billing, destroy only57807389, marklease/status destroyed, terminate only owned guard/recovery/keepawake processes after checking identities. Root owns campaigngoal/heartbeat status.

All reports/code/models remain private. No public writes, uploads, PRs, gists, leaderboard dispatch or messages to others.
