"""Stop only this task-owned lease at its fixed deadline; preserve output storage."""
from pathlib import Path
import datetime,json,subprocess,time
ROOT=Path(__file__).resolve().parent
STATE=ROOT/'lease.json'
while True:
 state=json.loads(STATE.read_text())
 assert state['owner_experiment']=='8421e31b-790d-4c13-9f29-d3b9bdc1ee59'
 if state.get('status') in ('destroyed','aborted','released','budget_stopped'):break
 instance=state.get('instance_id')
 if instance and time.time()>=state['deadline_unix']:
  # Cancel only this experiment through ORX before stopping its sole leased instance.
  env=__import__('os').environ.copy();env['ORX_DATA_DIR']='/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store'
  try:subprocess.run(['orx','exp','cancel',state['owner_experiment']],env=env,capture_output=True,text=True,timeout=30)
  except Exception:pass
  try:
   result=subprocess.run(['/Users/adeliyaleleytner/.local/bin/vastai','stop','instance',str(instance),'--raw'],capture_output=True,text=True,timeout=45)
   event={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'instance_id':instance,'action':'stop_compute_preserve_storage','returncode':result.returncode}
   (ROOT/'guard-stop.json').write_text(json.dumps(event,indent=2)+'\n')
   if result.returncode==0:
    state['status']='budget_stopped';STATE.write_text(json.dumps(state,indent=2)+'\n');break
  except Exception as e:(ROOT/'guard-error.txt').write_text(type(e).__name__+': '+str(e))
 time.sleep(15)
