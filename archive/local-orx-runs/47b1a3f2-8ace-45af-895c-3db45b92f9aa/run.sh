#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/47b1a3f2-8ace-45af-895c-3db45b92f9aa' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/47b1a3f2-8ace-45af-895c-3db45b92f9aa/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/cf61bb5820963deace7d7129557b093d36cfd53f20f79693beb0404a725dfdc8.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
