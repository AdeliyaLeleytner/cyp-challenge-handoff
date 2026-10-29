from pathlib import Path
import subprocess,json,time
ROOT=Path(__file__).resolve().parent
BUDGET=json.loads((ROOT/'budget.json').read_text())
INSTANCE=json.loads((ROOT/'rental-create.json').read_text())['new_contract']
DEADLINE=BUDGET['created_unix']+BUDGET['max_hours']*3600
while not (ROOT/'lease-complete.json').exists():
    state={'time':time.time(),'instance':INSTANCE,'deadline':DEADLINE,'estimated_cost_usd':(time.time()-BUDGET['created_unix'])/3600*BUDGET['quoted_usd_per_hour']}
    try:
        if (ROOT/'ssh-ready').exists():
            r=subprocess.run(['rsync','-az','--partial','--timeout=30','--exclude=browser-profile/',f'cyp-admet-browser-{INSTANCE}:/workspace/cyp-repro/admetlab_browser_all/',str(ROOT/'remote')+'/'],capture_output=True,text=True,timeout=60)
            state['backup_returncode']=r.returncode
        if time.time()>=DEADLINE:
            r=subprocess.run(['vastai','stop','instance',str(INSTANCE),'--raw'],capture_output=True,text=True,timeout=40)
            state.update(stop_attempted=True,stop_returncode=r.returncode)
            (ROOT/'guard-state.json').write_text(json.dumps(state));break
    except Exception as exc:state['error']=type(exc).__name__
    (ROOT/'guard-state.json').write_text(json.dumps(state))
    time.sleep(30)
