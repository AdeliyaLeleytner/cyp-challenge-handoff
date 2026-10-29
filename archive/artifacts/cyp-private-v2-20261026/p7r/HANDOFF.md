# Active P7R full comparison

Sole current launcher/supervisor: `/root/challenge_audit`. Do not launch a duplicate. All20 fits are already queued.

- Node `5b7e1c8f-ee3d-4eea-a971-2fb6adc561bd`; run `c95e19e7-e392-4a10-84c5-75d5af23f628`; source `8fad9cd`; worktree `p7r/full-worktree`.
- Instance `57857438`, machine149291,2×RTX4060Ti. Use only verified relay alias `cyp-private-p7r-57857438`. The direct path is unnecessary and was not used. All older owned leases are destroyed; unrelated55892464 must remain untouched.
- Immutable guard record `p7r/compute/lease-57857438.json`; guardPID76510; keepawakePID81744. Deadline2026-10-27T08:46:32UTC; worker margin15minutes. Actualrate$0.2138889/h.
- Budget proof `p7r/PROFILE_BUDGET_DECISION_v2.json`: maxepoch19.821s; full200×20 with2slots11.01h,10%timing contingency plus elapsed/fixed/recovery/bandwidth reserves=~$3.092<remaining$3.127. Hard13.6hcompute/disk+bandwidth bound=$3.109. No lower epoch ceiling/fewer folds/hidden hyperparameter changes.
- Scientific arms: zero/original/masked/repaired. Same31641rows,18targets+8boundcarriers, fixedP7 architecture/loss/stop rule. Only Vol/Dense intervention: raw85rows/170cells repaired;118other columns and transformed values remain identical. Root approved this narrow diagnostic, not a guaranteedtop10 gain.
- Remote `/workspace/p7r/full-results`. Read-only recoveryPID82469 copies completed jobs into `p7r/recovered/full-results`, logs `p7r/recovery-progress.jsonl`. MonitorPID2732 updates `p7r/current-progress.json` and generic STATUS workerstate fromactualremote logs; handles transientreaderrors withoutrelaunching. Profile recoveryPID83608 copies all4smoke checkpoints into `p7r/recovered/profile`.
- Currentgeneric STATUS fields explicitly describeP7R; oldgenericP3/P7 state is underhistory. Never infer currentjobs fromthehistorical20-complete records.

Finish without another routine approval if withinbound:
1. Monitor errors/deadline/budget. Preserve every completed model. No newfits beyondqueued20.
2. Onremoteparentcomplete, copy smallmetadata/predictions/logs and capture a SHA256/byte manifest of every remote output. Recover all20full checkpoints plus4profilecheckpoints; verify hashes beforeteardown. Do not assume rsyncexit alone provesdataidentity.
3. Fixed independentreadout (no fit/calibration):
`/Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python p7r/readout.py --results p7r/recovered/metric-snapshot --stage p7/stage --output p7r/readout --official /Users/adeliyaleleytner/autoresearch-runs/cyp-admet500-pilot-20261025/stage/official-train.csv --bootstrap 1000`
The p7stage table/foldmanifest are byte-identical toP7Rcommon inputs;readout expects `fold-manifest.json`. All5officialmetrics plusRMSE,bias,SD andPearsonextra; pairedcontrasts original−zero,masked−original,repaired−original,repaired−masked. Fixedseed20261026 scaffoldbootstrap withinfolds, descriptiveconditionalOOF uncertainty. No blindplacement orposthocmodelselection.
4. Ask model_audit for independent poolednumeric verification. Keep allper-CYP adversecases andone-seed/developmentdata limitations. Do not interpret3epochprofile asaccuracy evidence.
5. Mark `all_artifacts_hash_verified=true` onlyafterfullrecoveryproof. Destroy via tested `python3 p7r/compute/lease_control.py destroy --lease p7r/compute/lease-57857438.json --instance 57857438`. This issues `--yes` andfreshabsence readback. Never treat exit0orblankstdout alone asdestruction. Verify unrelatedIDs unchanged; capturetask-specific invoices andstop onlyowned guard/monitor/recovery/keepawake processes afteridentitycheck.
6. Update STATUS toinactivepaidresourceonlyafterverifieddeletion. Root owns broadergoal/heartbeat andfutureexperiments.

No publication, externalmessages, submission, newlease ornewmodel family is authorized here. P9 comparison is already complete onCPU anddoesnotrequire aGPUwindow.
