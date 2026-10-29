#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/3f276a29-e9f5-4ab9-9362-52cfca2793cb' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/3f276a29-e9f5-4ab9-9362-52cfca2793cb/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/1a626ccb4dd0839a5c4d0ba2564e14a9725ffbffbd31f9558621720cdafe4ec8.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
