#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/9d9731a6-6fa0-41e3-afb7-1cc9cea366f1' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/9d9731a6-6fa0-41e3-afb7-1cc9cea366f1/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/899ff99a94892ba358e05c9951af92c377e518cb3be521b046097c5790303209.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
