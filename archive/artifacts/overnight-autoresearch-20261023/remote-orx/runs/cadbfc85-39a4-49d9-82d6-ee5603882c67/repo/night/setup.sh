#!/bin/bash
set -euo pipefail
export PIP_DISABLE_PIP_VERSION_CHECK=1 HF_HUB_DISABLE_TELEMETRY=1 TABPFN_DISABLE_TELEMETRY=1
mkdir -p /workspace/cyp-night
# A host-wide lock prevents concurrent experiment bootstrap from racing pip.
exec 9>/workspace/cyp-night/setup.lock
flock 9
if [ ! -f /workspace/cyp-night/setup-v1.complete ]; then
  python -m pip install --no-cache-dir 'chemprop==2.2.1' 'lightning==2.5.5' 'rdkit==2026.9.1' 'pandas==2.3.3' 'numpy==2.2.6' 'scipy==1.16.2' 'scikit-learn==1.7.2' 'catboost==1.2.8' requests huggingface_hub
  python -m pip freeze > /workspace/cyp-night/requirements.remote.lock.txt
  touch /workspace/cyp-night/setup-v1.complete
fi
python - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('/workspace/cyp-night/assets')
for name,record in json.loads(Path('night_asset_manifest.json').read_text()).items():
    file=root/name
    assert file.stat().st_size==record['bytes'],name
    assert hashlib.sha256(file.read_bytes()).hexdigest()==record['sha256'],name
print('Pinned asset hashes verified',flush=True)
PY
