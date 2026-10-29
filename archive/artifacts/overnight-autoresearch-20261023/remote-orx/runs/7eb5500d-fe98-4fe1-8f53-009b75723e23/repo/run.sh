#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
bash night/setup.sh
python -u -m night.reference_views --source-root /workspace/cyp-night/results/R0_reference_seed42 --output-root /workspace/cyp-night/results/M1_reference_views --seed 42
exec python -u -m night.metamodel_runner --config meta_config.json
