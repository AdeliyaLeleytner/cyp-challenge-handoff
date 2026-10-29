#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/9f152720-d5bb-479c-8b24-1f584e0ddb21' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/9f152720-d5bb-479c-8b24-1f584e0ddb21/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/39da869073de668491e05c79a279d8ff52bf9d6eb3ef6cebd326d8ef640887d4.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
