from pathlib import Path
import json,hashlib,shutil
import numpy as np,pandas as pd
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize
b=Path(__file__).parent.parent;p=b/'p9-nested';stage=p/'stage';stage.mkdir(exist_ok=True);W=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts');G=W/'goal-20261026';official=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-admet500-pilot-20261025/stage/official-train.csv');truth=pd.read_csv(official).set_index('Molecule_Name');ep=['CYP1A2','CYP2C9','CYP2D6','CYP3A4'];cols=[e+'_pIC50_direct_inhibition' for e in ep];cohortpath=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-admet500-pilot-20261025/stage/cohorts.json');co=json.load(open(cohortpath))['cohorts'];mapmanifest=json.load(open(G/'model-audit/official-snapshot-18460/manifest.json'));idmap_path=Path(mapmanifest['files']['id_map']['path']);idmap=pd.read_csv(idmap_path);idmap=idmap[idmap.source=='official-train.csv'].set_index('Molecule_Name');fm=json.load(open(G/'submission-preparation/final-inputs/final-manifest.json'));pairpath=Path(fm['files']['strict_pairs']['path']);pairs=pd.read_csv(pairpath,dtype=str).fillna('');strictmap={}
def sha(q):return hashlib.sha256(Path(q).read_bytes()).hexdigest()
for _,r in pairs.iterrows():
 if r.stereo_preserving_tautomer_key_equal=='True':
  ids=r.request_ids.split(';')
  for v in ids:strictmap[v]=min(ids)
keys={}
for name,row in truth.iterrows():
 mol=Chem.MolFromSmiles(row.SMILES);ik=Chem.MolToInchiKey(mol).split('-')[0];m=rdMolStandardize.Uncharger().uncharge(rdMolStandardize.FragmentParent(mol));Chem.RemoveStereochemistry(m);keys[name]=(Chem.MolToSmiles(m,isomericSmiles=False),ik,strictmap.get(idmap.loc[name,'request_id']))
def forbidden(train,excluded):
 a={keys[x][0] for x in excluded};z={keys[x][1] for x in excluded};s={keys[x][2] for x in excluded if keys[x][2]};return [x for x in train if keys[x][0] in a or keys[x][1] in z or (keys[x][2] and keys[x][2] in s)]
