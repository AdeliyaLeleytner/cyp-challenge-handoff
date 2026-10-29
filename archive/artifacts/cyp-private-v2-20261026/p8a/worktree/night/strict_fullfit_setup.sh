#!/bin/bash
set -euo pipefail
export PIP_DISABLE_PIP_VERSION_CHECK=1
# Match the recorded parent runtime. Parent should select a torch2.6/cu124 image.
python - <<'PY'
import torch
assert torch.__version__ == '2.6.0+cu124', torch.__version__
assert torch.cuda.is_available()
PY
# Public PyPI TLS is unreachable from this task host; use its HTTPS package mirror.
python -m pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple --timeout 30 --retries 2 --no-cache-dir 'chemprop==2.2.1' 'lightning==2.5.5' 'rdkit==2026.9.1' 'pandas==2.3.3' 'numpy==2.2.6' 'scipy==1.16.2' 'scikit-learn==1.7.2'
python - <<'PY'
import importlib.metadata,json
names=['torch','chemprop','lightning','rdkit','numpy','pandas','scikit-learn','scipy']
print(json.dumps({'event':'corrected_reference_runtime','packages':{n:importlib.metadata.version(n) for n in names}}),flush=True)
PY
