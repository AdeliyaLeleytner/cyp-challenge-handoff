"""Finish already-authorized P10 outputs; never launches a fit or another lease."""
import json,time,subprocess,hashlib,datetime,os,signal,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'p10';C=R/'compute';HOST='cyp-private-p10-57884190';LEASE=C/'lease-57884190.json';RUN='7d3f8947-e1f1-43f7-9621-e304afd2d07e'
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
 call(['rsync','-az','--partial','--exclude=checkpoints','--exclude=selected-model.pt',HOST+':/workspace/p10/full-results/',str(small)+'/'],timeout=900)
 remote="""import json,hashlib\nfrom pathlib import Path\nr=Path('/workspace/p10/full-results');d=json.loads((r/'complete.json').read_text());assert d['status']=='complete' and d['jobs']==20\nfiles={}\nfor p in sorted(r.rglob('*')):\n if p.is_file():\n  h=hashlib.sha256()\n  with p.open('rb') as f:\n   for x in iter(lambda:f.read(8388608),b''):h.update(x)\n  files[str(p.relative_to(r))]={'bytes':p.stat().st_size,'sha256':h.hexdigest()}\nprint(json.dumps({'files':files,'run_id':'7d3f8947-e1f1-43f7-9621-e304afd2d07e'}))\n"""
 result=call(['ssh',HOST,'python -'],input=remote,timeout=180);manifest=json.loads(next(x for x in reversed(result.stdout.splitlines()) if x.startswith('{')));save(R/'remote-file-manifest.json',manifest)
 outlog=(R/'readout.log').open('w');evalproc=subprocess.Popen(['/Users/adeliyaleleytner/.cache/cyp-inhibition/venv/bin/python',str(R/'readout.py'),'--results',str(small),'--stage',str(R/'stage'),'--output',str(R/'readout'),'--bootstrap','1000'],stdout=outlog,stderr=outlog,start_new_session=True)
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
 assert not bad,bad;assert sum(x.endswith('.ckpt') for x in manifest['files'])==20;assert sum(x.endswith('selected-model.pt') for x in manifest['files'])==20
 save(R/'RECOVERY_CERTIFICATE.json',{'utc':utc(),'status':'PASS','run_id':RUN,'checkpoint_count':20,'file_count':len(manifest['files']),'bytes':sum(x['bytes'] for x in manifest['files'].values()),'remote_manifest_sha256':sha(R/'remote-file-manifest.json'),'errors':[]})
 # Earlier smoke/invalid outcomes must also be preserved before destroying the lease.
 for scope in ['smoke-results','invalid-eval-mode-fc0ad05e']:
  dest=R/'recovered'/scope;dest.mkdir(parents=True,exist_ok=True)
  call(['rsync','-az','--partial',HOST+':/workspace/p10/'+scope+'/',str(dest)+'/'],timeout=1200)
  code="import json,hashlib;from pathlib import Path;r=Path('/workspace/p10/"+scope+"');print(json.dumps({str(p.relative_to(r)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in r.rglob('*') if p.is_file()}))"
  q=call(['ssh',HOST,'python -'],input=code,timeout=180);files=json.loads(next(x for x in q.stdout.splitlines() if x.startswith('{')));save(R/(scope+'-remote-manifest.json'),files)
  assert all((dest/k).stat().st_size==v['bytes'] and sha(dest/k)==v['sha256'] for k,v in files.items())
  save(R/(scope+'-RECOVERY_CERTIFICATE.json'),{'status':'PASS','files':len(files),'all_bytes_sha_verified':True,'scientifically_invalid':scope.startswith('invalid')})
 code=evalproc.wait(timeout=1200);outlog.close();save(C/'READOUT_EXIT.json',{'exit_code':code,'repair_locally_if_nonzero':True})
 spec=importlib.util.spec_from_file_location('lease_control',C/'lease_control.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);lease=json.loads(LEASE.read_text());lease['all_artifacts_hash_verified']=True;mod.save(LEASE,lease);receipt=mod.destroy_verified(LEASE,57884190);save(C/'FINAL_TEARDOWN.json',receipt)
 processes=json.loads((C/'processes-57884190.json').read_text());pid=processes['keepawake_pid'];command=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout.strip().split()
 if command and os.path.basename(command[0])=='caffeinate':os.kill(pid,signal.SIGTERM)
 statuspath=ROOT/'STATUS.json';status=json.loads(statuspath.read_text());status['recovery']={'scope':'P10 fullresults only','path':'p10/recovered/full-results','hash_verification_pending':False,'copied_jobs':20,'all_bytes_verified':True,'certificate':'p10/RECOVERY_CERTIFICATE.json'};status.update(updated_utc=utc(),phase=('P10 full20 complete, readout verified, all20 checkpoints hashverified, ownedlease destroyed' if code==0 else 'P10 full20 evidence recovered, ownedlease destroyed; local readout repair required'),active_run_id=None,completed_P10_run_id=RUN,instance_status='destroyed',paid_instances_active=False,resource_cleanup_verified=True,guard_process_status='exiting_or_exited',recovery_process_status='complete',keepawake_process_status='terminated',worker_status={'scope':'P10 full20','completed_jobs':20,'complete':True},P10_readout='p10/readout/READOUT.json',P10_recovery_certificate='p10/RECOVERY_CERTIFICATE.json',P10_teardown='p10/compute/FINAL_TEARDOWN.json',next_authorized='Independent peer rescore, private result interpretation and actual billing reconciliation. No further fit/lease/publication authorized by this child.');save(statuspath,status)
 save(C/'FINISH_COMPLETE.json',{'utc':utc(),'status':'complete' if code==0 else 'recovered_readout_repair_needed','readout_sha256':sha(R/'readout/READOUT.json') if (R/'readout/READOUT.json').exists() else None,'recovery_sha256':sha(R/'RECOVERY_CERTIFICATE.json'),'teardown_verified':True});print('P10_FINISH_COMPLETE',flush=True)
except Exception as e:
 save(C/'FINISH_ERROR.json',{'utc':utc(),'type':type(e).__name__,'message':str(e)[:2000],'no_automatic_relaunch':True});raise
