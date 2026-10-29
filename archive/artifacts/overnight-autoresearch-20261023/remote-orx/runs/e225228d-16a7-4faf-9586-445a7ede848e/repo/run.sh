#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 HF_HUB_DISABLE_TELEMETRY=1
bash night/setup.sh
python -m venv --system-site-packages /workspace/cyp-night/unimol-venv
/workspace/cyp-night/unimol-venv/bin/python -m pip install --no-cache-dir 'numpy==2.2.6' 'pandas==2.2.3' 'scipy==1.15.3' 'rdkit==2026.9.1' 'numba==0.61.2' 'addict==2.4.0' 'tqdm==4.67.1'
/workspace/cyp-night/unimol-venv/bin/python -m pip freeze > /workspace/cyp-night/requirements.unimol.lock.txt
python -u - <<'ASSETS'
from pathlib import Path
import subprocess,json
from night.fetch_features import fetch
root=Path('/workspace/cyp-night/assets');source=root/'sources/unimol_tools';revision='670afbd3144b58caef1d76cc618ddfeaecab8424'
if not source.exists():subprocess.run(['git','clone','--filter=blob:none','--no-checkout','https://github.com/deepmodeling/unimol_tools.git',str(source)],check=True)
subprocess.run(['git','-C',str(source),'fetch','--depth','1','origin',revision],check=True)
subprocess.run(['git','-C',str(source),'checkout','--detach',revision],check=True)
fetch('https://huggingface.co/dptech/Uni-Mol2/resolve/bf37d253c0f5ac61f468137eb00059978a104ff0/modelzoo/84M/checkpoint.pt',root/'weights/unimol2_84m/checkpoint.pt','5b9241630f1cf0b173fb06d1e76096e5daf5f91c3e51b066ba69524dafe60e35')
out=Path('/workspace/cyp-night/results/F1_unimol');out.mkdir(parents=True,exist_ok=True)
(out/'config.json').write_text(json.dumps({'batch_size':8,'conformer_workers':8,'seed':42,'device':'cuda','max_atoms':256}))
ASSETS
export CUDA_VISIBLE_DEVICES=2
exec timeout 1800 /workspace/cyp-night/unimol-venv/bin/python -u -m night.unimol_features --molecules /workspace/cyp-night/assets/all_molecules.csv --toolkit-root /workspace/cyp-night/assets/sources/unimol_tools --checkpoint /workspace/cyp-night/assets/weights/unimol2_84m/checkpoint.pt --asset-root /workspace/cyp-night/assets --asset-key unimol2_84m_foundation --config /workspace/cyp-night/results/F1_unimol/config.json --audit-path /workspace/cyp-night/results/F1_unimol/audit.json
