"""Read-only compact progress from the continuously recovered artifacts."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
for variant in ('chemeleon_strae_bf16', 'scratch_strae_bf16_fp32val_repair1'):
    root = ROOT / 'remote/results' / variant
    rows = []
    for log in root.rglob('worker.log'):
        events = []
        for line in log.read_text(errors='replace').splitlines():
            if line.startswith('{'):
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get('event') == 'exact_strae_epoch':
                    events.append(event)
        if not (log.parent / 'complete.json').exists():
            rows.append({'fold': str(log.parent.relative_to(root)),
                         'last_epoch': events[-1]['epoch'] if events else None,
                         'best_inner_ST_RAE': min(e['val_primary_strae'] for e in events) if events else None})
    print(json.dumps({'variant': variant,
                     'completed_folds': len(list(root.glob('*/results/*/fold*/complete.json'))) + len(list(root.glob('*/*/results/*/fold*/complete.json'))),
                     'active': rows,
                     'failure_diagnostics': [str(f.relative_to(root)) for f in root.rglob('validation_nonfinite*.json')],
                     'final_scores_exist': (root / 'scores.json').exists()}))
