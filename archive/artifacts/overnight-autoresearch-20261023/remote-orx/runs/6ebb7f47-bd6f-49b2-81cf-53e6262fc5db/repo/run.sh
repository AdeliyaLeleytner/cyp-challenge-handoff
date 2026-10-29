#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
bash night/setup.sh
bash night/setup_features.sh
/workspace/cyp-night/feature-venv/bin/python -u - <<'WAIT'
import time,json
from pathlib import Path
root=Path('/workspace/cyp-night/assets')
for attempt in range(120):
    p=root/'feature_manifest.json';w=root/'weights/tabicl-regressor-v2-20260212.ckpt'
    if p.exists() and w.exists() and 'chemeleon_foundation' in json.loads(p.read_text()).get('features',{}):break
    if attempt%4==0:print('Waiting for pinned foundation features and TabICL weights',flush=True)
    time.sleep(15)
else:raise RuntimeError('Required feature assets not ready after30min')
WAIT
exec /workspace/cyp-night/feature-venv/bin/python -u -m night.runner --config night_config.json
