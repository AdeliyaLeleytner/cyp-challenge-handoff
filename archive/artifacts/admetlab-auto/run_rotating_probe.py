"""User-authorized curl probe with a distinct Shifter session per HTTP request."""
import argparse,csv
from pathlib import Path
from collect import Collector,save,read,now,StopRun
from scheduled_queue import ROOT,INPUT,merge_all
from shifter_transport import ShifterDirect
p=argparse.ArgumentParser();p.add_argument('--size',type=int,choices=[10,50,100],required=True);p.add_argument('--tag',default='20261025');a=p.parse_args()
main=Collector(INPUT,ROOT,500)
try:
 report=merge_all(main)
 if a.size==100:
  gate=ROOT/'probes/shifter-rotating-50-20261025/run/results/complete.json'
  if not gate.exists():raise StopRun('50 must succeed before100')
 with (ROOT/'results/remaining-unlabeled.csv').open(newline='') as f:remaining=list(csv.DictReader(f))
 if not a.tag.isdigit() or len(a.tag)!=8:raise StopRun('Run tag must be YYYYMMDD')
 folder=ROOT/'probes'/f'shifter-rotating-{a.size}-{a.tag}'
 folder.mkdir(exist_ok=True);source=folder/'input.csv'
 if not source.exists():
  with source.open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['request_id','SMILES','priority']);w.writeheader();w.writerows(remaining[:a.size])
 with source.open(newline='') as f:rows=list(csv.DictReader(f))
 assert len(rows)==a.size
 known={r['SMILES'] for r in remaining}
 pc=Collector(source,folder/'run',500)
 try:
  if not pc.completed(0):
   if any(r['SMILES'] not in known for r in rows):raise StopRun('Already labeled molecule in probe')
   save(folder/'probe-plan.json',{'utc':now(),'rows':a.size,'overlap_with_collected':0,'session_policy':'New Shifter sid for each HTTP request, explicit user request. Same cookie jar preserves form CSRF.','main_queue_remains_paused':True})
   ShifterDirect(pc,rotate_per_request=True).process(0)
 finally:pc.close()
 print(merge_all(main))
finally:main.close()
