import subprocess,time,json
from pathlib import Path
p=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023');target=p/'quick'/'results';target.mkdir(parents=True,exist_ok=True)
while not (p/'rental-complete').exists():
 r=subprocess.run(['rsync','-az','--timeout=60','--include=*/','--include=*.csv','--include=*.json','--include=*.log','--exclude=*','cyp-night-57424368:/workspace/cyp-night/results/',str(target)+'/'],capture_output=True,text=True)
 (p/'quick-sync-status.json').write_text(json.dumps({'time':time.time(),'returncode':r.returncode,'stderr_tail':r.stderr[-300:]}))
 time.sleep(30)
