#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/5eb45156-3345-46aa-9c34-55e87055aa7a' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/5eb45156-3345-46aa-9c34-55e87055aa7a/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/080523ab3060f96f4f2ba8faae069efcb7e3acae2ea4e7f6b8359403db803c30.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
