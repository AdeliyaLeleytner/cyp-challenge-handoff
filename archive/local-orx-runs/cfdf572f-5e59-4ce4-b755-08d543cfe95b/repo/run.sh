#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
exec /Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python -u -m night.promotion_gate --manifest /Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/gate_bundle_v1/manifest.json --output /Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/gate_bundle_v1/certificate.json --n-bootstrap 2000
