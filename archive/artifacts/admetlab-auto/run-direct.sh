#!/bin/bash
set -euo pipefail
TASK_DIR="$(cd "$(dirname "$0")" && pwd)"
exec /usr/bin/caffeinate -i /usr/bin/python3 "$TASK_DIR/direct_http.py" \
  --input "$TASK_DIR/../../cyp-admet500-pilot-20261025/next-official-5155.csv" \
  --output "$HOME/Downloads/ADMETlab-direct-official-500" "$@"
