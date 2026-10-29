import subprocess,time,json,os
from pathlib import Path
p=Path(__file__).resolve().parent
started=time.time(); deadline=started+11.5*3600
while not (p/'lease-complete').exists():
 state={'utc_epoch':time.time(),'instance':57536384,'deadline_epoch':deadline,'estimated_cost_usd':(time.time()-started)/3600*.05666666666666667}
 try:
  r=subprocess.run(['rsync','-az','--timeout=30','cyp-admetlab-57536384:/workspace/cyp-repro/admetlab_web_all/',str(p/'remote')+'/'],capture_output=True,text=True,timeout=60)
  state['backup_returncode']=r.returncode
  if time.time()>deadline:
   r=subprocess.run(['vastai','stop','instance','57536384','--raw'],capture_output=True,text=True,timeout=40)
   state.update(stopped_at_deadline=True,stop_returncode=r.returncode)
   (p/'guard-state.json').write_text(json.dumps(state));break
 except Exception as e:state['error']=type(e).__name__
 (p/'guard-state.json').write_text(json.dumps(state));time.sleep(45)
