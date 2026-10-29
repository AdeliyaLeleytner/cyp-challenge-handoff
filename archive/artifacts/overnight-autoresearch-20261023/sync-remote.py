import subprocess,time,json
from pathlib import Path
p=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023'); target=p/'remote'; target.mkdir(exist_ok=True)
while not (p/'rental-complete').exists():
 r=subprocess.run(['rsync','-az','--partial','--timeout=90','--exclude=feature-venv/','--exclude=*.partial','cyp-night-57424368:/workspace/cyp-night/',str(target)+'/'],capture_output=True,text=True)
 (p/'sync-status.json').write_text(json.dumps({'time':time.time(),'returncode':r.returncode,'stderr_tail':r.stderr[-500:]}))
 time.sleep(120)
