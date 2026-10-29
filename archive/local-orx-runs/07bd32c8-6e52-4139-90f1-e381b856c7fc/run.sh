#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/07bd32c8-6e52-4139-90f1-e381b856c7fc' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/07bd32c8-6e52-4139-90f1-e381b856c7fc/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/28466a761f3aa064ae5f234283f4560ce56917758fe710664aeebef30f20cce6.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
