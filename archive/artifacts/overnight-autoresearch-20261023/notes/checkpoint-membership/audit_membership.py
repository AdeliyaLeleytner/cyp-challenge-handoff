"""Read-only membership audit; cached public assets, no training or checkpoint unpickling."""
import json,sys,hashlib,pickletools,zipfile
from pathlib import Path
import pandas as pd,numpy as np
ROOT=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023')
REPO=Path('/Users/adeliyaleleytner/.local/share/openresearch/projects/cyp-chemeleon-baseline-20261023')
FULL=Path('/Users/adeliyaleleytner/.local/share/cyp-inhibition/reciprocal-comparison-20261023/full')
OUT=Path(__file__).parent;sys.path.insert(0,str(REPO))
from night.public_data import normalize_parent_key

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
coh=json.loads((ROOT/'stage/cohorts.json').read_text())
train=pd.read_csv(ROOT/'stage/official-train.csv');test=pd.read_csv(ROOT/'stage/official-test.csv')
for df in [train,test]:df['parent_key']=df.SMILES.map(normalize_parent_key)
cohorts={'official_train':train,'actual_blinded_TEST':test}
for name,c in coh['cohorts'].items():cohorts[name+'_outer_holdout']=train[train.Molecule_Name.isin(c['test_ids'])]
result={'normalization':'RDKit FragmentParent, uncharge, remove stereochemistry, canonical SMILES; no tautomer canonicalization',
        'official_files':{name:{'rows':len(df),'parents':int(df.parent_key.nunique()),'invalid':int(df.parent_key.isna().sum())} for name,df in cohorts.items()},'checkpoints':{},'sources':{}}
source_manifest=json.loads((FULL/'source-manifest.json').read_text())
for filename in ['chemprop_medium.pt','chemprop_chemeleon.pt']:
 p=FULL/'vendor/checkpoints'/filename;b=p.read_bytes();blob=hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()
 expected=next(x['sha'] for x in source_manifest['files'] if x['path'].endswith('/'+filename));assert blob==expected
 with zipfile.ZipFile(p) as z:ops=list(pickletools.genops(z.read(next(n for n in z.namelist() if n.endswith('data.pkl')))))
 found={}
 for i,(op,arg,pos) in enumerate(ops):
  if arg in ['n_tasks','d_h','depth','output_columns']:
   found[arg]=next(a for o,a,p in ops[i+1:] if o.name not in ['BINPUT','LONG_BINPUT','MEMOIZE'])
 result['checkpoints'][filename]={'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha1':blob,'git_blob_matches_pinned_Jeremy_revision':True,'metadata':found,'training_membership':'unknown; no hash-linked training membership manifest or named output columns found'}
for tag in ['adme_pretrain','chemeleon']:
 p=FULL/'prepared'/f'{tag}.npy';a=np.load(p,mmap_mode='r');result.setdefault('feature_caches',{})[tag]={'sha256':digest(p),'shape':list(a.shape),'checkpoint':'chemprop_medium.pt' if tag=='adme_pretrain' else 'chemprop_chemeleon.pt','proof':'prepare_remote.py maps tag to checkpoint and performs frozen forward pass; saved outputs/preparation.json matches checkpoint SHA256'}

def audit(name,df,smiles_col,labelcols,identity):
 d=df.copy();d['parent_key']=d[smiles_col].map(normalize_parent_key)
 d[labelcols]=d[labelcols].apply(pd.to_numeric,errors='coerce')
 finite=np.isfinite(d[labelcols]).any(axis=1);labeled=set(d.loc[finite,'parent_key'].dropna());allkeys=set(d.parent_key.dropna())
 entry={'identity':identity,'rows':len(d),'unique_parents':len(allkeys),'invalid_structures':int(d.parent_key.isna().sum()),'labeled_parents':len(labeled),'label_columns':labelcols,'membership':{}}
 allmatches=[]
 for cname,c in cohorts.items():
  match=c.parent_key.isin(labeled);m=c.loc[match,['Molecule_Name','SMILES','parent_key']].copy();m['cohort']=cname;allmatches.append(m)
  counts={col:int(c.parent_key.isin(set(d.loc[np.isfinite(d[col]),'parent_key'].dropna())).sum()) for col in labelcols}
  entry['membership'][cname]={'matching_structure_rows':int(c.parent_key.isin(allkeys).sum()),'matching_labeled_rows':int(match.sum()),'matching_labeled_unique_parents':int(c.loc[match,'parent_key'].nunique()),'per_endpoint_matching_rows':counts}
 result['sources'][name]=entry
 pd.concat(allmatches).to_csv(OUT/(name+'-matched-official-rows.csv'),index=False)
for repo in ['cyp1a2-cyp2d6-cyp3a4-cyp2c9-chemeleon-v1','cyp1a2-cyp2d6-cyp3a4-cyp3c9-chemeleon-baseline']:
 data=OUT/repo/'anvil_training/data';x=pd.read_csv(data/'X_train.csv');y=pd.read_csv(data/'y_train.csv');assert len(x)==len(y)
 info=json.loads((OUT/(repo+'.json')).read_text());weight=next(z for z in info['tree'] if z['path']=='anvil_training/model.pth')
 identity={'repo':'openadmet/'+repo,'revision':info['info']['sha'],'model_sha256':weight['lfs']['oid'],'matches_either_Jeremy_checkpoint':weight['lfs']['oid'] in [v['sha256'] for v in result['checkpoints'].values()],'X_train_sha256':digest(data/'X_train.csv'),'y_train_sha256':digest(data/'y_train.csv'),'applicability':'Verified membership of this different official OpenADMET model; not evidence of exact Jeremy membership'}
 audit(repo,pd.concat([x,y],axis=1),x.columns[0],list(y),identity)
p=FULL/'vendor/data/external/cyp_chembl.csv';d=pd.read_csv(p)
audit('Jeremy_disclosed_cyp_chembl',d,'smiles',[c for c in d if c.endswith('_PIC50')],{'sha256':digest(p),'repo':source_manifest['repository'],'revision':source_manifest['commit'],'applicability':'Published auxiliary/source table with README association to adme_pretrain; no hash-linked row-level training membership for either checkpoint'})
foundation=json.loads((OUT/'chemprop-foundation-pretraining-weights.json').read_text())
result['foundation_hash_comparison']={'repo':foundation['info']['id'],'revision':foundation['info']['sha'],'weights_compared':len([x for x in foundation['tree'] if x.get('lfs')]),'matches':[{ 'file':x['path'],'checkpoint':k} for x in foundation['tree'] if x.get('lfs') for k,v in result['checkpoints'].items() if x['lfs']['oid']==v['sha256']]}
(OUT/'membership.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:{c:v['matching_labeled_rows'] for c,v in d['membership'].items()} for k,d in result['sources'].items()},indent=2))
