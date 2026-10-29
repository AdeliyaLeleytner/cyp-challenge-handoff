#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
bash setup_encoder_runtime.sh
exec /workspace/cyp-tabpfn-admet/encoder-venv/bin/python -u -m night.adme_blind_bank
