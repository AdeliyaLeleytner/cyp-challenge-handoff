#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
export HF_HOME=/workspace/cyp-tdi/hf-cache
bash tdi/setup.sh
exec python -u -m tdi.runner
