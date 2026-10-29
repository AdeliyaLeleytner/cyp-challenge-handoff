import time,json,subprocess
from pathlib import Path
p=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023')
while not (p/'all-rentals-complete').exists():
 ids=[]
 for name in ['rental-create.json','rental-create-2.json']:
  f=p/name
  if f.exists():
   d=json.loads(f.read_text())
   if d.get('success') and d.get('new_contract'):ids.append(str(d['new_contract']))
 try:
  r=subprocess.run(['/Users/adeliyaleleytner/.local/bin/vastai','show','user','--raw'],capture_output=True,text=True,timeout=40)
  credit=float(json.loads(r.stdout)['credit'])
  state={'time':time.time(),'credit':credit,'instances':ids,'reserve':1.80}
  stop=credit<=1.80 or time.time()>=1792818000
 except Exception as e:
  state={'time':time.time(),'error_type':type(e).__name__,'instances':ids};stop=time.time()>=1792818000
 if stop:
  state['action']='stop_campaign_instances_preserve_data'
  for instance in ids:
   result=subprocess.run(['/Users/adeliyaleleytner/.local/bin/vastai','stop','instance',instance,'--raw'],capture_output=True,text=True,timeout=60)
   state[instance]={'stop_returncode':result.returncode}
  (p/'budget-guard.json').write_text(json.dumps(state,indent=2));break
 (p/'budget-guard.json').write_text(json.dumps(state,indent=2));time.sleep(30)
