#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/f77263cb-82ef-47ff-8ecd-0767aaf881dd' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/f77263cb-82ef-47ff-8ecd-0767aaf881dd/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/7fba48b1879b822acd067e7326ddd754a6916df48aa9e58b4dde6965c7feb7ae.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
