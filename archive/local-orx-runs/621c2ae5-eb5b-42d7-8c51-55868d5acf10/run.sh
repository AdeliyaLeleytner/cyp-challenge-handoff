#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/621c2ae5-eb5b-42d7-8c51-55868d5acf10' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/621c2ae5-eb5b-42d7-8c51-55868d5acf10/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/e267059db2156157fd8169f43237ae9eb8b5229e726470bc04295f1a5a3146b1.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
