# Prepared corrected native reference — zero fits launched

- ORX child: `31f8a64a-174d-4f92-95e8-2ada73c2176d`
- Parent: `1346e303-7733-44ce-b2d8-ffe26eab8a61`, completed native two-holdout reference
- Branch: `orx/native-reference-with-strict-tautomer-purges`
- Commit: `c7d9be7a5afa2162be9b97b56cdd64b5929af2d7`
- Run command: **bash run.sh**, inherited unchanged
- Status: **prepared, committed, never run**; no rented compute or model fitting

The child removes exactly12 approved outer-training component rows and62 strict train-side equivalence counterparts across the existing inner folds. The broader4analog rows are retained. All original outer query/truth files and surviving validation memberships/order are preserved, as are the native hyperparameters and primary task weights. No scaffold folds were regenerated.

| Cohort/component | Rows before | Rows after | Outer removals | Inner train exclusions across5folds |
|---|---:|---:|---:|---:|
| briford529/2d6isoform6 | 22833 | 22830 | 3 | 16 |
| briford529/2d6single | 1317 | 1317 | 0 | 0 |
| briford529/mtaux8 | 4375 | 4375 | 0 | 0 |
| briford529/union18 | 31140 | 31137 | 3 | 18 |
| own750/2d6isoform6 | 22746 | 22744 | 2 | 14 |
| own750/2d6single | 1343 | 1343 | 0 | 0 |
| own750/mtaux8 | 4155 | 4155 | 0 | 0 |
| own750/union18 | 30920 | 30916 | 4 | 14 |

Only union18 and2d6isoform6 are retrained:20fits. The20mtaux8/2d6single folds are reused only after the unchanged data/spec/fold, original outer ID/parent/InChI purge, checkpoint, metadata, prediction and native-source checks. Reused job.json files stay unchanged; the new orchestration wrapper avoids the native.run behaviour that would otherwise rewrite them. The actual native worker, vendor algorithms and native ensemble collector are unmodified.

The full staging preparation was independently replayed into a temporary directory. Its162-file asset manifest matched byte-for-byte. Local preflight confirmed zero strict-equivalence overlap across corrected outer/inner boundaries, exact reused OOF/query ID correspondence, and all payload/checkpoint hashes. Historical cached raw/placed ST-RAE values reproduce exactly with the reporting scorer (absolute error0). These are preparation/scorer checks, **not new corrected model results**.

## Assets and execution

Stage: `/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026/chemistry-audit/corrected-native-reference/stage`. Size: 395,285,378bytes. Asset-manifest SHA256: `66ba9896250b0b169bd8af32e3c3222991cdda236733649edaf26deb7d8f7f24`.

The parent must stage those assets unchanged at `/workspace/cyp-strict-reference/stage` and select live compute within its remaining budget. Config currently exposes8GPUs; an operational GPU-list adjustment must be committed before launching the provisional node. The setup requires historical torch2.6.0+cu124 plus the pinned dependency versions and fails instead of silently changing runtime or falling back to CPU. CUDA/runtime execution has not been tested here.

See [worktree/RUN_PLAN.md](worktree/RUN_PLAN.md) for the exact ORX launch template, resource caveats, recovery and teardown. Historical affected-fit cost is about4.87GPU-hours; that is not a current provider quote. No run has been queued.

## Auditable outputs

- [preparation-summary.json](preparation-summary.json)
- [stage/purge-and-reuse-manifest.json](stage/purge-and-reuse-manifest.json): complete removed rows, revised indices, per-fold certificates and reuse provenance
- [outer-removed-rows.csv](outer-removed-rows.csv)
- [inner-train-exclusions.csv](inner-train-exclusions.csv)
- [fold-membership-summary.csv](fold-membership-summary.csv)
- [stage/corrected/](stage/corrected/): frozen corrected data/spec/fold files
- [stage/asset-manifest.json](stage/asset-manifest.json)
- [deterministic-replay.json](deterministic-replay.json)
- [preflight.log](preflight.log)
- [historical-scorer-preflight.json](historical-scorer-preflight.json)

The source audit's171incomplete tautomer enumerations and broader stereochemical relations remain explicitly outside the13approved strict-equivalence edges. No structure was silently merged or standardized for training. Historical metrics and source artifacts remain untouched.
