#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/adf173dc-4754-4383-8016-3d57cbd3fb11' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/adf173dc-4754-4383-8016-3d57cbd3fb11/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/171ab30e1fd4ccdef2ccc1e1bd78deb42edf83d30a220e82c6b5fa2045923406.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
