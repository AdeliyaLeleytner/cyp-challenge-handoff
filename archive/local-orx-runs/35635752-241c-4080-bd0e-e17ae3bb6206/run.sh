#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/35635752-241c-4080-bd0e-e17ae3bb6206' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/35635752-241c-4080-bd0e-e17ae3bb6206/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/d957a9d13fc216a17369af47614289813575fe321a1a5d27dde0f64c75bd536b.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
