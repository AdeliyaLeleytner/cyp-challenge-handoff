#!/bin/bash
set -euo pipefail
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
exec /Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python night/source_encoder_supervisor.py source_encoder_config.json
