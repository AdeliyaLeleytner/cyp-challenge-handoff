#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/0191f3b8-5d6b-4a7a-8a8d-8357345e02de' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/0191f3b8-5d6b-4a7a-8a8d-8357345e02de/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/4f677243386d454ede486b2887a233a71e1bb452a1273b9111cc3e59f8581695.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
