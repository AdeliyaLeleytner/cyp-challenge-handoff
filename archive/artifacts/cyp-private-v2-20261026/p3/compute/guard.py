import json,time,subprocess
from pathlib import Path
r=Path(__file__).parent
while True:
 s=json.loads((r/'lease.json').read_text())
 if s['status'] in ['destroyed','budget_stopped']:break
 if time.time()>=s['deadline_unix']:
  p=subprocess.run(['vastai','stop','instance',str(s['instance_id']),'--raw'],capture_output=True,text=True,timeout=60)
  (r/'budget-stop.json').write_text(json.dumps({'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}))
  if p.returncode==0:s['status']='budget_stopped';(r/'lease.json').write_text(json.dumps(s,indent=2));break
 time.sleep(20)
