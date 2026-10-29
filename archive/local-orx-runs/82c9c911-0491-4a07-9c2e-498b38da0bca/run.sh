#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/82c9c911-0491-4a07-9c2e-498b38da0bca' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/82c9c911-0491-4a07-9c2e-498b38da0bca/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/d9e31767f0044948e8cff4b540ff866223f66f33a04a98a1c9389fde1326bb04.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
