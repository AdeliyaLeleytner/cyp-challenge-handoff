"""Private fixed-coefficient artifact×feature replay; no fitting or network code."""
from pathlib import Path
import json,os,time,shutil,importlib.metadata
import numpy as np,pandas as pd
from rdkit import Chem,RDLogger
from rdkit.Chem.Scaffolds import MurckoScaffold
from .private_p1 import T,METRICS,sha,save,require,event,read_vector,scores
ROOT=Path(__file__).resolve().parents[1];RDLogger.DisableLog('rdApp.*')
def mix(base,feature,weight,present):
 b=np.asarray(base,float);f=np.asarray(feature,float);w=np.asarray(weight,float);require(b.shape==f.shape and b.shape[1]==len(w),'Mix alignment failure');require(np.isfinite(b).all() and np.isfinite(f).all() and np.isfinite(w).all() and np.all((0<=w)&(w<=1)),'Invalid fixed mixture')
 return (1-w)*b+w*f if present else b.copy()
def fixed_map(x,reference_mean,calibration,floor=1.):
 return np.column_stack([np.maximum(reference_mean[j]+calibration[t.split('_')[0]]['scale']*(x[:,j]-reference_mean[j])+calibration[t.split('_')[0]]['offset'],floor) for j,t in enumerate(T)])
