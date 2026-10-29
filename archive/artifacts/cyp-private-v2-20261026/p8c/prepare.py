import json,hashlib,shutil
from pathlib import Path
import pandas as pd,numpy as np
from rdkit import Chem
B=Path(__file__).resolve().parents[1];S=B/'p8c/stage';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
base=B/'p7/stage/table.csv';fold=B/'p7/stage/fold-manifest.json';act=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/fullfit-strae-prep/stage/original_full/raw/tdi.csv');maps=B/'p8b/results/selected_maps.json';membership=B/'p8b/results/selector_membership.csv'
assert sha(maps)=='be16dd34c6776312e73707acd0c0e0dff1823c32267b20f76af8263f3c6aa9d8';assert sha(act)=='2ebad28ff5e155dc7de3a7e6e10920e938f559be561ca74f2a7c95dcfdf03a82';df=pd.read_csv(base,float_precision='round_trip');a=pd.read_csv(act).set_index('molecule_name');m=json.loads(fold.read_text());old=m['targets'];EP=['cyp1a2','cyp2c9','cyp2d6','cyp3a4'];active=[x+'_pic50_tdi_condition' for x in EP]
assert a.index.is_unique and df.molecule_name.is_unique
idx=df.molecule_name.isin(a.index);aliases=a.loc[df.loc[idx,'molecule_name']]
canon=lambda s:Chem.MolToSmiles(Chem.MolFromSmiles(s),isomericSmiles=True)
assert all(canon(x)==canon(y) for x,y in zip(df.loc[idx,'smiles'],aliases.smiles))
for c in active:df[c]=a[c].reindex(df.molecule_name).to_numpy(float)
assert len(df)==31641 and int(df[active].notna().sum().sum())==6571
out=df[['molecule_name','smiles','request_id']+old+active+[f'{s}_{j}' for s in ['low','high'] for j in range(4)]];out.to_csv(S/'table.csv',index=False,float_format='%.17g')
# Exact old-label identity, rather than a new curation/membership decision.
assert np.allclose(out[old].to_numpy(float),df[old].to_numpy(float),rtol=0,atol=0,equal_nan=True)
shutil.copy2(maps,S/'selected_maps.json');shutil.copy2(membership,S/'selector_membership.csv')
mem=pd.read_csv(membership);frozen=json.loads(maps.read_text());proof=[]
for f in range(5):
 tr=np.array(m['folds'][f]['train']);forbid=set(m['folds'][f]['test'])|set(m['folds'][f]['stop'])
 for j,c in enumerate(EP):
  observed=np.isfinite(out[active[j]])&np.isfinite(out[c+'_log2fc']);ix=tr[observed.iloc[tr].to_numpy()];r=next(x for x in frozen if x['outer_fold']==f and x['target']==c);expected=mem[(mem.outer_fold==f)&(mem.target==c)]
  assert ix.tolist()==expected.row_index.tolist() and out.molecule_name.iloc[ix].tolist()==expected.molecule_name.tolist();assert not set(ix)&forbid
  digest=hashlib.sha256('\n'.join(out.molecule_name.iloc[ix]).encode()).hexdigest();assert digest==r['fit_ids_sha256'] and len(ix)==r['fit_count']
  proof.append({'fold':f,'target':c,'fit_count':len(ix),'fit_ids_sha256':digest})
m.update(targets=old+active,real_heads=22,output_heads=30,data_sha256=sha(S/'table.csv'),original_18_table_sha256=sha(base),original_fold_manifest_sha256=sha(fold),active_source_sha256=sha(act),selected_maps_sha256=sha(S/'selected_maps.json'),selector_membership_sha256=sha(S/'selector_membership.csv'),active_target_counts={c:int(out[c].notna().sum()) for c in active},source_files={**m['source_files'],str(act):sha(act)},map_membership_proof=proof,loss_normalization='batch_rows*22 fixed slots; missing/unused cells masked; no observed-cell renormalization',active_labels_in_A='masked; identity scale on unused active heads',screen_indices=[old.index(c+'_log2fc') for c in EP],active_indices=[18,19,20,21],primary_indices=[0,1,2,3])
(S/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({'rows':len(out),'active_cells':6571,'active_counts':m['active_target_counts'],'screen_indices':m['screen_indices'],'maps_verified':len(proof),'data_sha256':m['data_sha256']},indent=2))
