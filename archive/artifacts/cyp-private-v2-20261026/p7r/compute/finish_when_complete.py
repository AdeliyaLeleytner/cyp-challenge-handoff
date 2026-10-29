"""Finish already-authorized P7R outputs; never launches a fit or another lease."""
import json,time,subprocess,hashlib,datetime,os,signal,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'p7r';C=R/'compute';HOST='cyp-private-p7r-57857438';LEASE=C/'lease-57857438.json';RUN='c95e19e7-e392-4a10-84c5-75d5af23f628'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,d):Path(p).write_text(json.dumps(d,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8388608),b''):h.update(b)
 return h.hexdigest()
def call(args,**kw):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=kw.pop('timeout',180),**kw)
try:
 while True:
  lease=json.loads(LEASE.read_text());progress=R/'current-progress.json'
  if progress.exists() and json.loads(progress.read_text()).get('complete'):break
  if lease['status'] in ['destroyed','budget_stopped']:raise RuntimeError('Lease stopped before full20 completion; preserve partial outputs')
  time.sleep(30)
 small=R/'recovered/metric-snapshot';small.mkdir(parents=True,exist_ok=True)
 call(['rsync','-az','--partial','--exclude=checkpoints',HOST+':/workspace/p7r/full-results/',str(small)+'/'],timeout=900)
 remote="""import json,hashlib\nfrom pathlib import Path\nr=Path('/workspace/p7r/full-results');d=json.loads((r/'complete.json').read_text());assert d['status']=='complete' and d['jobs']==20\nfiles={}\nfor p in sorted(r.rglob('*')):\n if p.is_file():\n  h=hashlib.sha256()\n  with p.open('rb') as f:\n   for x in iter(lambda:f.read(8388608),b''):h.update(x)\n  files[str(p.relative_to(r))]={'bytes':p.stat().st_size,'sha256':h.hexdigest()}\nprint(json.dumps({'files':files,'run_id':'c95e19e7-e392-4a10-84c5-75d5af23f628'}))\n"""
 result=call(['ssh',HOST,'python -'],input=remote,timeout=180);manifest=json.loads(next(x for x in reversed(result.stdout.splitlines()) if x.startswith('{')));save(R/'remote-file-manifest.json',manifest)
 outlog=(R/'readout.log').open('w');evalproc=subprocess.Popen(['/Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python',str(R/'readout.py'),'--results',str(small),'--stage',str(ROOT/'p7/stage'),'--output',str(R/'readout'),'--official',str(R/'evaluation-inputs/official-train.csv'),'--bootstrap','1000'],stdout=outlog,stderr=outlog,start_new_session=True)
 # Recovery daemon copies each immutable completed directory. Do not compete for its files.
 while True:
  ledger=R/'recovery-progress.jsonl';seen=set()
  if ledger.exists():
   for line in ledger.read_text().splitlines():
    x=json.loads(line)
    if x.get('exit_code')==0:seen.add(x['job'])
  if len(seen)==20:break
  if json.loads(LEASE.read_text())['status']!='active':raise RuntimeError('Lease stopped during recovery; no destructive teardown')
  time.sleep(20)
 full=R/'recovered/full-results';call(['rsync','-a','--exclude=checkpoints',str(small)+'/',str(full)+'/'])
 bad=[]
 for rel,v in manifest['files'].items():
  p=full/rel
  if not p.exists() or p.stat().st_size!=v['bytes'] or sha(p)!=v['sha256']:bad.append(rel)
 assert not bad,bad;assert sum(x.endswith('.ckpt') for x in manifest['files'])==20
 save(R/'RECOVERY_CERTIFICATE.json',{'utc':utc(),'status':'PASS','run_id':RUN,'checkpoint_count':20,'file_count':len(manifest['files']),'bytes':sum(x['bytes'] for x in manifest['files'].values()),'remote_manifest_sha256':sha(R/'remote-file-manifest.json'),'errors':[]})
 code=evalproc.wait(timeout=1200);outlog.close();assert code==0,'Independent readout failed; outputs safely recovered'
 spec=importlib.util.spec_from_file_location('lease_control',C/'lease_control.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);lease=json.loads(LEASE.read_text());lease['all_artifacts_hash_verified']=True;mod.save(LEASE,lease);receipt=mod.destroy_verified(LEASE,57857438);save(C/'FINAL_TEARDOWN.json',receipt)
 processes=json.loads((C/'processes-57857438.json').read_text());pid=processes['keepawake_pid'];command=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout.strip().split()
 if command and os.path.basename(command[0])=='caffeinate':os.kill(pid,signal.SIGTERM)
 statuspath=ROOT/'STATUS.json';status=json.loads(statuspath.read_text());status['recovery']={'scope':'P7R fullresults only','path':'p7r/recovered/full-results','hash_verification_pending':False,'copied_jobs':20,'all_bytes_verified':True,'certificate':'p7r/RECOVERY_CERTIFICATE.json'};status.update(updated_utc=utc(),phase='P7R full20 complete, readout verified, all20 checkpoints hashverified, ownedlease destroyed',active_run_id=None,completed_P7R_run_id=RUN,instance_status='destroyed',paid_instances_active=False,resource_cleanup_verified=True,guard_process_status='exiting_or_exited',recovery_process_status='complete',keepawake_process_status='terminated',worker_status={'scope':'P7R full20','completed_jobs':20,'complete':True},P7R_readout='p7r/readout/READOUT.json',P7R_recovery_certificate='p7r/RECOVERY_CERTIFICATE.json',P7R_teardown='p7r/compute/FINAL_TEARDOWN.json',next_authorized='Independent peer rescore, private result interpretation and actual billing reconciliation. No further fit/lease/publication authorized by this child.');save(statuspath,status)
 save(C/'FINISH_COMPLETE.json',{'utc':utc(),'status':'complete','readout_sha256':sha(R/'readout/READOUT.json'),'recovery_sha256':sha(R/'RECOVERY_CERTIFICATE.json'),'teardown_verified':True});print('P7R_FINISH_COMPLETE',flush=True)
except Exception as e:
 save(C/'FINISH_ERROR.json',{'utc':utc(),'type':type(e).__name__,'message':str(e)[:2000],'no_automatic_relaunch':True});raise
