#!/usr/bin/env bash
cd '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/d61f74fa-febd-4384-a381-78c3c79d294a' || exit 97
(
trap 'exit 143' TERM
trap 'code=$?; wait; echo "$code" > '\''/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/local-runs/d61f74fa-febd-4384-a381-78c3c79d294a/exit_code'\''; exit "$code"' EXIT
set -eo pipefail; mkdir -p repo; tar -xf '/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/source-snapshots/493b45412e1d3f20b422613f16e84738e73dc93e5db58c0fd0feb291e25e3d05.tar' -C repo; cd repo; bash run.sh
) > log 2>&1
