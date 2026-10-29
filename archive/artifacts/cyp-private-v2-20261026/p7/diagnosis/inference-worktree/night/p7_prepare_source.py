import json,hashlib
from pathlib import Path
import pandas as pd,numpy as np
R=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026/chemistry-audit/final-32421-v3');base=Path(__file__).resolve().parents[1];out=base/'p7/stage'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(R/'features-snapshot.csv')=='0ce7a04675c45d48d8055f75cad3a95dd757613657b0ff01a5d7a70b762a7d52'
df=pd.read_csv(base/'p3/stage/table.csv');f=pd.read_csv(R/'features-snapshot.csv');assert f.request_id.is_unique
cols=sorted(c for c in f.columns if c.startswith('ADMETLAB::') and '::category=' not in c);assert len(cols)==120
eligible=set(pd.read_csv(R/'feature-eligible-request-ids.csv').request_id);assert set(df.request_id)<=eligible
f=f.set_index('request_id').loc[df.request_id];x=f[cols].to_numpy(float);assert x.shape==(31641,120) and np.isfinite(x).all()
np.save(out/'admet120.npy',x.astype(np.float64));df[['molecule_name','request_id','smiles']].assign(request_smiles=f.SMILES.to_numpy(),service_smiles=f.service_smiles.to_numpy()).to_csv(out/'rows.csv',index=False)
m={'rows':31641,'columns':cols,'source_snapshot_sha256':sha(R/'features-snapshot.csv'),'source_eligibility_sha256':sha(R/'feature-eligible-request-ids.csv'),'source_audit_summary_sha256':sha(R/'summary.json'),'p3_table_sha256':sha(base/'p3/stage/table.csv'),'matrix_sha256':sha(out/'admet120.npy'),'row_map_sha256':sha(out/'rows.csv'),'normalization_applied_at_join':False,'join':'exact request_id; frozen commonP3 roworder; no positionaljoin to servicecache','finite':True};(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print({k:v for k,v in m.items() if k!='columns'})
