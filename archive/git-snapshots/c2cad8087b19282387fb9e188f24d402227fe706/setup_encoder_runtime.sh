#!/bin/bash
set -euo pipefail
TASK_ROOT=/workspace/cyp-tabpfn-admet
BASE_PYTHON=/opt/conda/bin/python
ENCODER_PYTHON="$TASK_ROOT/encoder-venv/bin/python"
mkdir -p "$TASK_ROOT/encoder-runtime"
"$BASE_PYTHON" - <<'PY'
import platform,torch
assert platform.python_version()=='3.11.13'
assert torch.__version__=='2.8.0+cu128' and torch.cuda.is_available()
PY
if [ ! -x "$ENCODER_PYTHON" ]; then "$BASE_PYTHON" -m venv --system-site-packages "$TASK_ROOT/encoder-venv"; fi
if [ ! -f "$TASK_ROOT/encoder-runtime/install-complete.json" ]; then
  "$ENCODER_PYTHON" -m pip --disable-pip-version-check install -r requirements.encoder.txt -c constraints.tabpfn-runtime.txt
  "$ENCODER_PYTHON" -m pip freeze > "$TASK_ROOT/encoder-runtime/pip-freeze.txt"
  "$ENCODER_PYTHON" - <<'PY'
from pathlib import Path
import importlib.metadata,json
expected={'torch':'2.8.0+cu128','chemprop':'2.2.1','lightning':'2.5.5','rdkit':'2026.9.1','numpy':'2.2.6'}
actual={p:importlib.metadata.version(p) for p in expected};assert actual==expected
Path('/workspace/cyp-tabpfn-admet/encoder-runtime/install-complete.json').write_text(json.dumps(actual,indent=2)+'\n')
print({'event':'isolated_encoder_runtime_ready','packages':actual},flush=True)
PY
fi
