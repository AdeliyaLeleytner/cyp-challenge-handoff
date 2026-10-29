#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2
exec /Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python -m night.private_p5b
