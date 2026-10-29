#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
bash night/strict_fullfit_setup.sh
exec python -u -m night.strict_fullfit_runner
