#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
bash night/setup.sh
exec python -u -m night.bindingdb_patents --asset-root /workspace/cyp-night/assets --release 202610
