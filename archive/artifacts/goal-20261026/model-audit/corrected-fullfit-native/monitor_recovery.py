"""Bounded transport-only monitor; never launches training or destroys a lease."""
from pathlib import Path
import subprocess,time,json,datetime
ROOT=Path(__file__).resolve().parent
PYTHON='/Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python'
while True:
 state=json.loads((ROOT/'execution/lease.json').read_text())
 if state.get('status') in ['destroyed','released','budget_stopped'] or time.time()>=state['deadline_unix']:break
 r=subprocess.run([PYTHON,str(ROOT/'recover.py')],capture_output=True,text=True,timeout=900)
 print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':'incremental_recovery','exit':r.returncode,'output':r.stdout[-1200:],'error':r.stderr[-400:]}),flush=True)
 if r.returncode==0:
  x=json.loads((ROOT/'incremental-recovery.json').read_text())
  if x['completed_remote_folds']==20:
   f=subprocess.run([PYTHON,str(ROOT/'recover.py'),'--final'],capture_output=True,text=True,timeout=900)
   print(json.dumps({'event':'final_recovery','exit':f.returncode,'output':f.stdout[-1200:],'error':f.stderr[-400:]}),flush=True)
   if f.returncode==0:
    v=subprocess.run([PYTHON,str(ROOT/'verify_recovered.py')],capture_output=True,text=True,timeout=180)
    (ROOT/'execution/local-verification.log').write_text(v.stdout+'\n'+v.stderr)
    print(json.dumps({'event':'local_verification','exit':v.returncode}),flush=True)
    break
 time.sleep(60)
