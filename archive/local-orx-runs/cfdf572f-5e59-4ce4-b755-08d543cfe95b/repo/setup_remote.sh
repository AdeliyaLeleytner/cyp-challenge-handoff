#!/bin/bash
set -euo pipefail
export PIP_DISABLE_PIP_VERSION_CHECK=1
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export HF_HUB_DISABLE_TELEMETRY=1 TABPFN_DISABLE_TELEMETRY=1
python -m pip install --no-cache-dir 'chemprop==2.2.1' 'lightning==2.5.5' 'rdkit==2026.9.1' 'lightgbm==4.6.0' 'pandas==2.3.3' 'numpy==2.2.6' 'scipy==1.16.2' 'scikit-learn==1.7.2' 'tabpfn==9.2.0' requests huggingface_hub
python -m pip freeze > requirements.remote.lock.txt
python -u prepare_remote.py
