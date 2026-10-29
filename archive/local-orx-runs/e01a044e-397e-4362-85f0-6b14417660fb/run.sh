#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/e01a044e-397e-4362-85f0-6b14417660fb' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/e01a044e-397e-4362-85f0-6b14417660fb/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/2fc4896f6fc52871a08101da2a5e951b2fa3bfd3bd59e60da4f4d160345e7b5d.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
