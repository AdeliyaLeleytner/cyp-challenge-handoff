"""Bounded serial collection: paced HTTP requests, new sessions, exact deduplication."""
import argparse,csv,json,time,datetime as dt
from pathlib import Path
from collect import Collector,StopRun,read,save,now
from scheduled_queue import ROOT,INPUT,merge_all
from shifter_transport import ShifterDirect

class Gate:
 def __init__(self):self.last_start=0;self.requests=0;self.posts=0;self.times=[]
 def enter(self,is_post):
  if self.requests>=24:raise StopRun('Bounded test request budget reached')
  time.sleep(max(0,4-(time.monotonic()-self.last_start)))
  self.last_start=time.monotonic();self.requests+=1;self.posts+=int(is_post)
  self.times.append({'utc':now(),'monotonic':self.last_start,'method':'POST' if is_post else 'GET'})
class Paced(ShifterDirect):
 def __init__(self,c,gate):super().__init__(c,rotate_per_request=True);self.gate=gate
 def request(self,i,url,payload=None):
  self.gate.enter(payload is not None)
  previous=self.timeout
  self.timeout=previous if payload is not None else 30
  try:return super().request(i,url,payload)
  finally:self.timeout=previous

def main():
 p=argparse.ArgumentParser();p.add_argument('--max-posts',type=int,default=5);p.add_argument('--max-successes',type=int,default=2);a=p.parse_args()
 if not 1<=a.max_posts<=5 or not 1<=a.max_successes<=2:p.error('Initial diagnostic run is bounded to5 POSTs and2 successes')
 main=Collector(INPUT,ROOT,500);gate=Gate();success=0;rejections=0;stop='budget_complete';folders=[]
 stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S')
 logfile=ROOT/('paced-run-'+stamp+'.json');pc=None
 try:
  merge_all(main)
  while gate.posts<a.max_posts and success<a.max_successes and gate.requests<24:
   if pc is None:
    with (ROOT/'results/remaining-unlabeled.csv').open(newline='') as f:remaining=list(csv.DictReader(f))
    if not remaining:stop='collection_complete';break
    folder=ROOT/'probes'/f'shifter-paced-{stamp}-batch{success+1:03}'
    folder.mkdir(exist_ok=False);source=folder/'input.csv'
    with source.open('w',newline='') as f:
     w=csv.DictWriter(f,fieldnames=['request_id','SMILES','priority']);w.writeheader();w.writerows(remaining[:10])
    folders.append(str(folder));pc=Collector(source,folder/'run',500)
    save(folder/'probe-plan.json',{'utc':now(),'rows':len(pc.rows),'overlap_with_collected':0,'minimum_http_start_interval_seconds':4,'fresh_session_every_request':True,'authorization':'User requested paced rotating requests, same set until successful result; bounded initial run'})
   state=pc.state(0)
   if state['phase']=='rate_limited':
    until=state.get('retry_not_before') or 0
    if until>time.time():stop='server_retry_after';break
    pc.set_state(0,phase='result_ready' if state.get('result_url') else 'pending')
   try:Paced(pc,gate).process(0)
   except Exception as exc:
    state=pc.state(0)
    if state['phase']=='rate_limited':
     rejections+=1;print(json.dumps({'event':'retry_same_batch','posts':gate.posts,'requests':gate.requests,'error':'HTTP429'}),flush=True)
     continue
    if state['phase']=='pending' and gate.requests<24:
     print(json.dumps({'event':'get_failed_no_post','error':str(exc)}),flush=True);continue
    stop='uncertain_or_error';save(pc.folder(0)/'stopped.json',{'utc':now(),'error':str(exc),'state':state});break
   if not pc.completed(0):stop='not_complete';break
   success+=1;pc.close();pc=None
   merged=merge_all(main);print(json.dumps({'event':'validated_success','successful_batches':success,'total_rows':merged['rows']}),flush=True)
 finally:
  if pc:pc.close()
  gaps=[b['monotonic']-a['monotonic'] for a,b in zip(gate.times,gate.times[1:])]
  report={'utc':now(),'posts':gate.posts,'requests':gate.requests,'successful_batches':success,'rejections':rejections,'stop':stop,'min_http_start_gap_seconds':min(gaps) if gaps else None,'folders':folders,'request_times':gate.times}
  save(logfile,report);main.close();print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
