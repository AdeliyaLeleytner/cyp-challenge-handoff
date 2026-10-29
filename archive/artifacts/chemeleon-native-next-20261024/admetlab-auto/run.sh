#!/bin/bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
BOOTPY=""
for candidate in "$HERE/.venv/bin/python" /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  if "$candidate" -c 'import sys; assert sys.version_info >= (3,10)' 2>/dev/null; then
    BOOTPY="$candidate"
    break
  fi
done
if [ -z "$BOOTPY" ]; then
  echo 'Нужен Python3.10 или новее. Установите Python и повторите запуск.' >&2
  exit 1
fi
for arg in "$@"; do
  case "$arg" in
    --prepare-only|--status|--merge-only|--help|-h)
      exec "$BOOTPY" "$HERE/collect.py" "$@"
      ;;
  esac
done
if [ ! -x "$HERE/.venv/bin/python" ]; then
  "$BOOTPY" -m venv "$HERE/.venv"
fi
PY="$HERE/.venv/bin/python"
if ! "$PY" -c "from importlib.metadata import version; assert version('playwright') == '1.64.1'" 2>/dev/null; then
  "$PY" -m pip install --disable-pip-version-check 'playwright==1.64.1'
fi
# Installed Google Chrome is used; no additional browser binary is downloaded.
if [ "$(uname -s)" = Darwin ]; then
  exec caffeinate -i "$PY" "$HERE/collect.py" "$@"
fi
exec "$PY" "$HERE/collect.py" "$@"
