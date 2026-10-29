#!/bin/bash
set -euo pipefail
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4
export VECLIB_MAXIMUM_THREADS=4
exec /Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python night/p9_tabicl_supervisor.py p9_tabicl_config.json
