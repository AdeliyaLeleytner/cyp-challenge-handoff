#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/f870d574-9ed7-4b77-b0c6-e42ec35509dd' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/f870d574-9ed7-4b77-b0c6-e42ec35509dd/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/0a804705a431288974f0db431954da1527c34c9e8beb28c1141ceaa39b98f193.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
