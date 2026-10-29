import subprocess,time,json,datetime,os,signal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HOST='cyp-private-p7r-57857438'; base='/workspace/p7r/full-results'; local=ROOT/'p7r/recovered/full-results';local.mkdir(parents=True,exist_ok=True)
log=ROOT/'p7r/recovery-progress.jsonl';seen=set()
if log.exists():
 for line in log.read_text().splitlines():
  x=json.loads(line)
  if x.get('exit_code')==0 and x.get('job'):seen.add(x['job'])
def call(cmd,timeout):
 p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
 try:
  out,err=p.communicate(timeout=timeout);return subprocess.CompletedProcess(cmd,p.returncode,out,err)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:out,err=p.communicate(timeout=5)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
  return subprocess.CompletedProcess(cmd,124,out,err+'\nBounded read-only recovery timeout; retry pending.')
while True:
 lease=json.loads((ROOT/'p7r/compute/lease-57857438.json').read_text())
 if lease['status'] in ['destroyed','budget_stopped']:break
 p=call(['ssh',HOST,"find /workspace/p7r/full-results -mindepth 2 -maxdepth 2 -name complete.json"],50)
 if p.returncode==0:
  for line in p.stdout.splitlines():
   if not line.startswith(base+'/') or not line.endswith('/complete.json'):continue
   name=line.split('/')[-2]
   if name in seen:continue
   assert name in {f'{c}_f{k}' for c in ['zero','original','masked','repaired'] for k in range(5)}
   t=time.time();q=call(['rsync','-az','--partial',HOST+':'+base+'/'+name,str(local)+'/'],900)
   with log.open('a') as f:f.write(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'job':name,'exit_code':q.returncode,'seconds':time.time()-t,'stderr':q.stderr[-500:]})+'\n')
   if q.returncode==0:seen.add(name)
 if len(seen)==20:break
 time.sleep(45)
