from pathlib import Path
import subprocess,time,json
p=Path(__file__).resolve().parent
while not (p/'rental3-complete').exists():
 try:
  r=subprocess.run(['rsync','-az','--partial','--timeout=90','--exclude=*.partial','cyp-briford-57496410:/workspace/cyp-repro/',str(p/'remote')+'/'],capture_output=True,text=True,timeout=150)
  (p/'sync-status.json').write_text(json.dumps({'time':time.time(),'returncode':r.returncode,'stderr_tail':r.stderr[-300:]}))
 except Exception as e:(p/'sync-error.json').write_text(json.dumps({'time':time.time(),'type':type(e).__name__}))
 time.sleep(60)
