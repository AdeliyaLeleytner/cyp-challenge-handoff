#!/usr/bin/env python3
"""Persistent timing and integrity guard for the ADMETlab Chrome heartbeat.
No network submissions or UI actions: browser actions are performed by the agent.
"""
import argparse,csv,datetime as dt,hashlib,json,shutil,time
from pathlib import Path
from urllib.parse import urlsplit
from collect import Collector,StopRun,read,save,sha,now,retry_time
from parsing import parse_batch
from chrome_routed import check_route
SCRIPT=Path(__file__).resolve().parent
ROOT=Path.home()/'Downloads/ADMETlab-Chrome-direct-500'
INPUT=SCRIPT/'../../cyp-admet500-pilot-20261025/next-official-5155.csv'
BASE_WAIT=600

def timestamp(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def iso(t):return dt.datetime.fromtimestamp(t,dt.timezone.utc).isoformat()
def initialize(c):
 p=ROOT/'schedule.json';state=read(p)
 if state:return state
 latest=max([timestamp(c.state(i)['updated_utc']) for i in range(len(c.batches)) if c.completed(i)] or [time.time()])
 state={'status':'active','base_cooldown_seconds':BASE_WAIT,'next_allowed_at':iso(latest+BASE_WAIT),'consecutive_429':0,'last_success_at':iso(latest),'policy':'Normal browser clicks in existing Chrome. Ten minutes after successful download. On consecutive HTTP429 wait 20,40,80,160,320 minutes, capped at six hours; honor longer Retry-After. Never repeat an uncertain POST.'}
 save(p,state);return state

def guard_uncached_batch(c,i):
 p=ROOT/'results/all-collected.csv'
 if not p.exists():return
 with p.open(encoding='utf-8-sig',newline='') as f:known={row['raw_smiles'] for row in csv.DictReader(f)}
 overlap=[row['SMILES'] for row in c.batches[i] if row['SMILES'] in known]
 if overlap:raise StopRun(f'Batch contains {len(overlap)} already labeled molecules. Rebuild pending batches from results/remaining-unlabeled.csv before submitting.')

def merge_all(c):
 c.merge()
 original=ROOT/'original-500.csv'
 if not original.exists():
  source=Path.home()/'Downloads/ADMETLab3_e01f3a5de8fd1b871792938651.csv'
  shutil.copy2(source,original)
 files=[original]+[c.folder(i)/'result.csv' for i in range(len(c.batches)) if c.completed(i)]
 # Include only independently validated, completed size probes.
 for run in sorted((ROOT/'probes').glob('*/run')):
  source=run.parent/'input.csv'
  if not source.exists() or not (run/'plan.json').exists():continue
  probe=Collector(source,run,500)
  try:
   for j in range(len(probe.batches)):
    if probe.completed(j):
     probe.validate(j);files.append(probe.folder(j)/'result.csv')
  finally:probe.close()
 raw=[];seen=set();fields=None;inputs=[]
 for p in files:
  with p.open(encoding='utf-8-sig',newline='') as f:
   reader=csv.DictReader(f)
   if fields is None:fields=reader.fieldnames
   if set(fields)!=set(reader.fieldnames):raise StopRun('Inconsistent endpoint columns')
   for row in reader:
    smi=row['raw_smiles']
    if smi in seen:raise StopRun('Duplicate raw_smiles in merged collection')
    seen.add(smi);raw.append(row)
    inputs.append({'SMILES':smi,'request_id':hashlib.sha256(smi.encode()).hexdigest(),'priority':'0'})
 results=ROOT/'results';results.mkdir(exist_ok=True)
 p=results/'all-collected.csv';tmp=p.with_suffix('.csv.tmp')
 with tmp.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(raw)
 parsed,failed,audit=parse_batch(tmp.read_bytes(),inputs,c.schema,'combined-web-default')
 if failed:raise StopRun('Combined collection failed validation')
 tmp.replace(p)
 feature_names=sorted({k for row in parsed for k in row['features']})
 feature_path=results/'all-collected-features.csv';tmp=feature_path.with_suffix('.csv.tmp')
 with tmp.open('w',newline='') as f:
  names=['request_id','SMILES','service_smiles']+feature_names
  w=csv.DictWriter(f,fieldnames=names);w.writeheader()
  for row in parsed:w.writerow({**{k:row[k] for k in names[:3]},**row['features']})
 tmp.replace(feature_path)
 scope=read(ROOT/'acquisition-scope.json',{})
 official={row['SMILES'] for row in c.rows}
 with original.open(encoding='utf-8-sig',newline='') as f:official.update(row['raw_smiles'] for row in csv.DictReader(f))
 if scope.get('pool_csv'):
  pool_path=Path(scope['pool_csv'])
  if sha(pool_path)!=scope['pool_sha256']:raise StopRun('Full pool source hash changed')
  with pool_path.open(encoding='utf-8-sig',newline='') as f:pool=list(csv.DictReader(f))
  if len(pool)!=scope['pool_size'] or len({row['SMILES'] for row in pool})!=len(pool):raise StopRun('Invalid full pool size/uniqueness')
  if any(hashlib.sha256(row['SMILES'].encode()).hexdigest()!=row['request_id'] for row in pool):raise StopRun('Full pool request hash mismatch')
  pool.sort(key=lambda row:(row['SMILES'] not in official,int(row.get('priority') or 0)))
 else:
  pool=list(c.rows)
  with original.open(encoding='utf-8-sig',newline='') as f:
   pool.extend({'request_id':hashlib.sha256(row['raw_smiles'].encode()).hexdigest(),'SMILES':row['raw_smiles'],'priority':'0'} for row in csv.DictReader(f))
 pool_smiles={row['SMILES'] for row in pool}
 if not seen<=pool_smiles:raise StopRun('Collected molecules outside the acquisition pool')
 remaining=[row for row in pool if row['SMILES'] not in seen]
 with (results/'remaining-unlabeled.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['request_id','SMILES','priority']);w.writeheader();w.writerows(remaining)
 if len(remaining)!=len(pool)-len(raw):raise StopRun('Pool coverage mismatch')
 report={'utc':now(),'rows':len(raw),'pool_size':len(pool),'remaining_total':len(pool)-len(raw),'official_rows':len(official&seen),'remaining_official':len(official-seen),'raw_csv':str(p),'features_csv':str(feature_path),'endpoint_columns':len(fields)-2,'feature_columns':len(feature_names),'raw_csv_sha256':sha(p),'features_sha256':sha(feature_path),'inputs':[{'path':str(f),'sha256':sha(f)} for f in files],'source_mode':'web_default'}
 save(results/'all-collected-manifest.json',report);return report

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('action',choices=['status','check-route','begin','reject','result','adopt','merge'])
 p.add_argument('--batch',type=int);p.add_argument('--csv',type=Path);p.add_argument('--url');p.add_argument('--retry-after')
 a=p.parse_args();c=Collector(INPUT,ROOT,500)
 try:
  schedule=initialize(c);todo=[i for i in range(len(c.batches)) if not c.completed(i)]
  if not todo:
   schedule['status']='complete';save(ROOT/'schedule.json',schedule)
  if a.action=='status':
   if todo:
    i=todo[0];state=c.state(i)
    result={'batch':i+1,'batch_state':state,'smiles_path':str(c.folder(i)/'smiles.txt'),'rows':len(c.batches[i]),'seconds_until_allowed':max(0,timestamp(schedule['next_allowed_at'])-time.time()),'can_submit':state['phase'] in ('pending','rate_limited') and not state.get('result_url') and time.time()>=timestamp(schedule['next_allowed_at'])}
   else:result={'all_batches_complete':True}
   print(json.dumps({'schedule':schedule,'collection':c.status(),**result},indent=2))
  elif a.action=='check-route':print(json.dumps(check_route(),indent=2))
  elif a.action=='merge':print(json.dumps(merge_all(c),indent=2))
  else:
   if a.batch is None or not todo or a.batch-1!=todo[0]:raise StopRun('Must operate on the first incomplete batch')
   i=a.batch-1;state=c.state(i)
   if a.action=='begin':
    if state['phase'] not in ('pending','rate_limited') or state.get('result_url'):raise StopRun('Uncertain or already accepted POST must not be repeated')
    if time.time()<timestamp(schedule['next_allowed_at']):raise StopRun('Cooldown not finished')
    if state.get('retry_not_before') and time.time()<state['retry_not_before']:raise StopRun('Retry-After not finished')
    guard_uncached_batch(c,i)
    route=check_route();c.payload(i)
    attempt=int(state.get('attempt',0))+1
    save(c.folder(i)/f'pre-attempt-{attempt:03}.json',state)
    save(c.folder(i)/f'route-attempt-{attempt:03}.json',route)
    c.set_state(i,phase='submitting',attempt=attempt,submitted_at=now(),submission_mode='normal_browser_click_after_cooldown',error=None)
   elif a.action=='reject':
    if state['phase'] not in ('submitting','uncertain','result_ready'):raise StopRun('No in-flight submission or result download to reject')
    failures=int(schedule.get('consecutive_429',0))+1
    wait=min(21600,BASE_WAIT*(2**min(failures,6)))
    until=max(time.time()+wait,retry_time(a.retry_after) or 0)
    c.set_state(i,phase='rate_limited',http_status=429,error='HTTP429',retry_not_before=until,retry_after=a.retry_after)
    schedule.update(consecutive_429=failures,next_allowed_at=iso(until),last_rejection_at=now())
    save(ROOT/'schedule.json',schedule)
   elif a.action=='result':
    if not a.url or not c.result_url(a.url):raise StopRun('Invalid result URL')
    c.set_state(i,phase='result_ready',result_url=a.url)
   elif a.action=='adopt':
    url=a.url or state.get('result_url')
    if not a.csv or not url or not c.result_url(url):raise StopRun('CSV and valid result URL required')
    c.validate(i,a.csv)
    dest=c.folder(i)/'result.csv'
    if a.csv.resolve()!=dest.resolve():shutil.copy2(a.csv,dest)
    save(c.folder(i)/'download.json',{'sha256':sha(dest),'result_url':url,'download_url':url+'/download/csv','utc':now(),'acquisition':'Chrome download, exact raw_smiles verified'})
    c.adopt_download(i)
    schedule.update(consecutive_429=0,last_success_at=now(),next_allowed_at=iso(time.time()+BASE_WAIT),status='complete' if all(c.completed(j) for j in range(len(c.batches))) else 'active')
    save(ROOT/'schedule.json',schedule)
    print(json.dumps(merge_all(c),indent=2))
   print(json.dumps({'schedule':schedule,'batch_state':c.state(i)},indent=2))
 finally:c.close()

if __name__=="__main__":main()
