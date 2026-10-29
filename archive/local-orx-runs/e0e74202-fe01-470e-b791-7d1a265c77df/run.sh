#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/e0e74202-fe01-470e-b791-7d1a265c77df' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/e0e74202-fe01-470e-b791-7d1a265c77df/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/a8ee54ebb80d06e2e6e3514ff9dd2d7844bd8bdadc0b96c1e8bccbb4f6843306.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
