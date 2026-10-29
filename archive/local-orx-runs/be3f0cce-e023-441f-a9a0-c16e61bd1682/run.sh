#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/be3f0cce-e023-441f-a9a0-c16e61bd1682' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/be3f0cce-e023-441f-a9a0-c16e61bd1682/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/5665302f034196016f411e954f07be6b40640450316d8154770cd049b7cc6c1c.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
