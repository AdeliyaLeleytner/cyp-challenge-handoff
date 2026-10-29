#!/usr/bin/env python3
"""One due, serialized curl batch; successful trial enables curl-only continuation."""
import argparse,json,time
from pathlib import Path
from collect import Collector,StopRun,read,save,now
from direct_http import Direct
from scheduled_queue import ROOT,INPUT,BASE_WAIT,initialize,timestamp,iso,merge_all,guard_uncached_batch
from chrome_routed import check_route

class RecordedDirect(Direct):
 def request(self,i,url,payload=None):
  if payload is not None:
   self.c.set_state(i,submitted_at=now(),submission_mode='curl_direct_wifi',transport='curl_interface_en0')
  return super().request(i,url,payload)

def run_once(c):
 schedule=initialize(c);control=read(ROOT/'curl-control.json',{})
 if control.get('mode') not in ('awaiting_trial','curl_only'):raise StopRun('Curl continuation is not enabled')
 if schedule.get('status') in ('needs_attention','complete'):return {'status':schedule['status']}
 pending=[i for i in range(len(c.batches)) if not c.completed(i)]
 if not pending:
  report=merge_all(c);schedule['status']='complete';save(ROOT/'schedule.json',schedule)
  control['mode']='complete';save(ROOT/'curl-control.json',control);return report
 i=pending[0];state=c.state(i)
 until=max(timestamp(schedule['next_allowed_at']),state.get('retry_not_before') or 0)
 if time.time()<until:return {'status':'waiting','next_allowed_at':iso(until),'seconds_remaining':until-time.time(),'batch':i+1}
 if state['phase'] not in ('pending','rate_limited','result_ready'):
  raise StopRun('Uncertain submission or invalid result: do not repeat POST')
 if state['phase']=='result_ready' and not state.get('result_url'):raise StopRun('Missing saved result URL')
 if control['mode']=='awaiting_trial' and i+1!=control['trial_batch']:raise StopRun('Trial batch changed unexpectedly')
 if not state.get('result_url'):guard_uncached_batch(c,i)
 save(c.folder(i)/'curl-route-check.json',check_route())
 attempt=int(state.get('attempt',0))+1
 save(c.folder(i)/f'pre-curl-attempt-{attempt:03}.json',state)
 c.set_state(i,phase='result_ready' if state.get('result_url') else 'pending',attempt=attempt,error=None)
 c.emit('curl_batch_start',batch=i+1,mode=control['mode'],cooldown_satisfied=True)
 try:
  RecordedDirect(c).process(i)
 except Exception as exc:
  current=c.state(i)
  if current['phase']=='rate_limited':
   n=int(schedule.get('consecutive_429',0))+1
   wait=min(21600,BASE_WAIT*(2**min(n,6)))
   until=max(time.time()+wait,current.get('retry_not_before') or 0)
   c.set_state(i,retry_not_before=until,error=str(exc))
   schedule.update(consecutive_429=n,next_allowed_at=iso(until),last_rejection_at=now())
   if control['mode']=='awaiting_trial':
    control.update(mode='trial_failed',error=str(exc),trial_finished_at=now());schedule['status']='needs_attention'
   save(ROOT/'schedule.json',schedule);save(ROOT/'curl-control.json',control)
   return {'status':'trial_failed' if control['mode']=='trial_failed' else 'rate_limited','batch':i+1,'next_allowed_at':iso(until),'error':str(exc)}
  control.update(last_error=str(exc),error_at=now());save(ROOT/'curl-control.json',control)
  schedule['status']='needs_attention';save(ROOT/'schedule.json',schedule)
  raise
 if not c.completed(i):raise StopRun('Batch did not complete')
 schedule.update(consecutive_429=0,last_success_at=now(),next_allowed_at=iso(time.time()+BASE_WAIT),status='active')
 control.update(mode='curl_only',last_successful_batch=i+1,last_success_at=now())
 if not control.get('trial_success_at'):control['trial_success_at']=now()
 if all(c.completed(j) for j in range(len(c.batches))):schedule['status']='complete';control['mode']='complete'
 save(ROOT/'schedule.json',schedule);save(ROOT/'curl-control.json',control)
 report=merge_all(c)
 return {'status':'complete' if control['mode']=='complete' else 'batch_complete','batch':i+1,'next_allowed_at':schedule['next_allowed_at'],'collection':report}

def main():
 p=argparse.ArgumentParser();p.add_argument('--status',action='store_true');a=p.parse_args()
 c=Collector(INPUT,ROOT,500)
 try:
  if a.status:print(json.dumps({'control':read(ROOT/'curl-control.json'),'schedule':read(ROOT/'schedule.json'),'collection':c.status()},indent=2));return
  outcome=run_once(c);save(ROOT/'last-curl-outcome.json',{'utc':now(),**outcome});print(json.dumps(outcome,indent=2))
 finally:c.close()
if __name__=='__main__':main()
