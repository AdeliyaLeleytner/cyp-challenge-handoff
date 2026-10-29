"""Serial, deduplicated ADMETlab collection with paced proxy submissions."""
import csv,datetime as dt,json,os,time,hashlib
from urllib.parse import urlencode,urljoin
from pathlib import Path
from collect import Collector,StopRun,read,save,sha,now
from direct_http import Direct,Page
from scheduled_queue import ROOT,INPUT,merge_all
from paced_shifter_probe import Gate,Paced

class ContinuousGate(Gate):
 def enter(self,is_post):
  time.sleep(max(0,4-(time.monotonic()-self.last_start)))
  self.last_start=time.monotonic();self.requests+=1;self.posts+=int(is_post)
  # Store totals durably; individual requests are recorded in batch events.

STATE=ROOT/'continuous-state.json'
SETTINGS=ROOT/'worker-settings.json'
def reserved_request_ids():
 record=read(ROOT/'uncertain-submissions.json',{})
 return {key for item in record.get('submissions',[]) if item.get('status')=='unknown_origin_outcome' for key in item.get('reserved_request_ids',[])}

def batch_size():
 size=int(read(SETTINGS,{}).get('batch_size',10))
 if not 1<=size<=500:raise StopRun('Configured batch size must be1..500')
 return size

def promote_after_success(completed_size):
 settings=read(SETTINGS,{})
 ramp=settings.get('ramp',[])
 current=int(settings.get('batch_size',10))
 if not settings.get('auto_increase') or completed_size!=current or current not in ramp:return current
 position=ramp.index(current)
 if position+1<len(ramp):
  new=ramp[position+1]
  save(ROOT/'batch-size-promotions'/('size-'+str(current)+'-to-'+str(new)+'.json'),{'utc':now(),'validated_size':current,'next_size':new})
  settings.update(batch_size=new,updated_utc=now(),last_validated_size=current)
  save(SETTINGS,settings);return new
 return current

def reissue_lost_inference_response(pc):
 settings=read(SETTINGS,{})
 if not settings.get('allow_unknown_response_reissue',False):return False
 state=pc.state(0)
 if state.get('phase')!='submitting' or state.get('result_url'):return False
 records=sorted(pc.folder(0).glob('http-*.json'))
 if not records:return False
 meta=read(records[-1]);uploaded=float(meta.get('uploaded_bytes') or 0)
 if meta.get('method')!='POST' or meta.get('http_status')!=0 or uploaded<=0 or meta.get('curl_exit') not in (28,52,55,56):return False
 count=int(state.get('unknown_reissues',0))
 if count>=int(settings.get('max_unknown_reissues_per_batch',2)):return False
 save(pc.folder(0)/f'unknown-response-{count+1:03}.json',{'utc':now(),'original_outcome':'unknown','may_repeat_server_computation':True,'authorization':'User instructed same set until a result and full-pool labeling; no saved result or result URL exists','state_before':state,'http_evidence':meta})
 pc.set_state(0,phase='pending',unknown_reissues=count+1,prior_unknown_response=True,http_status=0,not_submitted=False,error_stage='response_lost_after_upload')
 return True

def cycle(pc,gate):
 state=pc.state(0)
 if pc.completed(0):return True
 if state.get('retry_not_before') and state['retry_not_before']>time.time():return False
 if state['phase']=='rate_limited':
  pc.set_state(0,phase='result_ready' if state.get('result_url') else 'pending')
  state=pc.state(0)
 if state['phase'] not in ('pending','result_ready'):raise StopRun('Uncertain submission or invalid result; do not repeat POST')
 transport=Paced(pc,gate)
 transport.timeout=int(read(SETTINGS,{}).get('post_timeout_seconds',180))
 result=state.get('result_url')
 if not result:
  cookie=pc.root/'cookies.txt';cached=pc.folder(0)/'prepared-form-urlencoded.txt'
  use_cache=cached.exists() and cookie.exists() and state.get('prepared_cookie_sha256')==sha(cookie)
  if use_cache:payload=cached.read_text()
  else:
   url,body=transport.follow(0,pc.base+'/server/screening')
   page=Page(body.read_text())
   if not page.form or page.form.get('action')!='/server/screeningCal' or page.form.get('method','').lower()!='post' or page.fields.get('method')!='2':raise StopRun('Form contract changed')
   fields=dict(page.fields);fields['smiles-list']=pc.payload(0);payload=urlencode(fields)
   cached.write_text(payload);cached.chmod(0o600)
   pc.set_state(0,prepared_cookie_sha256=sha(cookie) if cookie.exists() else None)
  save(pc.folder(0)/'request-integrity.json',pc.verify_form_request(payload,'application/x-www-form-urlencoded',0))
  attempt=int(state.get('attempt',0))+1
  pc.set_state(0,phase='submitting',attempt=attempt,submitted_at=now())
  status,headers,body=transport.request(0,pc.base+'/server/screeningCal',payload)
  if status not in (302,303) or not headers.get('location'):raise StopRun('Unexpected submission response; do not resubmit')
  result=urljoin(pc.base,headers['location'])
  if not pc.result_url(result):raise StopRun('Unexpected redirect; do not resubmit')
  pc.set_state(0,phase='result_ready',result_url=result)
 # The CSV endpoint is the observed Download CSV route for accepted result IDs.
 # Direct retrieval avoids repeating the prediction when a proxy download fails.
 gate.enter(False)
 csvurl=result.rstrip('/')+'/download/csv'
 status,headers,body=Direct(pc,timeout=45).request(0,csvurl)
 if status!=200:raise StopRun('CSV returned HTTP'+str(status))
 try:pc.validate(0,body)
 except Exception:
  pc.set_state(0,phase='invalid_result');raise
 dest=pc.folder(0)/'result.csv';dest.write_bytes(body.read_bytes())
 save(pc.folder(0)/'download.json',{'utc':now(),'sha256':sha(dest),'result_url':result,'download_url':csvurl,'prediction_transport':'Shifter curl, fresh session each request','download_transport':'direct Wi-Fi; no new calculation'})
 pc.adopt_download(0);pc.set_state(0,error=None,http_status=200)
 return True

