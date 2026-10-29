"""Read checkpoint epoch metadata without deserializing model code."""
from pathlib import Path
import subprocess,json,datetime
ROOT=Path(__file__).resolve().parent
code='''from pathlib import Path
import json,zipfile,pickletools,time
root=Path("/workspace/cyp-strict-reference/output");rows=[]
def scalar(data,key):
 iterator=iter(pickletools.genops(data))
 for op,arg,pos in iterator:
  if arg==key:
   for op,arg,pos in iterator:
    if op.name in ("MEMOIZE","BINPUT","LONG_BINPUT","PUT"):continue
    return arg if op.name in ("BININT","BININT1","BININT2","LONG1","LONG4","INT","LONG") else None
 return None
for cohort in ["own750","briford529"]:
 for member in ["union18","2d6isoform6"]:
  for fold in range(5):
   d=root/cohort/"results"/member/("fold"+str(fold));row={"cohort":cohort,"member":member,"fold":fold,"complete":(d/"complete.json").exists()}
   p=next(iter(d.glob("checkpoints/*.ckpt")),None)
   if p:
    try:
     with zipfile.ZipFile(p) as z:data=z.read(next(n for n in z.namelist() if n.endswith("/data.pkl")))
     row.update(best_epoch=scalar(data,"epoch"),global_step_at_best=scalar(data,"global_step"),checkpoint_age_seconds=round(time.time()-p.stat().st_mtime))
    except (zipfile.BadZipFile,StopIteration,EOFError):row["checkpoint_read_raced_update"]=True
   if row["complete"]:row["fit_seconds"]=json.loads((d/"metadata.json").read_text())["seconds"]
   rows.append(row)
print(json.dumps(rows))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','cyp-strict-ref-57740054','python','-'],input=code,text=True,capture_output=True,timeout=60,check=True)
rows=json.loads(r.stdout.strip().splitlines()[-1]);report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'completed':sum(r['complete'] for r in rows),'checkpointed':sum('best_epoch' in r for r in rows),'folds':rows}
(ROOT/'training-progress.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
