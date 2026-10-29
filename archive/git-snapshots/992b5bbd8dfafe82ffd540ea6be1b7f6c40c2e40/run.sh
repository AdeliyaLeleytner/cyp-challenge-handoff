#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
bash setup_remote.sh
exec python -u run.py
