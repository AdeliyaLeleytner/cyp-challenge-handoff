#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
bash night/setup.sh
bash night/setup_features.sh
export CUDA_VISIBLE_DEVICES=2 WANDB_MODE=disabled WANDB_DISABLED=true
exec /workspace/cyp-night/feature-venv/bin/python -u -m night.audit_monroe_pcba --official-train /workspace/cyp-night/assets/official-train.csv --official-test /workspace/cyp-night/assets/official-test.csv --monroe-source /workspace/cyp-night/assets/sources/Monroe --cache-root /workspace/cyp-night/assets/pcba-audit-cache --output-dir /workspace/cyp-night/results/monroe_pcba_audit --workers 8
