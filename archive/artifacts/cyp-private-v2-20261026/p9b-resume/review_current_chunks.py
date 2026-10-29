import sys,json,time,hashlib
from pathlib import Path
import pandas as pd,numpy as np
p=Path(__file__).parent;sys.path.insert(0,str(p/'worktree/night'));from p9_identity import validate
rows=pd.read_csv(p.parent/'p9a/next-stage/official5655-structures.csv');records=[];files=[x for x in sorted((p.parent/'p9b/results').glob('coordinates-through-*.npz')) if time.time()-x.stat().st_mtime>2]
for file in files:
 co=np.load(file)
 for key in co.files:
  if not key.startswith('z_'):continue
  i=int(key[2:]);rec={'row':i,'id':rows.Molecule_Name.iloc[i]}
  try:rec.update(status='pass',checks=validate(rows.SMILES.iloc[i],co[key],co[f'pos_{i}']))
  except Exception as e:rec.update(status='flagged',error=type(e).__name__+': '+str(e))
  records.append(rec)
r={'scope':'preliminaryimmutablechunks_only;terminalrevalidationstillrequired','rows':len(records),'unique_rows':len({x['row'] for x in records}),'flagged':[x for x in records if x['status']!='pass'],'validator_sha256':hashlib.sha256((p/'worktree/night/p9_identity.py').read_bytes()).hexdigest(),'chunk_hashes':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in files}};(p/'PARTIAL_MODERN_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='chunk_hashes'}))
