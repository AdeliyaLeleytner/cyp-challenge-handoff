#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
exec /Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python -u -m night.runner --config night_config.json
