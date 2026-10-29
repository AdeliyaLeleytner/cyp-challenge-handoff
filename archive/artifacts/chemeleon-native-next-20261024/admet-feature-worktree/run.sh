#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
# Standard-library gate fails on a partial/unbound feature cache before any setup/training.
python -u -m night.admet_feature_contract --config admet_feature_config.json
bash night/briford_setup.sh
exec python -u -m night.admet_feature_runner --config admet_feature_config.json
