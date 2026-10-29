"""Replay published analog selection and audit model-fold equivalence; no models trained."""
from pathlib import Path
import ast,types,sys,json,hashlib,os
import numpy as np,pandas as pd
from rdkit import Chem,RDLogger,DataStructs
from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator
RDLogger.DisableLog('rdApp.*');os.umask(0o077)
R=Path(__file__).resolve().parent;W=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition');G=W/'artifacts/goal-20261026';A=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/reference_audit');SRC=A/'sources/8c72c7559471febaf0962fd551b4eaab8db3a136/src/workbench';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def functions(path,names,namespace):
 a=ast.parse(path.read_text());n=ast.Module(body=[x for x in a.body if isinstance(x,ast.FunctionDef) and x.name in names],type_ignores=[]);exec(compile(n,str(path),'exec'),namespace)
ns={'np':np,'pd':pd,'Chem':Chem};functions(SRC/'utils/chem_utils/fingerprints.py',['similarity_fingerprints'],ns)
for name in ['workbench','workbench.utils','workbench.utils.chem_utils','workbench.utils.chem_utils.fingerprints']:sys.modules[name]=types.ModuleType(name)
sys.modules['workbench.utils.chem_utils.fingerprints'].similarity_fingerprints=ns['similarity_fingerprints']
functions(SRC/'training/splits.py',['analog_holdout_split','_find_smiles_column'],ns)
data=pd.read_csv(A/'official_train.csv');print('reference_rows',len(data),flush=True);targets=[c for c in data if c.lower().endswith('_pic50_direct_inhibition')];idcol='molecule_name' if 'molecule_name' in data else 'Molecule_Name';scol='smiles' if 'smiles' in data else 'SMILES';mask=ns['analog_holdout_split'](data,target_columns=targets,smiles_column=scol,n_hits=50,analogs_per_hit=10);expected=set(pd.read_csv(A/'holdout_ids.csv').iloc[:,0]);actual=set(data.loc[mask,idcol]);replay={'source_fingerprint_sha256':sha(SRC/'utils/chem_utils/fingerprints.py'),'source_split_sha256':sha(SRC/'training/splits.py'),'source_input_sha256':sha(A/'official_train.csv'),'n_hits_per_target':50,'targets':targets,'analogs_per_hit':10,'minimum_count_Tanimoto':.4,'replayed_count':len(actual),'frozen_count':len(expected),'exact_frozen_ID_match':actual==expected,'symmetric_difference':sorted(actual^expected)}
(R/'briford529_protocol_replay.json').write_text(json.dumps(replay,indent=2)+'\n')
# Sensitivity geometry under the actual analog-selector representation: raw sparse-count Morgan.
m=json.loads((G/'model-audit/official-snapshot-18460/manifest.json').read_text());tr=pd.read_csv(m['files']['official_train']['path']);q=pd.read_csv(m['files']['official_test']['path']);coh=json.loads(Path(m['files']['cohorts']['path']).read_text())['cohorts'];index={x:i for i,x in enumerate(tr.Molecule_Name)};f,_=ns['similarity_fingerprints'](tr.SMILES.tolist());b,_=ns['similarity_fingerprints'](q.SMILES.tolist());assert len(f)==4905 and len(b)==750
contexts={'blind750':(b,np.arange(4905))}
for name in ['own750','briford529']:contexts[name]=([f[index[i]] for i in coh[name]['test_ids']],np.array([index[i] for i in coh[name]['train_ids']]))
rows=[]
for name,(queries,refs) in contexts.items():
 nn=np.array([max(DataStructs.BulkTanimotoSimilarity(fp,[f[i] for i in refs])) for fp in queries]);within=np.array([max(s for j,s in enumerate(DataStructs.BulkTanimotoSimilarity(fp,queries)) if j!=i) for i,fp in enumerate(queries)]);rows.append({'context':name,'representation':'raw sparse-count Morgan radius2, native analog-selector default','n':len(queries),'reference_n':len(refs),'median_to_training':np.median(nn),'fraction_to_training_ge_0.7':np.mean(nn>=.7),'median_within_query':np.median(within),'fraction_within_query_ge_0.7':np.mean(within>=.7)})
pd.DataFrame(rows).to_csv(R/'sparse_count_geometry_sensitivity.csv',index=False)
# Match audited strict request groups against actual official inner/outer membership.
final=json.loads((G/'submission-preparation/final-inputs/final-manifest.json').read_text());pairs=pd.read_csv(final['files']['strict_pairs']['path'],dtype=str).fillna('');group={}
for _,r in pairs.iterrows():
 if r.stereo_preserving_tautomer_key_equal!='True':continue
 ids=r.request_ids.split(';');key=min(ids)
 for i in ids:group[i]=key
mapping=pd.read_csv(m['files']['id_map']['path']);mapping=mapping[mapping.source=='official-train.csv'].set_index('Molecule_Name');keys={n:group.get(r) for n,r in mapping.request_id.items()};audit={}
for name in ['own750','briford529']:
 c=coh[name];a={keys[i] for i in c['train_ids'] if keys.get(i)};b={keys[i] for i in c['test_ids'] if keys.get(i)};overlaps=[]
 for k,fold in enumerate(c['inner_folds']):
  aa={keys[i] for i in fold['train_ids'] if keys.get(i)};bb={keys[i] for i in fold['val_ids'] if keys.get(i)};overlaps.append({'fold':k,'crossing_audited_strict_groups':len(aa&bb)})
 audit[name]={'outer_crossing_audited_strict_groups':len(a&b),'inner_folds':overlaps}
(R/'official_strict_group_membership_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps({'exact_brifford_ID_replay':actual==expected,'count':len(actual),'strict_official_overlaps':audit},indent=2))
