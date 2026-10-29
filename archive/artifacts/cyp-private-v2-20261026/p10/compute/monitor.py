import json,time,subprocess,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[2];L=R/'p10/compute/lease-57884190.json'
remote="""import glob,json,os,time
r='/workspace/p10/full-results';done=[];active=[]
for p in glob.glob(r+'/*.log'):
 n=os.path.basename(p)[:-4];c=r+'/'+n+'/complete.json'
 if os.path.exists(c):done.append(n)
 else:
  lines=open(p).read().splitlines();e=[json.loads(x) for x in lines if x.startswith('{') and 'epoch_timing' in x];v=[json.loads(x) for x in lines if x.startswith('{') and 'checkpoint_metric' in x];active.append({'job':n,'epoch':e[-1]['continuation_epoch'] if e else None,'validation_STRAE':v[-1]['primary_strae'] if v else None,'error':any('Traceback' in x for x in lines)})
print(json.dumps({'observed_unix':time.time(),'scope':'P10 full20','done':done,'active':active,'complete':os.path.exists(r+'/complete.json')}))
"""
while True:
 if json.loads(L.read_text())['status'] in ['destroyed','budget_stopped']:break
 try:
  q=subprocess.run(['ssh','cyp-private-p10-57884190','python -'],input=remote,capture_output=True,text=True,timeout=40);q.check_returncode();d=json.loads(next(x for x in reversed(q.stdout.splitlines()) if x.startswith('{')));(R/'p10/current-progress.json').write_text(json.dumps(d,indent=2)+'\n')
  p=R/'STATUS.json';s=json.loads(p.read_text());s['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();s['worker_status']=d;s['P10_current_progress']=d
  ledger=R/'p10/recovery-progress.jsonl';success={}
  if ledger.exists():
   for line in ledger.read_text().splitlines():
    row=json.loads(line)
    if row.get('exit_code')==0:success[row['job']]=row
  local=R/'p10/recovered/full-results';size=sum(q.stat().st_size for q in local.rglob('*') if q.is_file())
  s['recovery']={'scope':'P10 fullresults only','path':'p10/recovered/full-results','hash_verification_pending':True,'copied_jobs':len(success),'copied_job_names':sorted(success),'local_bytes_including_partial':size,'last_success_utc':max(row['utc'] for row in success.values()) if success else None,'successful_transfer_seconds':[row['seconds'] for row in success.values()]}
  p.write_text(json.dumps(s,indent=2)+'\n')
  if d['complete']:break
 except Exception as e:
  (R/'p10/compute/monitor-last-error.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'error_type':type(e).__name__,'message':str(e)[:200]}))
 time.sleep(45)
