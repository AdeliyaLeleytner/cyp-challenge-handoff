#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/19fbf09f-f792-436b-bc26-121d8f74b655' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/19fbf09f-f792-436b-bc26-121d8f74b655/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/26e92afef3718fb94cc6f5f71de787915c45b98f926eaf4dcec4df3bd6538758.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
