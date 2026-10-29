#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/91b8e4ae-48f9-48e6-91d1-08d1937b280e' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/91b8e4ae-48f9-48e6-91d1-08d1937b280e/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/e61bf715f8d67f1979272349850f3e8caf6841c80b236c7a9e97dbdefcc23542.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
