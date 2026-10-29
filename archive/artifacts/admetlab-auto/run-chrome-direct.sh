#!/bin/bash
set -euo pipefail
TASK_DIR="$(cd "$(dirname "$0")" && pwd)"
exec /usr/bin/caffeinate -i /usr/bin/python3 "$TASK_DIR/chrome_routed.py" "$@"
