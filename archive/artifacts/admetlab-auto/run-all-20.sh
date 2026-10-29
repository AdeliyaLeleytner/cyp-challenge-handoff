#!/bin/bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
"$HERE/.venv/bin/python" "$HERE/prepare_all_20.py"
exec bash "$HERE/run.sh" --input "$HERE/data/molecules.csv" --output "$HERE/output-all-20" --batch-size 20 --profile-dir "$HERE/output/chrome-profile" "$@"
