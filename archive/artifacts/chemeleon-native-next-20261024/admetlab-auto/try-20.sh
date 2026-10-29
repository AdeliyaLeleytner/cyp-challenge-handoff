#!/bin/bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
# One diagnostic batch; reuse the same Chrome session and network.
# No locally imposed delay; respect an explicit server Retry-After if present.
"$HERE/.venv/bin/python" - "$HERE" <<'PY'
from pathlib import Path
import datetime as dt,json,sys,time
root=Path(sys.argv[1]);deadline=0
for folder in ('output','output-pilot-20'):
    for file in (root/folder/'batches').glob('*/state.json'):
        state=json.loads(file.read_text())
        if state.get('phase')!='rate_limited':continue
        deadline=max(deadline,state.get('retry_not_before') or 0)
if deadline>time.time():
    print('Сервер указал Retry-After до '+dt.datetime.fromtimestamp(deadline).astimezone().strftime('%H:%M:%S %Z')+'. Затем один пакет из20 молекул. Ctrl+C отменяет запуск.',flush=True)
    while time.time()<deadline:time.sleep(max(0,min(30,deadline-time.time())))
PY
exec bash "$HERE/run.sh" --input "$HERE/data/pilot-20.csv" --output "$HERE/output-pilot-20" --batch-size 20 --profile-dir "$HERE/output/chrome-profile"
