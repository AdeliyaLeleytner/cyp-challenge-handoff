from pathlib import Path
import argparse,datetime,hashlib,json,subprocess,shutil,zipfile,csv
ROOT=Path(__file__).resolve().parent;HOST='cyp-strict-fullfit-57760728';REMOTE='/workspace/cyp-strict-fullfit/output';LOCAL=ROOT/'recovered-output'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--final',action='store_true');args=p.parse_args()
state=json.loads((ROOT/'execution/lease.json').read_text());assert state['instance_id']==57760728
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',HOST,'python','-']
code='''from pathlib import Path
import hashlib,json
root=Path('/workspace/cyp-strict-fullfit/output');result={}
for p in sorted(root.glob('results/*/fold*/complete.json')):
 d=p.parent;meta=json.loads(p.read_text());assert meta['status']=='complete'
 for rel,h in meta['files'].items():assert hashlib.sha256((d/rel).read_bytes()).hexdigest()==h
 result[str(d.relative_to(root))]={'complete_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'files':meta['files']}
print(json.dumps(result))
'''
def remote(code):
 r=subprocess.run(ssh,input=code,text=True,capture_output=True,timeout=90,check=True);return json.loads(r.stdout.strip().splitlines()[-1])
def sync(source,dest):
 dest.mkdir(parents=True,exist_ok=True);subprocess.run(['rsync','-a','--partial','--delay-updates','--timeout=120','-e','ssh -o BatchMode=yes -o ConnectTimeout=10',HOST+':'+source+'/',str(dest)+'/'],check=True,timeout=300)
proof=json.loads((ROOT/'stage/purge-and-reuse-manifest.json').read_text())
for cert in proof['reused_folds']:
 src=ROOT/'stage/reuse'/cert['member']/f"fold{cert['fold']}";dest=LOCAL/'results'/cert['member']/f"fold{cert['fold']}"
 if not dest.exists():shutil.copytree(src,dest)
 assert sha(dest/'complete.json')==cert['complete_sha256']
 for rel,h in cert['files'].items():assert sha(dest/rel)==h
found=remote(code)
for rel,m in found.items():
 dest=LOCAL/rel
 if not ((dest/'complete.json').exists() and sha(dest/'complete.json')==m['complete_sha256'] and all((dest/f).exists() and sha(dest/f)==h for f,h in m['files'].items())):sync(REMOTE+'/'+rel,dest)
 assert sha(dest/'complete.json')==m['complete_sha256']
 for f,h in m['files'].items():assert sha(dest/f)==h
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'instance_id':57760728,'completed_remote_folds':len(found),'verified_reused_folds':10,'verified_new_folds':sum('/union18/' in k or '/2d6isoform6/' in k for k in found),'final':args.final}
if args.final:
 inv='''from pathlib import Path
import hashlib,json
root=Path('/workspace/cyp-strict-fullfit/output');assert json.loads((root/'complete.json').read_text())['status']=='complete'
print(json.dumps({str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.rglob('*')) if p.is_file()}))
'''
 before=remote(inv);sync(REMOTE,LOCAL);after=remote(inv);assert before==after
 for f,m in after.items():assert (LOCAL/f).stat().st_size==m['bytes'] and sha(LOCAL/f)==m['sha256'],f
 ckpts=list(LOCAL.glob('results/*/fold*/checkpoints/*.ckpt'));assert len(ckpts)==20
 for f in ckpts:
  with zipfile.ZipFile(f) as z:assert z.testzip() is None and any(x.endswith('/data.pkl') for x in z.namelist())
 for f in LOCAL.rglob('*.csv'):
  with f.open(newline='') as h:r=csv.reader(h);assert len(next(r))>1 and sum(1 for _ in r)>0
 assert len(found)==20
 done=json.loads((LOCAL/'complete.json').read_text());assert done['retrained_folds']==done['reused_folds']==10
 for f,h in done['files'].items():assert sha(LOCAL/f)==h
 report.update({'remote_stable_during_recovery':True,'files':after,'checkpoint_archives_verified':20,'fold_completion_records_verified':20,'all_remote_hashes_match':True,'run_id':state.get('run_id')})
(ROOT/('recovery-certificate.json' if args.final else 'incremental-recovery.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='files'}))
