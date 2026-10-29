#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export HF_HUB_DISABLE_TELEMETRY=1 TABPFN_DISABLE_TELEMETRY=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
# Dedicated new task image; bootstrap is tracked by this same ORX run, never a raw SSH fit.
if [ "${CYP_TABPFN_SKIP_SETUP:-0}" != "1" ]; then bash setup_tabpfn_runtime.sh; fi
TFM_PYTHON="${CYP_TABPFN_PYTHON:-/workspace/cyp-tabpfn-admet/tfm-venv/bin/python}"
if [ ! -x "$TFM_PYTHON" ]; then echo 'Missing isolated Torch2.8+cu128 / TabPFN9.2 runtime' >&2; exit 2; fi
exec "$TFM_PYTHON" -u -m night.tabpfn_evaluate "$@"
