#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/75f89f21-ec7a-42a3-8943-4d8034d43052' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/75f89f21-ec7a-42a3-8943-4d8034d43052/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/f4f85731d4f618e3a47ed963b51a5c0708b19eb0e77abf732463bbd08686a0ad.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
