"""Read-only reconciliation of the restore dispatch. Polls the public board, then records the result.

Never submits. Writes an immutable reconciliation.json into the attempt directory so the
per-track cooldown guard can read a settled prior state before any future dispatch.
"""
from pathlib import Path
from datetime import datetime, timezone
import json, sys, time

HERE = Path(__file__).resolve().parent
TRANSPORT = Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026/model-audit/submission-transport')
sys.path.insert(0, str(TRANSPORT))
import live_contract as lc
import h6_submit as old

EXPECTED = '349165ecf50906e43a27f12dee97891a92cda59e798db614ef27a7c920c38a37'
DISPATCH_MINUTE = '2026-10-27 19:40 UTC'
INTERVAL = 180
LIMIT = 150 * 60


def read_board(endpoint):
    from gradio_client import Client
    live = Client(lc.SPACE, verbose=False).predict(api_name=endpoint)
    return live.get('value', live)


def main():
    prepared = json.loads((HERE / 'prepared.json').read_text())
    endpoint = prepared['contract']['leaderboard_refresh_endpoint']
    target = old.LEDGER / 'attempts' / prepared['attempt_key']
    deadline = time.monotonic() + LIMIT
    while True:
        live = read_board(endpoint)
        headers = live['headers']
        ours = [dict(zip(headers, r)) for r in live['data'] if r[1] in ('AdeliyaLL', 'AdeliyaLL-CYP')]
        stamp = datetime.now(timezone.utc).isoformat()
        scored = [o for o in ours if o.get('Submitted') == DISPATCH_MINUTE]
        if scored:
            row = scored[0]
            snapshot = HERE / 'board-processed.json'
            snapshot.write_text(json.dumps(live, indent=1, sort_keys=True) + '\n')
            snapshot.chmod(0o600)
            evidence = HERE / 'processed-result.json'
            value = {'checked_utc': stamp, 'status': 'processed', 'csv_sha256': EXPECTED,
                     'row': row, 'board_rows': len(live['data']),
                     'board_snapshot': lc.record(snapshot),
                     'match_rule': 'alias and the dispatch minute of this restore attempt',
                     'limit': 'Public board does not expose the uploaded file hash; this complements the local immutable intent and receipt.'}
            lc.dump(evidence, value)
            legacy = lc.legacy()
            legacy._immutable(target / 'reconciliation.json', legacy._json_bytes(
                {'reconciled_utc': stamp, 'status': 'processed', 'csv_sha256': EXPECTED,
                 'evidence': lc.record(evidence), 'row': row}))
            print(json.dumps({'status': 'processed', 'row': row}, ensure_ascii=False, indent=1))
            return 0
        if time.monotonic() >= deadline:
            value = {'checked_utc': stamp, 'status': 'still_pending', 'csv_sha256': EXPECTED,
                     'latest_visible_row': ours[0] if ours else None,
                     'note': 'Not scored within the polling window. No retry; reconcile later before any further dispatch.'}
            lc.dump(HERE / 'pending-result.json', value)
            print(json.dumps(value, ensure_ascii=False, indent=1))
            return 1
        time.sleep(INTERVAL)


if __name__ == '__main__':
    raise SystemExit(main())
