#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export WANDB_MODE=disabled
bash night/strict_fullfit_setup.sh
python -u -m night.test_p3
export P3_DEADLINE_UNIX=$(python -c 'import json;print(json.load(open("/workspace/p3/lease.json"))["deadline_unix"])')
exec python -u -m night.p3_runner
