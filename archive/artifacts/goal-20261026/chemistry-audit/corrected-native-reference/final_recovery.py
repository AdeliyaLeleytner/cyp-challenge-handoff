"""Recover a terminal task's outputs and verify byte-for-byte hashes before teardown."""
from pathlib import Path
import json,hashlib,subprocess,csv,zipfile,datetime
ROOT=Path(__file__).resolve().parent;HOST='cyp-strict-ref-57740054';REMOTE='/workspace/cyp-strict-reference/output'
control=json.loads((ROOT/'execution-control.json').read_text());assert control['authorized_instance_id']==57740054
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ssh=['ssh','-o','HostName=175.155.64.155','-o','Port=19316','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=4',HOST,'python','-']
code='''from pathlib import Path
import hashlib,json
root=Path("/workspace/cyp-strict-reference/output");files={}
for p in sorted(root.rglob("*")):
 if p.is_file():files[str(p.relative_to(root))]={"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
print(json.dumps({"files":files,"complete":json.loads((root/"complete.json").read_text()) if (root/"complete.json").exists() else None}))
'''
def inventory():
 p=subprocess.run(ssh,input=code,text=True,capture_output=True,timeout=90,check=True);return json.loads(p.stdout.strip().splitlines()[-1])
before=inventory();local=ROOT/'recovered-output';local.mkdir(exist_ok=True)
subprocess.run(['rsync','-a','--partial','--delay-updates','--timeout=120','-e','ssh -o HostName=175.155.64.155 -o Port=19316 -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4',HOST+':'+REMOTE+'/',str(local)+'/'],check=True,timeout=600)
after=inventory();assert before==after,'Remote artifacts changed during final recovery'
for rel,r in after['files'].items():
 p=local/rel;assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],rel
csvs=0;checkpoints=0;folds=0;readability_errors=[]
complete_run=after['complete'] is not None and after['complete']['status']=='complete'
for p in local.rglob('*'):
 if p.suffix=='.csv':
  try:
   with p.open(newline='') as f:reader=csv.reader(f);header=next(reader);assert len(header)>1;assert sum(1 for _ in reader)>0
   csvs+=1
  except Exception as exc:readability_errors.append({'file':str(p.relative_to(local)),'error':type(exc).__name__})
 if p.suffix=='.ckpt':
  try:
   with zipfile.ZipFile(p) as z:assert z.testzip() is None and any(x.endswith('/data.pkl') for x in z.namelist())
   checkpoints+=1
  except Exception as exc:readability_errors.append({'file':str(p.relative_to(local)),'error':type(exc).__name__})
 if p.name=='complete.json' and p.parent.name.startswith('fold'):
  d=json.loads(p.read_text());assert d['status']=='complete'
  for rel,h in d['files'].items():assert sha(p.parent/rel)==h
  folds+=1
# The ORX main log is recovered separately from the scientific output tree.
run_id=control['run_id'];log=ROOT/'orx-run.log'
subprocess.run(['rsync','-a','--timeout=120','-e','ssh -o HostName=175.155.64.155 -o Port=19316 -o BatchMode=yes -o ConnectTimeout=10',HOST+':/root/.orx/runs/'+run_id+'/log',str(log)],check=True,timeout=90)
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'instance_id':57740054,'run_id':run_id,'remote_files':len(after['files']),'remote_bytes':sum(x['bytes'] for x in after['files'].values()),'all_remote_hashes_match':True,'remote_stable_across_recovery':True,'complete_run':complete_run,'readability_errors':readability_errors,'checkpoint_archives_verified':checkpoints,'fold_completion_records_verified':folds,'csv_files_readable':csvs,'orx_log_sha256':sha(log),'files':after['files']}
if report['complete_run']:assert checkpoints==40 and folds==40 and not readability_errors
(ROOT/'recovery-certificate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='files'}))
