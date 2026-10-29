import time,json,subprocess
from pathlib import Path
p=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023'); ids=['57424368','57428215']; stopping=False
def call(args):
 r=subprocess.run(['/Users/adeliyaleleytner/.local/bin/vastai']+args+['--raw'],capture_output=True,text=True,timeout=45)
 if r.returncode:raise RuntimeError('provider_cli_failed')
 return json.loads(r.stdout)
while not (p/'all-rentals-complete').exists():
 state={'time':time.time(),'instances':ids,'reserve':1.80,'version':2}
 try:
  credit=float(call(['show','user'])['credit']);state['credit']=credit
  stopping=stopping or credit<=1.80 or time.time()>=1792818000
  if stopping:
   rows=call(['show','instances']);active=[str(x['id']) for x in rows if str(x['id']) in ids and x.get('actual_status') not in ['exited','stopped','destroyed']]
   state['action']='stopping_preserving_data';state['still_active']=active
   if not active:
    state['action']='verified_stopped_or_absent';(p/'budget-guard.json').write_text(json.dumps(state,indent=2));break
   for instance in active:
    r=subprocess.run(['/Users/adeliyaleleytner/.local/bin/vastai','stop','instance',instance,'--raw'],capture_output=True,text=True,timeout=45);state[instance]={'stop_returncode':r.returncode}
 except Exception as e:state['error_type']=type(e).__name__;stopping=stopping or time.time()>=1792818000
 (p/'budget-guard.json').write_text(json.dumps(state,indent=2));time.sleep(15 if stopping else 30)
