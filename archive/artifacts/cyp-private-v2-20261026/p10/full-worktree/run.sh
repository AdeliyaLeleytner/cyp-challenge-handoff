#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 WANDB_MODE=disabled
bash night/strict_fullfit_setup.sh
python -u -m night.test_p10
export P10_DEADLINE_UNIX=$(python -c 'import json;print(json.load(open("/workspace/p10/lease.json"))["deadline_unix"])')
exec python -u -m night.p10_runner
