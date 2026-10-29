#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/af8d3191-e3fe-4f90-b4c3-c6f491b4bd2e' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/af8d3191-e3fe-4f90-b4c3-c6f491b4bd2e/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/a38d44026bc760e846ed9dd55be4f384d37b1be6e73f1946aa2961310f33c715.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
