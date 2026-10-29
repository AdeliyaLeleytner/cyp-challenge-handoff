#!/bin/bash
set -euo pipefail
export MPLBACKEND=Agg
export OMP_NUM_THREADS=2
exec /Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python night/p7_diagnosis.py --config p7_diagnosis_config.json
