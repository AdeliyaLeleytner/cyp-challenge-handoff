"""Recover only completed affected folds; reuse verified local unaffected folds."""
from pathlib import Path
import json,hashlib,subprocess,shutil,datetime
ROOT=Path(__file__).resolve().parent;HOST='cyp-strict-ref-57740054';REMOTE='/workspace/cyp-strict-reference/output'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
state=json.loads((ROOT/'execution-control.json').read_text());assert state['authorized_instance_id']==57740054
local=ROOT/'recovered-output';local.mkdir(exist_ok=True)
proof=json.loads((ROOT/'stage/purge-and-reuse-manifest.json').read_text());reuse_count=0
for cert in proof['reused_folds']:
 src=ROOT/'stage/reuse'/cert['cohort']/cert['member']/f"fold{cert['fold']}";dest=local/cert['cohort']/'results'/cert['member']/f"fold{cert['fold']}"
 if not dest.exists():shutil.copytree(src,dest)
 assert sha(dest/'complete.json')==cert['complete_sha256']
 for rel,h in cert['checkpoint_prediction_and_metadata_hashes'].items():assert sha(dest/rel)==h
 reuse_count+=1
code='''from pathlib import Path
import hashlib,json
root=Path("/workspace/cyp-strict-reference/output");result={}
for cohort in ["own750","briford529"]:
 for member in ["union18","2d6isoform6"]:
  for fold in range(5):
   d=root/cohort/"results"/member/("fold"+str(fold));p=d/"complete.json"
   if not p.exists():continue
   meta=json.loads(p.read_text());assert meta["status"]=="complete"
   for rel,h in meta["files"].items():assert hashlib.sha256((d/rel).read_bytes()).hexdigest()==h
   result[str(d.relative_to(root))]={"complete_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"files":meta["files"]}
print(json.dumps(result))
'''
ssh=['ssh','-o','HostName=175.155.64.155','-o','Port=19316','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=4',HOST,'python','-']
r=subprocess.run(ssh,input=code,text=True,capture_output=True,timeout=60,check=True)
manifest=json.loads(r.stdout.strip().splitlines()[-1]);(ROOT/'completed-folds-remote.json').write_text(json.dumps(manifest,indent=2)+'\n')
verified=[]
for rel,record in manifest.items():
 dest=local/rel
 ready=(dest/'complete.json').exists() and sha(dest/'complete.json')==record['complete_sha256'] and all((dest/p).exists() and sha(dest/p)==h for p,h in record['files'].items())
 if not ready:
  dest.mkdir(parents=True,exist_ok=True)
  subprocess.run(['rsync','-a','--partial','--delay-updates','--timeout=120','-e','ssh -o HostName=175.155.64.155 -o Port=19316 -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=4',HOST+':'+REMOTE+'/'+rel+'/',str(dest)+'/'],check=True,timeout=600)
 assert sha(dest/'complete.json')==record['complete_sha256']
 for name,h in record['files'].items():assert sha(dest/name)==h,(rel,name)
 verified.append(rel)
summary={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'instance_id':57740054,'run_id':state['run_id'],'verified_new_folds':len(verified),'verified_reused_folds_from_local_stage':reuse_count,'new_fold_paths':verified,'final_recovery':False}
(ROOT/'incremental-recovery.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
