#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export HF_HUB_DISABLE_TELEMETRY=1 TABPFN_DISABLE_TELEMETRY=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
# Fail on incomplete goal/selection/cache before bootstrap or any model access.
BASE_PYTHON="${CYP_TABPFN_PREFLIGHT_PYTHON:-/opt/conda/bin/python}"
"$BASE_PYTHON" -u -m night.tabpfn_final --preflight
if [ "${1:-}" = "--preflight" ]; then exit 0; fi
"$BASE_PYTHON" - <<'CHECK'
import json
assert json.load(open('tabpfn_final_config.json'))['training_enabled'] is True,'Preparation-only node; fitting disabled'
CHECK
if [ "${CYP_TABPFN_SKIP_SETUP:-0}" != "1" ]; then bash setup_tabpfn_runtime.sh; fi
TFM_PYTHON="${CYP_TABPFN_PYTHON:-/workspace/cyp-tabpfn-final/tfm-venv/bin/python}"
if [ ! -x "$TFM_PYTHON" ]; then echo 'Missing isolated Torch2.8+cu128 / TabPFN9.2 runtime' >&2; exit 2; fi
exec "$TFM_PYTHON" -u -m night.tabpfn_final "$@"
