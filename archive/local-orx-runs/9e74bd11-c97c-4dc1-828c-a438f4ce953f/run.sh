#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/9e74bd11-c97c-4dc1-828c-a438f4ce953f' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/9e74bd11-c97c-4dc1-828c-a438f4ce953f/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/5dccba231c5230991cb00aa8d62d9004da0282aa0a135b16cc3b0d2a120db177.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
