#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
bash night/setup.sh
bash night/setup_features.sh
export CUDA_VISIBLE_DEVICES=2 WANDB_MODE=disabled WANDB_DISABLED=true
exec /workspace/cyp-night/feature-venv/bin/python -u -m night.fetch_features
