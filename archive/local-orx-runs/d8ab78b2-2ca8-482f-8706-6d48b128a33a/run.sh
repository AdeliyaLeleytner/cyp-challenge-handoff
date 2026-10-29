#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/d8ab78b2-2ca8-482f-8706-6d48b128a33a' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/d8ab78b2-2ca8-482f-8706-6d48b128a33a/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/9ba3ad17ac8b42f3c79076543a4dbd865bb20cc4f1983b76653052fe1dd27c73.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
