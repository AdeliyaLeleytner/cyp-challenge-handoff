import subprocess,time,json,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HOST='cyp-private-p3-57807389'; base='/workspace/p7/full-results'; local=ROOT/'p7/recovered/full-results';local.mkdir(parents=True,exist_ok=True)
log=ROOT/'p7/recovery-progress.jsonl';seen=set()
while True:
 lease=json.loads((ROOT/'p3/compute/lease.json').read_text())
 if lease['status'] in ['destroyed','budget_stopped']:break
 p=subprocess.run(['ssh',HOST,"find /workspace/p7/full-results -mindepth 2 -maxdepth 2 -name complete.json"],capture_output=True,text=True,timeout=50)
 if p.returncode==0:
  for line in p.stdout.splitlines():
   if not line.startswith(base+'/') or not line.endswith('/complete.json'):continue
   name=line.split('/')[-2]
   if name in seen:continue
   assert name in {f'{c}_f{k}' for c in ['zero','fusion'] for k in range(5)}
   t=time.time();q=subprocess.run(['rsync','-az','--partial',HOST+':'+base+'/'+name,str(local)+'/'],capture_output=True,text=True,timeout=900)
   with log.open('a') as f:f.write(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'job':name,'exit_code':q.returncode,'seconds':time.time()-t,'stderr':q.stderr[-500:]})+'\n')
   if q.returncode==0:seen.add(name)
 if len(seen)==10:break
 time.sleep(45)
