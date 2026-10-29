#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/5ba35a33-5f03-4603-a4cc-e2a8030b3f2e' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/5ba35a33-5f03-4603-a4cc-e2a8030b3f2e/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/3b00f32e1bba9407b8e20054a64242cd87c22e201c722b3badf2b39a3781e953.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
