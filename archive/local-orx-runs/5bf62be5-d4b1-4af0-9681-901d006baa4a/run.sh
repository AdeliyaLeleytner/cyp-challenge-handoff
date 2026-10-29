#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/5bf62be5-d4b1-4af0-9681-901d006baa4a' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/5bf62be5-d4b1-4af0-9681-901d006baa4a/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/2bc4400c5d4fe5abaf841d9140539c08fd9d2cca39fc23db0e907d44e9c592b1.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
