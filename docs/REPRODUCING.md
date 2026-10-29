# Restoring and Running on Another Machine

## 1. Inspect and verify preserved results

Python 3.10+ is sufficient for `tools/verify_handoff.py` and `tools/restore_assets.py`. GitHub CLI is needed to download the private release using an account with repository access. Verification performs no training, leaderboard queries, or paid compute.

```bash
python3 tools/verify_handoff.py
python3 tools/restore_assets.py --list
python3 tools/restore_assets.py --download
python3 tools/verify_handoff.py --all
```

Restoration checks each pack and object hash. Repeated runs skip files whose contents already match. Use `--prefix archive/artifacts/tdi-20261024/`, or another path prefix, to select a research direction. Each required pack is downloaded in full and removed from the download cache after restoration. Sizes are recorded in `manifest/summary.json`. Hard links reduce duplicate storage where supported; allow 12 GB of free space for the complete working package and temporary downloads.

## 2. Prepare a specific experimental tree

Each `worktree/`, `remote-orx/...`, and source snapshot belongs to a particular version. Keep separate environments for H6 CPU, ADME encoder GPU, P7/P7R/P10 Chemprop, and TDI workflows. Their requirement files, source hashes, configurations, and logs are stored alongside the relevant artifacts. Historical `/Users/...` and `/workspace/...` paths will not work unchanged on a new machine.

```bash
python3 tools/prepare_runtime.py \
  --source archive/artifacts/cyp-private-v2-20261026/p11 \
  --output .runtime/p11
```

This creates a separate runtime copy, rebases known local paths in UTF-8 files, and records the changes. Archived evidence remains unchanged. Remote GPU paths such as `/workspace/...` must be mapped to the corresponding recovered, staged, or output directory for that run, followed by asset-hash verification. Do not bypass manifest checks. Exact committed source trees are also available under `archive/git-snapshots/<commit>/`; the original host's full Git history and worktree pointers are not included.

## 3. Evaluate new candidates

Read the configuration and plan before executing `bash run.sh`: historical entry points may train models, rent compute, or submit predictions. Use a separate branch or directory for a new experiment, recording dataset, fold and source hashes, the exact baseline, budget, and expected outputs. Preserve previous results.

P11 includes `evaluate_future.py`, which requires compatible NumPy, pandas, and SciPy versions. After preparing the runtime, supply genuine outer-cohort predictions:

```bash
python3 .runtime/p11/evaluate_future.py \
  --own own750_predictions.csv \
  --briford briford529_predictions.csv \
  --blind blind750_predictions.csv \
  --provenance candidate_provenance.json \
  --output .runtime/candidate_sealed.json
```

Full-training predictions are not a substitute for genuine outer predictions. The script verifies identity but cannot establish training exclusion from a CSV alone; review the training provenance separately. It neither predicts a numerical leaderboard score nor submits anything.

Use the preserved, hash-identified CSV when the exact incumbent is required. Retraining the same recipe does not guarantee bitwise identity. Handoff verification covered saved artifacts and offline tools, not a fresh reproduction of the entire training campaign.
