#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/e9fbb5d2-1b02-4821-a153-d3312534c948' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/e9fbb5d2-1b02-4821-a153-d3312534c948/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/36bc896aa21b82b28b63a4a25e324c83eb58f818bfedbbfd5948235d529358de.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
