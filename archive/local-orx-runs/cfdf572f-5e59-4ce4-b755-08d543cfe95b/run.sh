#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/cfdf572f-5e59-4ce4-b755-08d543cfe95b' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/cfdf572f-5e59-4ce4-b755-08d543cfe95b/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/eeb006d6badb985c404ab7a4cbbd479bbb0788d6e6a0312dde64abe3e73a5226.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
