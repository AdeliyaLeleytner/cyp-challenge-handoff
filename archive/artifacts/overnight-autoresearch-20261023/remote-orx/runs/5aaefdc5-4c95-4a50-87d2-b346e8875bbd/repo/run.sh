#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export HF_HUB_DISABLE_TELEMETRY=1 TABPFN_DISABLE_TELEMETRY=1
bash night/setup.sh
exec 8>/workspace/cyp-night/tfm-setup.lock
flock 8
if [ ! -f /workspace/cyp-night/tfm-setup-v1.complete ]; then
  python -m venv --system-site-packages /workspace/cyp-night/tfm-venv
  /workspace/cyp-night/tfm-venv/bin/python -m pip install --no-cache-dir 'tabpfn==9.2.0' 'tabicl==2.2.0'
  /workspace/cyp-night/tfm-venv/bin/python -m pip freeze > /workspace/cyp-night/requirements.tfm.lock.txt
  touch /workspace/cyp-night/tfm-setup-v1.complete
fi
flock -u 8
/workspace/cyp-night/tfm-venv/bin/python -u - <<'ASSETS'
from pathlib import Path
import json
from night.fetch_features import fetch
root=Path('/workspace/cyp-night/assets')
features=json.loads((root/'feature_manifest.json').read_text())['features']
assert all(k in features for k in ['chemeleon_foundation','molformer','monroe'])
fetch('https://huggingface.co/Prior-Labs/tabpfn_3_5/resolve/06bf2ba35c80a92a3b9abb436b99cf49e7a0365e/tabpfn-v3.5-20260909.safetensors',root/'weights/tabpfn-v3.5-20260909.safetensors','ece4d67eadfea42eb0e610df5189bea60cb7f31073d81e9c7a019b76eacf0be3')
ASSETS
exec /workspace/cyp-night/tfm-venv/bin/python -u -m night.runner --config night_config.json
