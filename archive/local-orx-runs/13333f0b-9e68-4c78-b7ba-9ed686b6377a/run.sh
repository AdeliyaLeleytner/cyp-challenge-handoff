#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/13333f0b-9e68-4c78-b7ba-9ed686b6377a' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/13333f0b-9e68-4c78-b7ba-9ed686b6377a/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/ca8a88becad49174a4ff8be861c8d0c484764c1b3f860d137aa1d1677d4ae18e.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
