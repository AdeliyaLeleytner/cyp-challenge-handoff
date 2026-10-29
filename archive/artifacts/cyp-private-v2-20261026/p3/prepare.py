import json,hashlib,shutil
from pathlib import Path
import pandas as pd,numpy as np
R=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026')
S=R/'model-audit/corrected-fullfit-native/stage'; O=Path(__file__).parent/'stage'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
df=pd.read_csv(S/'prepared/union18.csv',float_precision='round_trip'); spec=json.loads((S/'prepared/union18.json').read_text())
offpath=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-admet500-pilot-20261025/stage/official-train.csv'); off=pd.read_csv(offpath).set_index('Molecule_Name')
a=pd.read_csv(S/'audit/id-map-snapshot.csv'); a=a[a.source=='union18'].set_index('Molecule_Name'); ids=df.molecule_name.tolist(); mapping=a.loc[ids]; assert len(mapping)==len(df)
excpath=R/'data-policy/fresh-full-pool-eligible-exclusions.csv'; exc=pd.read_csv(excpath); excluded=set(exc.request_id)
keep=~mapping.request_id.isin(excluded).to_numpy(); remap={old:new for new,old in enumerate(np.flatnonzero(keep))}
primary=[x.lower()+'_pic50_direct_inhibition' for x in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]; targets=primary+[x for x in spec['targets'] if x not in primary]
for k,e in enumerate(['CYP1A2','CYP2C9','CYP2D6','CYP3A4']):
 for side in ['low','high']:
  df[f'{side}_{k}']=off[e+'_pIC50_direct_inhibition_conf_'+side].reindex(ids).to_numpy()
 y=off[e+'_pIC50_direct_inhibition'].reindex(ids).to_numpy(); mask=np.isfinite(y); assert np.allclose(df.loc[mask,primary[k]],y[mask],rtol=0,atol=1e-12)
pairs=pd.read_csv(S/'audit/tautomer-pair-chemical-details.csv'); group={}
for _,p in pairs[pairs.stereo_preserving_tautomer_key_equal==True].iterrows():
 for rid in p.request_ids.split(';'):group[rid]=min(p.request_ids.split(';'))
rids=mapping.request_id.tolist(); gids=[group.get(r,r) for r in rids]; folds=[]
for k in range(5):
 test=spec['folds'][k]['validation']; stop=spec['folds'][(k+1)%5]['validation']; forbidden={gids[i] for i in test+stop}
 train=set(spec['folds'][k]['train'])&set(spec['folds'][(k+1)%5]['train']); train=sorted(i for i in train if gids[i] not in forbidden)
 f={role:[remap[i] for i in idx if keep[i]] for role,idx in [('train',train),('stop',stop),('test',test)]}; assert not set(f['train'])&(set(f['stop'])|set(f['test']));folds.append(f)
df=df.loc[keep,['molecule_name','smiles']+targets+[f'{s}_{i}' for s in ['low','high'] for i in range(4)]].copy();df.insert(2,'request_id',np.array(rids)[keep]);df.to_csv(O/'table.csv',index=False,float_format='%.17g')
assert df.molecule_name.is_unique and df.request_id.is_unique
manifest={'targets':targets,'real_heads':18,'output_heads':26,'rows':len(df),'excluded_rows':int((~keep).sum()),'official_rows':int(df.molecule_name.isin(off.index).sum()),'folds':folds,'data_sha256':sha(O/'table.csv'),'source_files':{str(p):sha(p) for p in [S/'prepared/union18.csv',S/'prepared/union18.json',S/'audit/id-map-snapshot.csv',S/'audit/tautomer-pair-chemical-details.csv',offpath,excpath]},'policy':'same legacy union18 across four cells; approved29 source/feature exclusions; train-side exactrequest and approvedstereo-tautomer purge against stopping and test sets;18 realheads rather than author22; no new externaldata','test_labels_never_used_for_selection':True}
(O/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items() if k not in ['folds','source_files']},indent=2));print('folds',[(len(f['train']),len(f['stop']),len(f['test'])) for f in folds])
