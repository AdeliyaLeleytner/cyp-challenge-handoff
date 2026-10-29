#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 WANDB_MODE=disabled
bash night/strict_fullfit_setup.sh
python -u -m night.test_p3
python -u -m night.test_p7
python -u -m night.test_p7r_stage
export P7R_DEADLINE_UNIX=$(python -c 'import json;print(json.load(open("/workspace/p7r/lease.json"))["deadline_unix"])')
exec python -u -m night.p7r_runner
