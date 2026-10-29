#!/bin/bash
set -euo pipefail
exec 8>/workspace/cyp-night/feature-setup.lock
flock 8
if [ ! -f /workspace/cyp-night/feature-setup-v1.complete ]; then
  python -m venv --system-site-packages /workspace/cyp-night/feature-venv
  /workspace/cyp-night/feature-venv/bin/python -m pip install --no-cache-dir 'torch-geometric==2.7.0' 'transformers==5.12.1' 'tabicl==2.2.0' 'datamol==0.12.5' 'wandb==0.22.2' 'pyarrow==21.0.0'
  /workspace/cyp-night/feature-venv/bin/python -m pip freeze > /workspace/cyp-night/requirements.features.lock.txt
  touch /workspace/cyp-night/feature-setup-v1.complete
fi
