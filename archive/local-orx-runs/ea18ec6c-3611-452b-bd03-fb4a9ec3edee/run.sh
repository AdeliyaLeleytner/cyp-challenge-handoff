#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/ea18ec6c-3611-452b-bd03-fb4a9ec3edee' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/ea18ec6c-3611-452b-bd03-fb4a9ec3edee/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/d2afb046b5d949c33ef9124c5283667a7e97b13889ddffa0be99619eb865eb8b.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