def main():
 os.umask(0o077);start=time.time();cfg=json.loads((ROOT/'private_p5_config.json').read_text());out=Path(cfg['output_dir']);require(not out.exists() or not any(out.iterdir()),'Output already populated');out.mkdir(parents=True,exist_ok=True)
 for k,r in cfg['files'].items():require(sha(r['path'])==r['sha256'],'Pinned input changed:'+k)
 train=pd.read_csv(cfg['files']['official_train']['path']).set_index('Molecule_Name');blind=pd.read_csv(cfg['files']['official_blind']['path']);require(set(blind)=={'Molecule_Name','SMILES'} and not set(blind.Molecule_Name)&set(train.index),'Blind structure-only/disjoint guard');coh=json.loads(Path(cfg['files']['cohorts']['path']).read_text())['cohorts'];selection=json.loads(Path(cfg['files']['outer_weights']['path']).read_text());final_selection=json.loads(Path(cfg['files']['blind_weights']['path']).read_text())
 save(out/'run-identity.json',{'config':cfg,'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','rdkit']},'source_scope':'Historical artifact contrast, not causal purge or fresh validation','feature_coefficient_convention':'w is feature contribution; (1-w)*base+w*same_head; absent arm is base, not attenuated base','serving_policy':'One original-context affine map and floor for all arms; original reference mean/scale/offset never recomputed per arm','base_fits':0,'coefficient_fits':0,'map_search':False,'network':False,'publication':False,'submission':False})
 met=[];per=[];paired=[];controls=[];fixed=[]
 for context in ['own750','briford529','blind750']:
  isblind=context=='blind750';ids=blind.Molecule_Name.tolist() if isblind else coh[context]['test_ids'];frame=blind[['Molecule_Name','SMILES']].copy() if isblind else train.loc[ids].reset_index()[['Molecule_Name','SMILES']]
  original=read_vector(cfg['files'][context+'_original_raw']['path'],ids,frame.SMILES);corrected=read_vector(cfg['files'][context+'_corrected_raw']['path'],ids,frame.SMILES);served=read_vector(cfg['files'][context+'_original_served']['path'],ids,frame.SMILES);h6raw=read_vector(cfg['files'][context+'_H6_raw']['path'],ids,frame.SMILES)
  if isblind:
   heads=[]
   for t in T:
    p=np.load(cfg['files']['blind_head_'+t]['path'],allow_pickle=False);require(p.shape==(750,) and np.isfinite(p).all(),'Blind pure-head shape/finiteness');heads.append(p)
   feature=np.column_stack(heads);w=final_selection['chosen']['weight'];required_manifest=json.loads(Path(cfg['files']['blind_model_manifest']['path']).read_text());require([required_manifest['native_blend_weights'][t] for t in T]==w,'Feature-weight provenance mismatch')
  else:feature=read_vector(cfg['files'][context+'_pure_head']['path'],ids,frame.SMILES);w=selection[context]['lightgbm__adme720']['blends']['per_target']['weight']
  calibration=json.loads(Path(cfg['files'][context+'_original_calibration']['path']).read_text())['calibration'];refmean=original.mean(0)
  reproduced=mix(corrected,feature,w,True);require(np.allclose(reproduced,h6raw,atol=1e-12,rtol=0),'Corrected+pure-head does not reproduce H6 raw; coefficients or component wrong')
  require(np.allclose(fixed_map(original,refmean,calibration),served,atol=1e-12,rtol=0),'Original fixed-map identity failed')
  controls.append({'context':context,'corrected_plus_head_raw_max_abs':float(np.max(np.abs(reproduced-h6raw))),'original_fixed_map_max_abs':float(np.max(np.abs(fixed_map(original,refmean,calibration)-served))),'feature_weights':w})
  fixed.append({'context':context,'original_raw_reference_mean':refmean.tolist(),'calibration':calibration,'floor':1.,'coefficients_fixed_from_existing_training_OOF':True,'feature_weights':w})
  raw={'original_absent':original,'corrected_absent':corrected,'original_present':mix(original,feature,w,True),'corrected_present':reproduced}
  if not isblind:
   truth=train.loc[ids];y=truth[T].to_numpy(float);lo=truth[[t+'_conf_low' for t in T]].to_numpy(float);hi=truth[[t+'_conf_high' for t in T]].to_numpy(float);groups=[]
   for s in frame.SMILES:
    m=Chem.MolFromSmiles(s);groups.append(Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(m),isomericSmiles=False) or 'acyclic:'+Chem.MolToInchiKey(m).split('-')[0])
   groups=np.array(groups);members=[np.flatnonzero(groups==g) for g in np.unique(groups)];rng=np.random.default_rng(cfg['bootstrap_seed']);samples=[np.concatenate([members[k] for k in rng.integers(0,len(members),len(members))]) for _ in range(cfg['bootstrap_samples'])]
  for lane in ['fixed_original_served','raw']:
   vectors={k:fixed_map(v,refmean,calibration) if lane=='fixed_original_served' else v for k,v in raw.items()};points={}
   for name,z in vectors.items():
    require(np.isfinite(z).all() and np.all(z.std(0,ddof=1)>=.01),'Invalid output finite/spread');f=frame.copy()
    for j,t in enumerate(T):f[t]=z[:,j]
    path=out/f'{context}__{lane}__{name}.csv'
    if name=='original_absent':shutil.copyfile(cfg['files'][context+'_original_'+('served' if lane=='fixed_original_served' else 'raw')]['path'],path)
    else:f.to_csv(path,index=False,float_format='%.17g')
    if not isblind:
     s=scores(y,z,lo,hi);points[name]=s;met.append({'cohort':context,'lane':lane,'arm':name,**s['macro']});per.extend({'cohort':context,'lane':lane,'arm':name,'target':t,**v} for t,v in s['per_cyp'].items());event('crossed_replay_score',cohort=context,lane=lane,arm=name,macro=s['macro'])
   if isblind:event('blind_crossed_vectors_saved_unscored',lane=lane,rows=750);continue
   # Five fixed contrasts; last is the base×feature difference-in-differences.
   contrasts={'feature_on_original':{'original_present':1,'original_absent':-1},'feature_on_corrected':{'corrected_present':1,'corrected_absent':-1},'base_without_feature':{'corrected_absent':1,'original_absent':-1},'base_with_feature':{'corrected_present':1,'original_present':-1},'base_by_feature_interaction':{'corrected_present':1,'corrected_absent':-1,'original_present':-1,'original_absent':1}}
   draw={k:[] for k in vectors}
   for ix in samples:
    for name,z in vectors.items():
     r=scores(y[ix],z[ix],lo[ix],hi[ix]);draw[name].append([[r['per_cyp'][t][m] for m in METRICS] for t in T])
   draw={k:np.asarray(v,float) for k,v in draw.items()}
   for contrast,coef in contrasts.items():
    d=sum(a*draw[k] for k,a in coef.items());point=sum(a*np.array([[points[k]['per_cyp'][t][m] for m in METRICS] for t in T]) for k,a in coef.items())
    for target,dd,pp in [('macro',d.mean(1),point.mean(0))]+[(t,d[:,j,:],point[j]) for j,t in enumerate(T)]:
     for j,m in enumerate(METRICS):
      a=dd[:,j];a=a[np.isfinite(a)];require(len(a)>0,'No finite paired uncertainty');paired.append({'cohort':context,'lane':lane,'contrast':contrast,'target':target,'metric':m,'delta':pp[j],'lower95':np.quantile(a,.025),'upper95':np.quantile(a,.975),'valid_samples':len(a),'requested_samples':cfg['bootstrap_samples'],'scope':'Conditional historical-artifact contrast on reused cohorts; not causal purge or hidden-score attribution'})
 pd.DataFrame(met).to_csv(out/'all-metrics.csv',index=False);pd.DataFrame(per).to_csv(out/'per-cyp-metrics.csv',index=False);pd.DataFrame(paired).to_csv(out/'paired-contrasts.csv',index=False);save(out/'identity-controls.json',controls);save(out/'fixed-coefficients.json',fixed)
 save(out/'complete.json',{'status':'complete','seconds':time.time()-start,'new_base_fits':0,'new_weight_fits':0,'new_map_fits':0,'blind_scored':False,'publication':False,'submission':False,'files_sha256':{p.name:sha(p) for p in out.iterdir() if p.is_file()}});event('private_P5_complete',seconds=time.time()-start,no_new_fits=True)
if __name__=='__main__':
 from threadpoolctl import threadpool_limits
 with threadpool_limits(limits=2):main()
