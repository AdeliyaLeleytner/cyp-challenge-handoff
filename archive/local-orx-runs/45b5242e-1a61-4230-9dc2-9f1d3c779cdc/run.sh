#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/45b5242e-1a61-4230-9dc2-9f1d3c779cdc' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/45b5242e-1a61-4230-9dc2-9f1d3c779cdc/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/1f33d99dc5d86c0dc4f9e82535daa8da0325851ae781b74a8c51a9c2bc253553.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
