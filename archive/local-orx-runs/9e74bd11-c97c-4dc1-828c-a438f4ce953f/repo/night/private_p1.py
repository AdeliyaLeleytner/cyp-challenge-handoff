"""Private fixed-input operator replay. No training or network/dispatch paths."""
from pathlib import Path
import json,hashlib,os,time,shutil,importlib.metadata
import numpy as np,pandas as pd
from scipy.stats import rankdata,spearmanr,kendalltau,wasserstein_distance
from rdkit import Chem,RDLogger
from rdkit.Chem.Scaffolds import MurckoScaffold
from official_scoring_functions import rae_soft_threshold_absolute_error
ROOT=Path(__file__).resolve().parents[1];T=[f'{x}_pIC50_direct_inhibition' for x in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']];METRICS=['ST_RAE','MAE','R2','Spearman','Kendall'];RDLogger.DisableLog('rdApp.*')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def require(x,m):
 if not x:raise ValueError(m)
def event(name,**v):print(json.dumps({'event':name,**v},allow_nan=False),flush=True)
def transform(candidate,anchor,operator):
 c=np.asarray(candidate,float);b=np.asarray(anchor,float)
 require(c.shape==b.shape and c.ndim==2 and len(c)>1,'Invalid shapes');require(np.isfinite(c).all() and np.isfinite(b).all(),'Nonfinite inputs')
 require(np.all(np.std(c,axis=0,ddof=1)>0) and np.all(np.std(b,axis=0,ddof=1)>0),'Constant input; no silent fallback')
 if operator=='identity' or np.array_equal(c,b):return c.copy()
 if operator=='moment':return b.mean(0)+b.std(0,ddof=1)*(c-c.mean(0))/c.std(0,ddof=1)
 if operator=='quantile':return np.column_stack([np.interp(rankdata(c[:,j],method='average')-1,np.arange(len(b)),np.sort(b[:,j])) for j in range(c.shape[1])])
 raise ValueError('Unregistered operator')
def read_vector(path,ids,smiles):
 f=pd.read_csv(path);require(f.Molecule_Name.is_unique and f.Molecule_Name.tolist()==list(ids),'Exact prediction IDs/order mismatch');require(f.SMILES.tolist()==list(smiles),'Exact SMILES mismatch');p=f[T].to_numpy(float);require(np.isfinite(p).all(),'Nonfinite predictions');return p

def scores(y,p,lo,hi):
 rows=[]
 for j in range(4):
  m=np.isfinite(y[:,j]);v=y[m,j];q=p[m,j];l=lo[m,j];h=hi[m,j];require(len(v)>1 and np.isfinite(q).all(),'Insufficient observed labels');den=(np.maximum(l-v.mean(),0)+np.maximum(v.mean()-h,0)).sum();require(den>0,'Undefined ST denominator');var=np.sum((v-v.mean())**2)
  rows.append({'ST_RAE':float(rae_soft_threshold_absolute_error(v,q,y_true_lower=l,y_true_upper=h)),'MAE':float(np.abs(v-q).mean()),'R2':float(1-np.sum((v-q)**2)/var) if var>0 else None,'Spearman':float(spearmanr(v,q).statistic) if np.std(q)>0 else None,'Kendall':float(kendalltau(v,q).statistic) if np.std(q)>0 else None,'n':len(v)})
 return {'macro':{k:float(np.mean([r[k] for r in rows])) if all(r[k] is not None for r in rows) else None for k in METRICS},'per_cyp':dict(zip(T,rows))}

def main():
 os.umask(0o077);start=time.time();cfg=json.loads((ROOT/'private_p1_config.json').read_text());out=Path(cfg['output_dir']);require(not out.exists() or not any(out.iterdir()),'Output already populated');out.mkdir(parents=True,exist_ok=True)
 require(sha(ROOT/'official_scoring_functions.py')==cfg['scorer_sha256'],'Scorer drift')
 for k,v in cfg['files'].items():require(sha(v['path'])==v['sha256'],'Input hash changed:'+k)
 train=pd.read_csv(cfg['files']['official_train']['path']).set_index('Molecule_Name');blind=pd.read_csv(cfg['files']['official_blind']['path']);require(set(blind)=={'Molecule_Name','SMILES'} and not set(blind.Molecule_Name)&set(train.index),'Blind must contain structures only and disjoint IDs');coh=json.loads(Path(cfg['files']['cohorts']['path']).read_text())['cohorts']
 save(out/'run-identity.json',{'config':cfg,'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','rdkit']},'no_base_fits':True,'no_target_fitted_operator_parameters':True,'no_network':True,'no_publication':True,'no_submission':True,'blind_labels_loaded':False,'caveat':'Primary actual served-to-served replay; raw-to-raw is secondary. Existing outer cohorts are reused diagnostics.'})
 metrics=[];per=[];diag=[];boot=[];controls=[]
 for context in ['own750','briford529','blind750']:
  isblind=context=='blind750';ids=blind.Molecule_Name.tolist() if isblind else coh[context]['test_ids'];frame=blind[['Molecule_Name','SMILES']].copy() if isblind else train.loc[ids].reset_index()[['Molecule_Name','SMILES']]
  if not isblind:
   truth=train.loc[ids];y=truth[T].to_numpy(float);lo=truth[[t+'_conf_low' for t in T]].to_numpy(float);hi=truth[[t+'_conf_high' for t in T]].to_numpy(float)
   groups=[]
   for s in frame.SMILES:
    mol=Chem.MolFromSmiles(s);groups.append(Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(mol),isomericSmiles=False) or 'acyclic:'+Chem.MolToInchiKey(mol).split('-')[0])
   groups=np.array(groups);members=[np.flatnonzero(groups==g) for g in np.unique(groups)];rng=np.random.default_rng(cfg['bootstrap_seed']);samples=[np.concatenate([members[k] for k in rng.integers(0,len(members),len(members))]) for _ in range(cfg['bootstrap_samples'])]
  for lane in ['served','raw']:
   inputs={model:read_vector(cfg['files'][context+'_'+lane+'_'+model]['path'],ids,frame.SMILES) for model in ['original','corrected','H6']};anchor=inputs['original'];vectors={}
   for model,candidate in inputs.items():
    for op in cfg['operators']:
     z=transform(candidate,anchor,op);require(np.isfinite(z).all() and np.all(z.std(0,ddof=1)>=.01),'Output finite/spread failure');key=model+'__'+op;vectors[key]=z
     if model=='original':require(np.array_equal(z,anchor),'B-to-B invariance failure');controls.append({'context':context,'lane':lane,'operator':op,'exact_B_to_B':True})
     f=frame.copy()
     for j,t in enumerate(T):f[t]=z[:,j]
     fn=out/f'{context}__{lane}__{key}.csv'
     if op=='identity' or model=='original':shutil.copyfile(cfg['files'][context+'_'+lane+'_'+model]['path'],fn)
     else:f.to_csv(fn,index=False,float_format='%.17g')
     for j,t in enumerate(T):
      order=np.argsort(candidate[:,j],kind='stable');require(np.all(np.diff(z[order,j])>=-1e-12),'Map broke ordering')
      diag.append({'context':context,'lane':lane,'model':model,'operator':op,'target':t,'input_unique':len(np.unique(candidate[:,j])),'output_unique':len(np.unique(z[:,j])),'anchor_unique':len(np.unique(anchor[:,j])),'input_tied_rows':len(z)-len(np.unique(candidate[:,j])),'output_tied_rows':len(z)-len(np.unique(z[:,j])),'output_mean':z[:,j].mean(),'output_sd':z[:,j].std(ddof=1),'output_min':z[:,j].min(),'output_max':z[:,j].max(),'W1_marginal_to_anchor':wasserstein_distance(z[:,j],anchor[:,j]),'input_output_Spearman':spearmanr(candidate[:,j],z[:,j]).statistic,'no_new_clipping':True,'empirical_marginal_exact':bool(np.array_equal(np.sort(z[:,j]),np.sort(anchor[:,j])))})
     if not isblind:
      s=scores(y,z,lo,hi);metrics.append({'cohort':context,'lane':lane,'model':model,'operator':op,**s['macro']});per.extend({'cohort':context,'lane':lane,'model':model,'operator':op,'target':t,**v} for t,v in s['per_cyp'].items());event('replay_score',cohort=context,lane=lane,model=model,operator=op,macro=s['macro'])
   if isblind:event('blind_vectors_saved_unscored',rows=len(frame),lane=lane,vectors=len(vectors));continue
   keys=['original__identity']+[m+'__'+op for m in ['corrected','H6'] for op in cfg['operators']];draws={k:{metric:[] for metric in METRICS} for k in keys}
   for ix in samples:
    for key in keys:
     try:r=scores(y[ix],vectors[key][ix],lo[ix],hi[ix])['macro']
     except ValueError:r={m:None for m in METRICS}
     for metric in METRICS:draws[key][metric].append(r[metric] if r[metric] is not None else np.nan)
   point={k:scores(y,vectors[k],lo,hi)['macro'] for k in keys}
   for model in ['corrected','H6']:
    for op in cfg['operators']:
     key=model+'__'+op;references=['original__identity']+([model+'__identity'] if op!='identity' else [])
     for ref in references:
      for metric in METRICS:
       d=np.asarray(draws[key][metric])-np.asarray(draws[ref][metric]);d=d[np.isfinite(d)];require(len(d)>0,'No valid paired bootstrap draws');boot.append({'cohort':context,'lane':lane,'model':model,'operator':op,'reference':ref,'metric':metric,'delta':point[key][metric]-point[ref][metric],'lower95':np.quantile(d,.025),'upper95':np.quantile(d,.975),'valid_samples':len(d),'requested_samples':cfg['bootstrap_samples'],'note':'Paired Murcko-proxy bootstrap conditional on predictions; reused cohorts, no selection correction'})
 pd.DataFrame(metrics).to_csv(out/'all-metrics.csv',index=False);pd.DataFrame(per).to_csv(out/'per-cyp-metrics.csv',index=False);pd.DataFrame(diag).to_csv(out/'operator-diagnostics.csv',index=False);pd.DataFrame(boot).to_csv(out/'paired-bootstrap.csv',index=False);save(out/'identity-controls.json',controls)
 save(out/'complete.json',{'status':'complete','seconds':time.time()-start,'base_fits':0,'target_fitted_parameters':0,'publication':False,'submission':False,'blind_scored':False,'files_sha256':{p.name:sha(p) for p in out.iterdir() if p.is_file()}});event('private_P1_complete',seconds=time.time()-start,base_fits=0,blind_scored=False)
if __name__=='__main__':
 from threadpoolctl import threadpool_limits
 with threadpool_limits(limits=2):main()
