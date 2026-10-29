from pathlib import Path
import os,sys,json,subprocess,time,hashlib
import numpy as np,pandas as pd,torch
ROOT=Path(__file__).resolve().parent;P=ROOT/'prepared';P.mkdir(exist_ok=True);OUT=ROOT/'outputs';OUT.mkdir(exist_ok=True)
from modeling import weight_path
weight_path()
df=pd.read_csv(ROOT/'data/official-train.csv');df.to_csv(P/'challenge.csv',index=False)
cols=[f'{c}_pIC50_direct_inhibition' for c in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
(P/'target-columns.json').write_text(json.dumps({'primary':cols,'all':cols}))
fold=pd.read_csv(ROOT/'data/jeremy-folds.csv');assert fold.Molecule_Name.tolist()==df.Molecule_Name.tolist();f=fold.fold.to_numpy()
roles={}
for i in range(5):roles[f'jeremy_{i}']={'fit':np.flatnonzero(~np.isin(f,[i,(i+1)%5])).tolist(),'val':np.flatnonzero(f==(i+1)%5).tolist(),'test':np.flatnonzero(f==i).tolist()}
idmap={x:i for i,x in enumerate(df.Molecule_Name)}
roles['our_fixed_750']={k:[idmap[x] for x in pd.read_csv(ROOT/f'data/{v}.csv').Molecule_Name] for k,v in [('fit','train'),('val','validation'),('test','holdout')]}
(P/'roles.json').write_text(json.dumps(roles))
print('CORE_PROTOCOL',json.dumps({'config':json.loads((ROOT/'config.json').read_text()),'fold_file_sha256':hashlib.sha256((ROOT/'data/jeremy-folds.csv').read_bytes()).hexdigest(),'initialization_sha':hashlib.sha256(weight_path().read_bytes()).hexdigest()}),flush=True)
assert torch.cuda.device_count()>=5
jobs=[]
for i in range(5):
 env=os.environ.copy();env['CUDA_VISIBLE_DEVICES']=str(i);log=(OUT/f'chemeleon-jeremy_{i}.log').open('w');p=subprocess.Popen([sys.executable,'-u','worker.py','chemeleon',f'jeremy_{i}'],stdout=log,stderr=subprocess.STDOUT,env=env);jobs.append((i,p,log));print('LAUNCHED_CHEMELEON',i,p.pid,flush=True)
log=(OUT/'matched_lgb.log').open('w');p=subprocess.Popen([sys.executable,'-u','matched_lgb.py'],stdout=log,stderr=subprocess.STDOUT);jobs.append(('lgb',p,log))
while jobs:
 for i,p,log in jobs.copy():
  rc=p.poll()
  if rc is not None:
   log.close();print('CORE_FINISHED',i,rc,flush=True);jobs.remove((i,p,log))
   if rc:raise RuntimeError(f'Worker {i} failed')
 if jobs:time.sleep(5)
(OUT/'core-complete.json').write_text(json.dumps({'status':'complete','five_folds':True}));print('CORE_COMPLETE',flush=True)
