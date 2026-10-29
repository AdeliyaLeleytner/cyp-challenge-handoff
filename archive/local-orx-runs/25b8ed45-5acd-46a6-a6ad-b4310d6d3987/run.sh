#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/25b8ed45-5acd-46a6-a6ad-b4310d6d3987' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/25b8ed45-5acd-46a6-a6ad-b4310d6d3987/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/c2de40bba4eaf74cca0caa33f6ee34e7b46d540ab4a938b6c70a8ff46bb82aa8.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
