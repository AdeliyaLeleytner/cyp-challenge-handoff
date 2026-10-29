import subprocess,time,json
from pathlib import Path
p=Path(__file__).resolve().parent;started=time.time();instance=None
while not (p/'rental-complete').exists():
 try:
  if instance is None:
   d=json.loads((p/'rental-create.json').read_text())
   if not d.get('success'):break
   instance=d['new_contract']
  credit=float(json.loads(subprocess.run(['vastai','show','user','--raw'],capture_output=True,text=True,timeout=40,check=True).stdout)['credit'])
  state={'time':time.time(),'instance':instance,'credit':credit,'reserve':1.5,'deadline':started+3*3600}
  if credit<=1.5 or time.time()>started+3*3600:
   r=subprocess.run(['vastai','stop','instance',str(instance),'--raw'],capture_output=True,text=True,timeout=40)
   state.update(stop_attempted=True,stop_returncode=r.returncode)
  (p/'guard-state.json').write_text(json.dumps(state))
 except Exception as e:(p/'guard-error.json').write_text(json.dumps({'time':time.time(),'type':type(e).__name__}))
 time.sleep(30)
