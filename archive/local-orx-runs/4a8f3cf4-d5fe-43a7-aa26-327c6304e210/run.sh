#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/4a8f3cf4-d5fe-43a7-aa26-327c6304e210' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/4a8f3cf4-d5fe-43a7-aa26-327c6304e210/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/cd94d1fd806ed6c1ff88a1058789af3866718d96bca8d74c798db3027cb3ea91.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
