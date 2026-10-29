#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/57881623-7ebf-4816-b9c5-89e0805c0a9c' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/57881623-7ebf-4816-b9c5-89e0805c0a9c/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/0b7347b5762ee82180ef1e09dda8d4f5ad10d0fb29357c44c87581eeab57d35c.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
