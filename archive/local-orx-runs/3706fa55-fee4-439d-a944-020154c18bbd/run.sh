#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/3706fa55-fee4-439d-a944-020154c18bbd' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/3706fa55-fee4-439d-a944-020154c18bbd/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/16ea965eaa9e1fb32e9d05f0e39fa234ae99f8cf8a2580c95a63738b6ff09fe9.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
