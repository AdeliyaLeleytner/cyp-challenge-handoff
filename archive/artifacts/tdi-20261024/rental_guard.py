from pathlib import Path
import json,subprocess,time,datetime
p=Path(__file__).resolve().parent;b=json.loads((p/'budget.json').read_text());i=json.loads((p/'rental-create.json').read_text())['new_contract'];start=datetime.datetime.fromisoformat(b['started_utc']).timestamp()
while not (p/'rental-complete').exists():
 try:
  credit=float(json.loads(subprocess.check_output(['vastai','show','user','--raw'],timeout=40))['credit']);state={'time':time.time(),'instance':i,'credit':credit,'account_balance_change':float(b['credit_before'])-credit,'spent':(time.time()-start)*b['lease_hourly_rate']/3600}
  if credit<=b['reserve'] or state['spent']>=b['max_spend'] or time.time()-start>b['max_wall_hours']*3600:
   r=subprocess.run(['vastai','stop','instance',str(i),'--raw'],capture_output=True,text=True,timeout=40);state.update(stop_attempted=True,returncode=r.returncode)
  (p/'guard-state.json').write_text(json.dumps(state))
 except Exception as e:(p/'guard-error.json').write_text(json.dumps({'time':time.time(),'type':type(e).__name__}))
 time.sleep(30)
