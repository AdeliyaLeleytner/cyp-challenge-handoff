from pathlib import Path
import pandas as pd,numpy as np,json,hashlib
from rdkit import Chem
P=Path(__file__).resolve().parents[1];R=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/fullfit-strae-prep/stage/original_full/raw');d=pd.read_csv(P/'p7/stage/table.csv').set_index('molecule_name');t=pd.read_csv(R/'tdi.csv').set_index('molecule_name');s=pd.read_csv(R/'single_concentration.csv');m=json.loads((P/'p7/stage/fold-manifest.json').read_text());a=t.reindex(d.index);rows=[];coverage=[]
for i,c in enumerate(['cyp1a2','cyp2c9','cyp2d6','cyp3a4']):
 D=d[c+'_pic50_direct_inhibition'];A=a[c+'_pic50_tdi_condition'];S=d[c+'_log2fc'];coverage.append({'target':c,'direct':int(D.notna().sum()),'active':int(A.notna().sum()),'active_extra_vs_direct':int((A.notna()&D.isna()).sum()),'screen':int(S.notna().sum()),'direct_active':int((D.notna()&A.notna()).sum()),'active_screen':int((A.notna()&S.notna()).sum()),'triple':int((A.notna()&D.notna()&S.notna()).sum()),'training_active_screen_by_fold':[int((A.iloc[f['train']].notna()&S.iloc[f['train']].notna()).sum()) for f in m['folds']]})
 for name in A[A.notna()].index:rows.append({'molecule_name':name,'request_id':d.loc[name,'request_id'],'target':c,'active_pic50':float(A.loc[name]),'has_direct':bool(pd.notna(D.loc[name])),'has_screen':bool(pd.notna(S.loc[name])),'source_smiles':t.loc[name,'smiles'],'model_smiles':d.loc[name,'smiles']})
x=pd.DataFrame(rows);can=lambda z:Chem.MolToSmiles(Chem.MolFromSmiles(z),isomericSmiles=True);bad=[]
for name,g in x.groupby('molecule_name'):
 r=g.iloc[0]
 if can(r.source_smiles)!=can(r.model_smiles):bad.append(name)
assert not bad
x.to_csv(P/'biochem_sources/next-condition-active-membership.csv',index=False);out={'coverage':coverage,'active_cells':len(x),'active_unique_rows':x.molecule_name.nunique(),'exact_ID_join_source_graph_mismatches':bad,'no_extra_rows_added':True,'tdi_ids_exactly_in_common_table':len(set(t.index)&set(d.index)),'new_active_cells_without_direct':int((~x.has_direct).sum()),'source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'tdi.csv',R/'single_concentration.csv',R/'emax.csv',P/'p7/stage/table.csv',P/'p7/stage/fold-manifest.json',Path(__file__)]}};(P/'biochem_sources/next-condition-coverage.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k not in ['coverage','source_hashes']})
