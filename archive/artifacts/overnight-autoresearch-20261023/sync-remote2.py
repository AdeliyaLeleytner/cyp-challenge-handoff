import subprocess,time,json
from pathlib import Path
p=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023');target=p/'remote2';target.mkdir(parents=True,exist_ok=True)
while not (p/'all-rentals-complete').exists():
 r=subprocess.run(['rsync','-az','--partial','--timeout=60','--exclude=feature-venv/','--exclude=tfm-venv/','--exclude=*.partial','cyp-night-57428215:/workspace/cyp-night/',str(target)+'/'],capture_output=True,text=True)
 (p/'sync-status2.json').write_text(json.dumps({'time':time.time(),'returncode':r.returncode,'stderr_tail':r.stderr[-300:]}))
 time.sleep(60)
