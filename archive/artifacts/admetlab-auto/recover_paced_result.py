import sys,time
from pathlib import Path
from collect import Collector,StopRun,save,now
from scheduled_queue import ROOT,INPUT,merge_all
from paced_shifter_probe import Gate,Paced
class DownloadOnly(Paced):
 def request(self,i,url,payload=None):
  if payload is not None:raise StopRun('Recovery must never POST')
  return super().request(i,url,payload)
folder=Path(sys.argv[1]);main=Collector(INPUT,ROOT,500);pc=Collector(folder/'input.csv',folder/'run',500);gate=Gate();done=False
try:
 for attempt in range(3):
  state=pc.state(0)
  if not state.get('result_url'):raise StopRun('No known result URL')
  if state.get('retry_not_before',0) and state['retry_not_before']>time.time():raise StopRun('Server Retry-After still active')
  if state['phase']=='rate_limited':pc.set_state(0,phase='result_ready')
  try:DownloadOnly(pc,gate).process(0)
  except Exception as exc:
   print({'download_attempt':attempt+1,'error':str(exc)},flush=True)
   if pc.state(0)['phase']=='invalid_result':raise
   continue
  done=pc.completed(0)
  if done:break
 save(folder/'download-recovery.json',{'utc':now(),'success':done,'requests':gate.requests,'posts':gate.posts})
finally:pc.close()
try:
 if done:print(merge_all(main),flush=True)
 else:raise StopRun('Saved result not yet downloaded; no POST repeated')
finally:main.close()
