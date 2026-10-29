import json,time,subprocess,datetime,os
from pathlib import Path
R=Path(__file__).resolve().parents[2];L=R/'p7r/compute/lease-57857438.json';EXP='5b7e1c8f-ee3d-4eea-a971-2fb6adc561bd'
while True:
 s=json.loads(L.read_text())
 if s['status'] in ['destroyed','budget_stopped']:break
 progress=R/'p7r/current-progress.json'
 if progress.exists() and json.loads(progress.read_text()).get('complete'):break
 if time.time()>=s['deadline_unix']-900:
  env=dict(os.environ,ORX_DATA_DIR='/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store');p=subprocess.run(['orx','exp','cancel',EXP,'--no-telemetry'],capture_output=True,text=True,env=env,timeout=90);(R/'p7r/compute/early-cancel-receipt.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'experiment_id':EXP,'reason':'Preserve15minute recovery margin under revised bandwidth-inclusive financial cap','exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr},indent=2));break
 time.sleep(15)
