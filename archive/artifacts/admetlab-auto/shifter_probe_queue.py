"""Run the requested50/100 molecule tests through Shifter, one due batch per call."""
import csv,json,time
from pathlib import Path
from collect import Collector,StopRun,read,save,now,sha
from scheduled_queue import ROOT,INPUT,merge_all,timestamp,iso
from shifter_transport import ShifterDirect

def main():
 c=Collector(INPUT,ROOT,500)
 try:
  control=read(ROOT/'shifter-tests.json')
  if control['status']!='active':print(json.dumps(control,indent=2));return
  until=timestamp(control['next_allowed_at'])
  if time.time()<until:print(json.dumps({'status':'waiting','next_allowed_at':control['next_allowed_at']}));return
  size=control['sizes'][control['index']]
  report=merge_all(c)
  with (ROOT/'results/remaining-unlabeled.csv').open(newline='') as f:remaining=list(csv.DictReader(f))
  folder=ROOT/'probes'/f'shifter-{size}-20261025';folder.mkdir(exist_ok=True)
  source=folder/'input.csv'
  if not source.exists():
   rows=remaining[:size]
   if len(rows)!=size:raise StopRun('Not enough remaining molecules')
   with source.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['request_id','SMILES','priority']);w.writeheader();w.writerows(rows)
   save(folder/'probe-plan.json',{'utc':now(),'rows':size,'source_mode':'web_default','input_sha256':sha(source),'transport':'Shifter curl, one sticky session, no parallel jobs','overlap_with_collected':0})
  with source.open(newline='') as f:rows=list(csv.DictReader(f))
  known={r['SMILES'] for r in remaining}
  pc=Collector(source,folder/'run',500)
  try:
   state=pc.state(0)
   if pc.completed(0):pass
   elif state['phase'] not in ('pending','result_ready'):raise StopRun('Saved probe is rejected or uncertain; do not automatically resubmit')
   else:
    if any(r['SMILES'] not in known for r in rows):raise StopRun('Probe overlaps previously collected molecules')
    save(folder/'started.json',{'utc':now(),'rows':size,'cooldown_satisfied':True})
    ShifterDirect(pc,session=control.get('session_for_'+str(size),f'cypprobe{size}20261025')).process(0)
  except Exception as e:
   control.update(status='needs_attention',error=str(e),failed_size=size,failed_at=now())
   save(ROOT/'shifter-tests.json',control);raise
  finally:pc.close()
  merged=merge_all(c)
  control['index']+=1;control.update(last_success_at=now(),next_allowed_at=iso(time.time()+600),last_successful_size=size)
  if control['index']==len(control['sizes']):control['status']='complete'
  save(ROOT/'shifter-tests.json',control)
  print(json.dumps({'control':control,'collection':merged},indent=2))
 finally:c.close()
if __name__=='__main__':main()
