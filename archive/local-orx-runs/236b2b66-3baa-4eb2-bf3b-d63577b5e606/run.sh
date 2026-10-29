#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/236b2b66-3baa-4eb2-bf3b-d63577b5e606' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/236b2b66-3baa-4eb2-bf3b-d63577b5e606/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/fb5f73b3d49d05f80b5ff9146160f3a70c8e8b56bc7db3f75c8b5ee9e3c63caa.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
