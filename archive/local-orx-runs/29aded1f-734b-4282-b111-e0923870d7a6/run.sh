#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/29aded1f-734b-4282-b111-e0923870d7a6' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/29aded1f-734b-4282-b111-e0923870d7a6/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/e304559cc0da98af14dadecdb2dcdb55f41aeaf30c211c1268b85178bc9e805e.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
