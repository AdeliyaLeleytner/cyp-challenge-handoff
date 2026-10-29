#!/bin/bash
set -euo pipefail
mkdir -p /workspace/cyp-tdi
exec 9>/workspace/cyp-tdi/setup.lock
flock 9
if [ ! -f /workspace/cyp-tdi/setup.complete ]; then
 python -m pip install --no-cache-dir 'chemprop==2.2.1' 'lightning==2.5.5' 'rdkit==2026.9.1' 'pandas==2.3.3' 'numpy==2.2.6' 'scipy==1.16.2' 'scikit-learn==1.7.2' 'lightgbm==4.7.0' 'tabicl==2.2.0'
 python -m pip freeze > /workspace/cyp-tdi/requirements.lock.txt
 touch /workspace/cyp-tdi/setup.complete
fi
python - <<'PY'
from pathlib import Path
import json,hashlib,torch,importlib.metadata
assert torch.cuda.is_available()
for rel,record in json.loads(Path('input_manifest.json').read_text()).items():
 p=Path('/workspace/cyp-tdi/assets')/rel
 assert p.stat().st_size==record['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256'],rel
print(json.dumps({'event':'environment_ready','GPUs':torch.cuda.device_count(),'packages':{p:importlib.metadata.version(p) for p in ['torch','chemprop','lightgbm','tabicl','rdkit','scikit-learn']}}),flush=True)
PY

python - <<'PYSETUP'
from pathlib import Path
import numpy as np,hashlib,json,shutil,torch
from tabicl import TabICLClassifier
root=Path('/workspace/cyp-tdi');pin=root/'tabicl-classifier.ckpt'
if not (root/'tabicl-smoke.json').exists():
 m=TabICLClassifier(n_estimators=1,device='cuda',random_state=42)
 X=np.random.default_rng(42).normal(size=(24,6));m.fit(X,np.arange(24)%2);q=m.predict_proba(X[:3]);assert q.shape==(3,2) and np.isfinite(q).all()
 files=list((root/'hf-cache').rglob('tabicl-classifier-v2-20260212.ckpt'));assert files, 'Downloaded classifier checkpoint not located'
 shutil.copyfile(files[0],pin)
 (root/'tabicl-smoke.json').write_text(json.dumps({'checkpoint_sha256':hashlib.sha256(pin.read_bytes()).hexdigest(),'checkpoint_version':'tabicl-classifier-v2-20260212.ckpt','test':'Synthetic24rowsforruntimeonly; notscientificresult'}))
 print('TabICL CUDA smoke passed; classifier checkpoint pinned',flush=True)
PYSETUP