def main():
 main=Collector(INPUT,ROOT,500);pc=None;gate=ContinuousGate();start=time.time();stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S')
 state={'status':'running','pid':os.getpid(),'started_at':now(),'max_runtime_seconds':21600,'minimum_http_start_interval_seconds':4,'batch_size':batch_size(),'prediction_transport':'Shifter curl, new session per request','download_transport':'direct Wi-Fi','active_folder':None,'new_molecules_this_run':0,'posts':0,'requests':0}
 state['source_sha256']={name:hashlib.sha256((Path(__file__).resolve().parent/name).read_bytes()).hexdigest() for name in ['continuous_shifter.py','scheduled_queue.py','parsing.py','direct_http.py','shifter_transport.py']}
 prior=read(STATE)
 if prior and prior.get('active_folder'):
  old=read(Path(prior['active_folder'])/'run/batches/001/state.json',{})
  if old.get('phase') in ('submitting','uncertain','result_ready') or (old.get('result_url') and old.get('phase')!='complete'):
   main.close();raise StopRun('Recover the previous accepted or uncertain batch before restarting')
 if prior and prior.get('status') not in ('complete','stopped','needs_attention'):
  main.close();raise StopRun('An existing run needs inspection; not creating another')
 sequence=0;failures=0
 try:
  merged=merge_all(main);state.update(total_collected=merged['rows'],remaining=merged.get('remaining_total',merged['remaining_official']));save(STATE,state)
  while time.time()-start<21600 and gate.posts<1000:
   if pc is None:
    with (ROOT/'results/remaining-unlabeled.csv').open(newline='') as f:remaining=list(csv.DictReader(f))
    reserved=reserved_request_ids();state['reserved_uncertain_molecules']=len(reserved)
    remaining=[row for row in remaining if row['request_id'] not in reserved]
    if not remaining:
     if state.get('remaining',0)>0:state.update(status='needs_attention',last_error='Only reserved uncertain molecules remain; recover or explicitly resolve their original submission')
     else:state['status']='complete'
     break
    size=batch_size();state['batch_size']=size
    sequence+=1;folder=ROOT/'probes'/f'shifter-continuous-{stamp}-{sequence:04}'
    folder.mkdir(exist_ok=False);source=folder/'input.csv'
    with source.open('w',newline='') as f:
     w=csv.DictWriter(f,fieldnames=['request_id','SMILES','priority']);w.writeheader();w.writerows(remaining[:size])
    pc=Collector(source,folder/'run',500)
    save(folder/'probe-plan.json',{'utc':now(),'rows':len(pc.rows),'overlap_with_collected':0,'minimum_http_start_interval_seconds':4,'new_set_only_after_validated_result':True})
    state.update(active_folder=str(folder),current_batch_molecules=len(pc.rows))
   state.update(updated_at=now(),posts=gate.posts,requests=gate.requests);save(STATE,state)
   if pc.state(0).get('retry_not_before') and pc.state(0)['retry_not_before']>time.time():
    time.sleep(min(30,pc.state(0)['retry_not_before']-time.time()));continue
   try:done=cycle(pc,gate)
   except Exception as exc:
    if reissue_lost_inference_response(pc):
     state.update(last_error='Lost inference response recorded; authorized cache-missing batch reissue',last_error_at=now(),posts=gate.posts,requests=gate.requests);save(STATE,state);continue
    phase=pc.state(0)['phase'];failures+=1
    state.update(last_error=str(exc),last_error_at=now(),posts=gate.posts,requests=gate.requests,consecutive_errors=failures)
    if phase in ('submitting','invalid_result') or failures>=30:
     state['status']='needs_attention';save(STATE,state);break
    if phase not in ('pending','rate_limited','result_ready'):
     state['status']='needs_attention';save(STATE,state);break
    save(STATE,state);continue
   if not done:continue
   count=len(pc.rows);pc.close();pc=None;failures=0
   merged=merge_all(main)
   next_size=promote_after_success(count)
   state.update(batch_size=next_size,updated_at=now(),last_success_at=now(),new_molecules_this_run=state['new_molecules_this_run']+count,total_collected=merged['rows'],remaining=merged.get('remaining_total',merged['remaining_official']),active_folder=None,last_error=None,consecutive_errors=0,posts=gate.posts,requests=gate.requests)
   save(STATE,state);print(json.dumps(state),flush=True)
  else:state.update(status='stopped',stop_reason='Six-hour or1000-POST diagnostic budget reached')
 except (Exception,KeyboardInterrupt) as exc:state.update(status='needs_attention',last_error=str(exc),last_error_at=now());raise
 finally:
  if pc:pc.close()
  state.update(updated_at=now(),posts=gate.posts,requests=gate.requests);save(STATE,state);main.close()
if __name__=='__main__':main()
