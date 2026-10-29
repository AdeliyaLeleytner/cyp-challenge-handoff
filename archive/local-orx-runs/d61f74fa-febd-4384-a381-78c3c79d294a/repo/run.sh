#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
exec /Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python -u -m night.final_ensemble --config final_ensemble_config.json
