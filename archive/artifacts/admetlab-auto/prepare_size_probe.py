"""Prepare a disjoint size probe from the remaining official molecules."""
import argparse,csv
from pathlib import Path
from collect import Collector,StopRun,save,sha,now
from scheduled_queue import ROOT,INPUT,merge_all
p=argparse.ArgumentParser();p.add_argument('size',type=int);a=p.parse_args()
if a.size not in (50,100):raise SystemExit('Only the requested50/100 probes are supported')
c=Collector(INPUT,ROOT,500)
try:
 merge_all(c)
 with (ROOT/'results/remaining-unlabeled.csv').open(newline='') as f:remaining=list(csv.DictReader(f))
 if len(remaining)<a.size:raise StopRun('Not enough unlabeled molecules')
 target=ROOT/'probes'/('curl-'+str(a.size)+'-20261025')
 target.mkdir(exist_ok=False)
 rows=remaining[:a.size]
 if a.size==100:
  gate=ROOT/'probes/curl-50-20261025/run/results/complete.json'
  if not gate.exists():raise StopRun('The50-molecule probe must succeed before100 is submitted')
 with (target/'input.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['request_id','SMILES','priority']);w.writeheader();w.writerows(rows)
 save(target/'probe-plan.json',{'utc':now(),'rows':a.size,'input_sha256':sha(target/'input.csv'),'selection':'First remaining molecules after excluding original500, all completed main batches, and every validated completed probe','overlap_with_collected':0,'main_queue_remains_paused':True})
 print(str(target/'input.csv'))
finally:c.close()
