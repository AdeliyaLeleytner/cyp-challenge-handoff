"""Task-owned lease lifecycle: immutable instance binding and readback verification."""
import argparse,json,subprocess,time,datetime,os
from pathlib import Path
SCOPE='cyp-private-v2-p8c-20261026'
def call(args):return subprocess.run(['vastai',*args],capture_output=True,text=True,timeout=60)
def save(path,obj):
 p=Path(path);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2)+'\n');os.replace(tmp,p)
def bound(path,instance):
 p=Path(path);s=json.loads(p.read_text());assert p.name==f'lease-{instance}.json' and s['instance_id']==instance and s['scope']==SCOPE;return s

def listing(run=call):
 p=run(['show','instances','--raw'])
 if p.returncode:raise RuntimeError('Instance readback failed')
 rows=json.loads(p.stdout);assert isinstance(rows,list);return rows

def destroy_verified(path,instance,run=call):
 s=bound(path,instance);assert s.get('no_training_started') or s.get('all_artifacts_hash_verified'), 'Destructive teardown blocked until artifacts recoverable'
 before=listing(run);p=run(['destroy','instance',str(instance),'--yes','--raw']);after=listing(run)
 receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'instance_id':instance,'action':'destroy --yes','command_exit_code':p.returncode,'target_absent':all(x['id']!=instance for x in after),'unrelated_before':[x['id'] for x in before if x['id']!=instance],'unrelated_after':[x['id'] for x in after if x['id']!=instance]}
 save(Path(path).with_name(f'destroy-readback-{instance}-{int(time.time())}.json'),receipt)
 if not receipt['target_absent']:raise RuntimeError('Destroy NOT verified: lease and guard remain active')
 s.update(status='destroyed',destroyed_unix=time.time(),teardown_verified=True);save(path,s);return receipt

def guard(path,instance,run=call):
 while True:
  s=bound(path,instance)
  if s['status']=='destroyed':return
  if time.time()>=s['deadline_unix']:
   try:
    p=run(['stop','instance',str(instance),'--raw']);rows=listing(run);target=next((x for x in rows if x['id']==instance),None)
    stopped=target is None or target.get('actual_status') in ['stopped','exited']
    save(Path(path).with_name(f'budget-stop-{instance}.json'),{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'instance_id':instance,'command_exit_code':p.returncode,'actual_status':None if target is None else target.get('actual_status'),'verified_stopped':stopped})
    if stopped:s['status']='budget_stopped';save(path,s);return
   except Exception as e:
    save(Path(path).with_name(f'guard-error-{instance}.json'),{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'error_type':type(e).__name__,'message':str(e)[:500]})
  time.sleep(15)

def selftest():
 import tempfile
 from types import SimpleNamespace
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'lease-123.json';base={'instance_id':123,'scope':SCOPE,'status':'active','no_training_started':True};save(p,base)
  calls=[]
  def aborted(args):
   calls.append(args)
   return SimpleNamespace(returncode=0,stdout=json.dumps([{'id':123},{'id':999}]) if args[:2]==['show','instances'] else 'Aborted.',stderr='')
  try:destroy_verified(p,123,aborted);raise AssertionError('must fail closed')
  except RuntimeError:pass
  assert bound(p,123)['status']=='active' and ['destroy','instance','123','--yes','--raw'] in calls
  count=[0]
  def blank_success(args):
   if args[:2]==['show','instances']:
    count[0]+=1;return SimpleNamespace(returncode=0,stdout=json.dumps([{'id':123},{'id':999}] if count[0]==1 else [{'id':999}]),stderr='')
   return SimpleNamespace(returncode=0,stdout='',stderr='')
  receipt=destroy_verified(p,123,blank_success);assert receipt['target_absent'] and bound(p,123)['status']=='destroyed'
  rejected=False
  try:bound(p,456)
  except AssertionError:rejected=True
  assert rejected, 'wrong lease identity accepted'
  save(p,{**base,'no_training_started':False,'all_artifacts_hash_verified':False})
  try:destroy_verified(p,123,blank_success);raise RuntimeError('unsafe teardown accepted')
  except AssertionError:pass
 print(json.dumps({'offline_tests':'PASS','cases':['aborted exit0 remains active','explicit --yes required','empty stdout plus absence accepted','immutable lease ID binding','unrecovered artifacts block destroy'],'provider_calls':0}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('action',choices=['selftest','guard','destroy']);a.add_argument('--lease',type=Path);a.add_argument('--instance',type=int);v=a.parse_args()
 if v.action=='selftest':selftest()
 elif v.action=='guard':guard(v.lease,v.instance)
 else:print(json.dumps(destroy_verified(v.lease,v.instance)))
