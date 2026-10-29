#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/f23c6d16-ebcb-47e4-aaf0-43feb78f69df' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/f23c6d16-ebcb-47e4-aaf0-43feb78f69df/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/b923aec0199cbf30654307886267d51eed35cc8323952337b077f4e698b8155b.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
