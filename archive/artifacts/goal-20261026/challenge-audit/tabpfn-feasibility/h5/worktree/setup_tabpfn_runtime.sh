#!/bin/bash
set -euo pipefail
# Invoked only through the committed ORX run contract on this arm's fresh image.
TASK_ROOT=/workspace/cyp-tabpfn-admet
BASE_PYTHON=/opt/conda/bin/python
TFM_PYTHON="$TASK_ROOT/tfm-venv/bin/python"
mkdir -p "$TASK_ROOT/runtime"
"$BASE_PYTHON" - <<'PY'
import platform,torch
assert platform.python_version()=='3.11.13',platform.python_version()
assert torch.__version__=='2.8.0+cu128',torch.__version__
assert torch.cuda.is_available()
print({'event':'base_runtime_verified','python':platform.python_version(),'torch':torch.__version__,'gpu':torch.cuda.get_device_name(0)},flush=True)
PY
if [ ! -x "$TFM_PYTHON" ]; then
  "$BASE_PYTHON" -m venv --system-site-packages "$TASK_ROOT/tfm-venv"
fi
if [ ! -f "$TASK_ROOT/runtime/install-complete.json" ]; then
  "$TFM_PYTHON" -m pip --disable-pip-version-check install -r requirements.tabpfn-admet.txt -c constraints.tabpfn-runtime.txt
  "$TFM_PYTHON" -m pip freeze > "$TASK_ROOT/runtime/pip-freeze.txt"
  "$TFM_PYTHON" - <<'PY'
from pathlib import Path
import importlib.metadata,json,platform,torch
expected={'torch':'2.8.0+cu128','tabpfn':'9.2.0','numpy':'2.2.6','scikit-learn':'1.7.2','pandas':'2.3.3','rdkit':'2026.9.1'}
actual={p:importlib.metadata.version(p) for p in expected}
assert actual==expected,(actual,expected)
assert platform.python_version()=='3.11.13'
assert torch.cuda.is_available()
Path('/workspace/cyp-tabpfn-admet/runtime/install-complete.json').write_text(json.dumps({'packages':actual,'python':platform.python_version(),'cuda':torch.version.cuda},indent=2)+'\n')
print({'event':'isolated_runtime_ready','packages':actual},flush=True)
PY
fi
