#!/bin/bash
set -euo pipefail
export PIP_DISABLE_PIP_VERSION_CHECK=1
mkdir -p /workspace/cyp-repro
exec 9>/workspace/cyp-repro/setup.lock
flock 9
if [ ! -f /workspace/cyp-repro/setup.complete ]; then
  python -m pip install --no-cache-dir 'chemprop==2.2.1' 'lightning==2.5.5' 'rdkit==2026.9.1' 'pandas==2.3.3' 'numpy==2.2.6' 'scipy==1.16.2' 'scikit-learn==1.7.2'
  python -m pip freeze > /workspace/cyp-repro/requirements.lock.txt
  touch /workspace/cyp-repro/setup.complete
fi
python - <<'PY'
import torch,json,importlib.metadata
print(json.dumps({'event':'native_runtime','cuda':torch.cuda.is_available(),'torch':torch.__version__,'packages':{p:importlib.metadata.version(p) for p in ['chemprop','lightning','rdkit','pandas','numpy','scipy','scikit-learn']}}),flush=True)
assert torch.cuda.is_available()
PY
python - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('/workspace/cyp-repro/assets')
for rel,r in json.loads(Path('native_input_manifest.json').read_text()).items():
 f=root/rel
 assert f.stat().st_size==r['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256'],rel
print('Native prepared data/folds/validator hashes verified',flush=True)
PY
