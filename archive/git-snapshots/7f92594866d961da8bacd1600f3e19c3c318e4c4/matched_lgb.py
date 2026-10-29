from pathlib import Path
import sys,json
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor/src'))
from cyp_submission.features import featurize
from worker import lgbfit,savepred
train=pd.read_csv(ROOT/'data/official-train.csv');roles=json.loads((ROOT/'prepared/roles.json').read_text())
X=featurize(train.SMILES.tolist()).replace([np.inf,-np.inf],np.nan).to_numpy(np.float32);np.save(ROOT/'prepared/classical.npy',X)
for name,r in roles.items():
 out=ROOT/'outputs'/name;out.mkdir(exist_ok=True)
 for tag,tr in [('lgb_matched',r['fit']),('lgb',sorted(r['fit']+r['val']))]:
  pred=lgbfit(X,np.asarray(tr),np.asarray(r['test']),train,out,tag);savepred(out,tag,train.iloc[r['test']].Molecule_Name.to_numpy(),pred)
  print('MATCHED_LGB_COMPLETE',name,tag,flush=True)
