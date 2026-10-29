from pathlib import Path
import pandas as pd,json,hashlib
from rdkit import Chem,RDLogger
RDLogger.DisableLog('rdApp.*')
P=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent;R=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026/model-audit/corrected-fullfit-native/stage/audit');d=pd.read_csv(P/'p7/stage/rows.csv');m=json.loads((P/'p3/stage/manifest.json').read_text());pairs=pd.read_csv(R/'tautomer-pair-chemical-details.csv');p=pairs[pairs.stereo_preserving_tautomer_key_equal==True];parent={}
def find(v):
 parent.setdefault(v,v)
 if parent[v]!=v:parent[v]=find(parent[v])
 return parent[v]
for ids in p.request_ids.str.split(';'):
 for rid in ids[1:]:parent[find(ids[0])]=find(rid)
d['group']=[find(v) for v in d.request_id];rows=[]
for k,f in enumerate(m['folds']):
 overlap=set(d.iloc[f['stop']].group)&set(d.iloc[f['test']].group)
 for role in ['stop','test']:
  x=d.iloc[f[role]];x=x[x.group.isin(overlap)].copy();x['fold']=k;x['role']=role;rows.extend(x.to_dict('records'))
pd.DataFrame(rows).to_csv(O/'stop-test-equivalent-rows.csv',index=False)
def canonical(s):
 x=Chem.MolFromSmiles(s);return Chem.MolToSmiles(x,isomericSmiles=True) if x else None
z=d[d.smiles!=d.request_smiles].copy();z['model_graph']=z.smiles.map(canonical);z['request_graph']=z.request_smiles.map(canonical);bad=z[z.model_graph!=z.request_graph];bad.to_csv(O/'nonidentical-model-request-graphs.csv',index=False);result={'different_literal_smiles_rows':len(z),'canonical_isomeric_graph_mismatches':len(bad),'stop_test_overlap_rows':len(rows),'stop_test_overlap_groups':len({r['group'] for r in rows}),'no_changes_to_stage':True};(O/'GRAPH_DETAIL.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));print(bad[['molecule_name','smiles','request_smiles']].head(10).to_string(index=False))
