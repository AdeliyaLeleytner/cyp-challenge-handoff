"""Local budget guard: stop only the task-owned GPU lease at its deadline."""
import json,time,subprocess,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
while True:
 state=json.loads((ROOT/'control-lease.json').read_text())
 assert state['instance_id']==57740054
 if state.get('status') in ('destroyed','released','budget_stopped'):break
 if time.time()>=state['deadline_unix']:
  r=subprocess.run(['/Users/adeliyaleleytner/.local/bin/vastai','stop','instance','57740054','--raw'],capture_output=True,text=True,timeout=60)
  record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'instance_id':57740054,'action':'stop_compute_preserve_storage','exit_code':r.returncode,'response':r.stdout[:1000],'error':r.stderr[:500]}
  (ROOT/'budget-stop.json').write_text(json.dumps(record,indent=2)+'\n')
  if r.returncode==0:
   state['status']='budget_stopped';(ROOT/'control-lease.json').write_text(json.dumps(state,indent=2)+'\n');break
 time.sleep(30)
