#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
bash night/setup.sh
python -u -m night.reference_views --source-root /workspace/cyp-night/results/R0_reference_seed142_host2 --output-root /workspace/cyp-night/results/M1_reference_views142 --seed 142
exec python -u -m night.metamodel_runner --config meta_config.json
