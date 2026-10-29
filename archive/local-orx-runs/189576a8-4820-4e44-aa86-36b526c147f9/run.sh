#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/189576a8-4820-4e44-aa86-36b526c147f9' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/189576a8-4820-4e44-aa86-36b526c147f9/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/56d1015447c3e99d0363739b88415babee1e022624d30391303be84bb452d6d9.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
