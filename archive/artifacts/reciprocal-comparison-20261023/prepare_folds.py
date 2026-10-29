from pathlib import Path
import sys,json,hashlib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor/src'))
from cyp_submission.splits import butina_kfold,butina_clusters
src=Path.home()/'.cache/cyp-inhibition/data/cyp-challenge-TRAIN_inhibition.csv'
df=pd.read_csv(src)
folds=butina_kfold(df.SMILES.tolist(),n_folds=5,cutoff=.6,seed=42)
cols=[c for c in df if c.endswith('_direct_inhibition')]
out=df[['Molecule_Name','SMILES']].copy();out['fold']=folds
out.to_csv(ROOT/'jeremy-reconstructed-folds.csv',index=False)
structures=pd.read_csv(Path.home()/'.cache/cyp-inhibition/data/all_molecule_structures.csv')
print('STRUCTURE_COLUMNS',structures.columns.tolist(),flush=True)
result={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'folds_sha256':hashlib.sha256((ROOT/'jeremy-reconstructed-folds.csv').read_bytes()).hexdigest(),'fold_definition':{'cutoff_similarity':.6,'n_folds':5,'seed':42,'source':'unmodified participant splits.py'},'sizes':{str(f):{'n':int((folds==f).sum()),'labels':df.loc[folds==f,cols].notna().sum().to_dict()} for f in range(5)},'qualification':'Reconstructed with pinned participant code and input row order; not a recovered original saved fold assignment.'}
(ROOT/'fold-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