result={};sources={str(x):sha(x) for x in [official,cohortpath,idmap_path,pairpath]};checks=[]
for name in ['own750','briford529']:
 cc=co[name];outer_train=cc['train_ids'];query=cc['test_ids'];assert not forbidden(outer_train,query);inners=[];validation=[]
 for k,f in enumerate(cc['inner_folds']):
  tr=f['train_ids'];val=f['val_ids'];assert set(tr)|set(val)<=set(outer_train);remove=forbidden(tr,query+val);tr=[x for x in tr if x not in set(remove)];assert not (set(tr)&set(val) or set(tr)&set(query));inners.append({'fold':k,'train_ids':tr,'val_ids':val,'new_train_side_purged_ids':remove,'previous_parent_purged':f['parent_purged']});validation+=val
 assert sorted(validation)==sorted(outer_train) and len(validation)==len(set(validation))
 root=W/'briford-native-holdouts-20261024/remote/holdouts'/name;raw=pd.read_csv(root/'results/cyp-ensemble_activity_submission_native_raw.csv').set_index('Molecule_Name').loc[query];reference=pd.read_csv(b/'p5/results'/f'{name}__raw__original_absent.csv').set_index('Molecule_Name').loc[query];assert raw.SMILES.tolist()==truth.loc[query,'SMILES'].tolist();assert np.allclose(raw[cols],reference[cols],rtol=0,atol=1e-12)
 total=np.zeros((len(outer_train),4));counts=np.zeros_like(total);query_components={};oof_components={}
 for member in ['union18','mtaux8','2d6isoform6','2d6single']:
  specpath=root/'prepared'/f'{member}.json';datapath=root/'prepared'/f'{member}.csv';spec=json.load(open(specpath));data=pd.read_csv(datapath);assert not set(query)&set(data.molecule_name);sources[str(specpath)]=sha(specpath);sources[str(datapath)]=sha(datapath);whole=pd.read_csv(root/'results'/member/'oof.csv').set_index('molecule_name');sources[str(root/'results'/member/'oof.csv')]=sha(root/'results'/member/'oof.csv');assert whole.index.is_unique
  foldframes=[]
  for k,f in enumerate(spec['folds']):
   d=root/'results'/member/f'fold{k}';done=json.load(open(d/'complete.json'));assert done['status']=='complete';sources[str(d/'complete.json')]=sha(d/'complete.json')
   for rel in ['job.json','oof.csv','test.csv','metadata.json']:assert sha(d/rel)==done['files'][rel];sources[str(d/rel)]=done['files'][rel]
   z=pd.read_csv(d/'oof.csv').set_index('molecule_name');assert z.index.tolist()==data.molecule_name.iloc[f['validation']].tolist();foldframes.append(z)
  rebuilt=pd.concat(foldframes);assert rebuilt.index.is_unique and set(rebuilt.index)==set(data.molecule_name)
  queryframe=pd.read_csv(root/'results'/member/'test_raw.csv').set_index('molecule_name');sources[str(root/'results'/member/'test_raw.csv')]=sha(root/'results'/member/'test_raw.csv')
  for j,t in enumerate(cols):
   target=t.lower();pred=target+'_pred'
   if pred not in whole:continue
   assert np.allclose(rebuilt.loc[whole.index,target],whole[pred],rtol=0,atol=1e-12)
   obs=truth.loc[outer_train,t].notna();present=[x for x in outer_train if x in whole.index];assert np.allclose(whole.loc[present,target],truth.loc[present,t],equal_nan=True,rtol=0,atol=1e-12)
   values=whole[pred].reindex(outer_train).to_numpy();ok=np.isfinite(values);total[ok,j]+=values[ok];counts[ok,j]+=1;query_components.setdefault(j,[]).append(queryframe.loc[query,pred].to_numpy());checks.append({'cohort':name,'member':member,'target':target,'oof_available':int(ok.sum()),'official_observed_available':int(sum(x in whole.index for x in truth.loc[outer_train].index[obs]))})
 native=total/counts;assert np.isfinite(native).all();expected_counts=np.array([2,2,4,2])
 for j,t in enumerate(cols):
  observed=truth.loc[outer_train,t].notna().to_numpy();assert (counts[observed,j]==expected_counts[j]).all();reconstructed=np.stack(query_components[j],axis=1).mean(1);assert np.allclose(reconstructed,raw[t],rtol=0,atol=1e-12)
 n=truth.loc[outer_train,['SMILES']].reset_index()
 for j,e in enumerate(ep):n[e]=native[:,j]
 nf=stage/f'{name}-original-native-training-oof.csv';n.to_csv(nf,index=False,float_format='%.17g');q=raw.reset_index();qf=stage/f'{name}-original-native-query.csv';q.to_csv(qf,index=False,float_format='%.17g')
 p9={}
 for rep in ['adme600','atomjepa256']:
  src=b/'p9-tabicl/full-results'/f'{name}-{rep}-raw.csv';df=pd.read_csv(src);assert df.Molecule_Name.tolist()==query and df.SMILES.tolist()==truth.loc[query,'SMILES'].tolist();dst=stage/src.name;shutil.copy2(src,dst);p9[rep]={'path':str(dst),'sha256':sha(dst),'source':str(src)}
 result[name]={'train_ids':outer_train,'query_ids':query,'inner_folds':inners,'native_oof':{'path':str(nf),'sha256':sha(nf)},'native_query':{'path':str(qf),'sha256':sha(qf)},'p9_query':p9,'native_observed_component_counts':expected_counts.tolist(),'query_source_sha256':sha(root/'results/cyp-ensemble_activity_submission_native_raw.csv')}
 print(json.dumps({'cohort':name,'train':len(outer_train),'query':len(query),'inner_new_purges':[len(x['new_train_side_purged_ids']) for x in inners],'native_prediction_fold_hashes_verified':20}),flush=True)
manifest={'cohorts':result,'sources':sources,'native_component_checks':checks,'historical_limits':['Original native components use different inner fold maps; these are rowwise OOF values, not one common native split.','The original fixed expert retains previously audited public-source associations and strict-tautomer purge limitations. New P9 fits exclude whole outerquery and audited equivalences; this does not retrospectively clean the historical expert.','Both outer cohorts are repeatedly used development diagnostics, not independent blind confirmation.'],'source_sha256':sha(__file__),'no_fits':True};(stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
