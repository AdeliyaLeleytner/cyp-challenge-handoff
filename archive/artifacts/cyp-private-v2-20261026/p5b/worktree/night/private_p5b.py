"""Historical fixed-expert meta-fit only; no base models, features or calibration fitted."""
from pathlib import Path
import os,json,time,signal,shutil,importlib.metadata
import numpy as np,pandas as pd
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from .private_p1 import T,METRICS,sha,save,require,scores
from .private_p5 import mix,fixed_map
from .admet_full_math import blend_weight
ROOT=Path(__file__).resolve().parents[1]
def read(record,ids,truth,columns):
 require(sha(record['path'])==record['sha256'],'Input vector changed');d=pd.read_csv(record['path']).set_index('Molecule_Name');require(d.index.is_unique and set(d.index)==set(ids),'Vector IDs mismatch');d=d.loc[ids];require(d.SMILES.tolist()==truth.loc[ids,'SMILES'].tolist(),'Vector SMILES mismatch');a=d[columns].to_numpy(float);require(np.isfinite(a).all(),'Nonfinite vector');return a

def main():
 start=time.monotonic();c=json.loads((ROOT/'private_p5b_config.json').read_text());signal.signal(signal.SIGALRM,lambda *args:(_ for _ in ()).throw(TimeoutError('P5b10minute limit')));signal.alarm(c['timeout_seconds']);out=Path(c['output_dir']);out.mkdir(parents=True,exist_ok=False);require(sha(ROOT/'official_scoring_functions.py')==c['scorer_sha256'],'Scorer changed');require(sha(c['manifest']['path'])==c['manifest']['sha256'],'Manifest changed');m=json.loads(Path(c['manifest']['path']).read_text())
 for record in m['files'].values():require(sha(record['path'])==record['sha256'],'Input hash changed')
 truth=pd.read_csv(m['files']['official_train']['path']).set_index('Molecule_Name');frozen={r['context']:r for r in json.loads(Path(m['files']['fixed_P5']['path']).read_text())};EP=[x.split('_')[0] for x in T];metrics=[];per=[];deltas=[];identity=[];allweights={}
 save(out/'run-identity.json',{'config':c,'manifest_sha256':c['manifest']['sha256'],'scope':'Original-incumbent anchored historical expert combination','base_fits':0,'new_feature_values':0,'new_calibration_fits':0,'new_coefficient_fits':8,'no_global_OOF_substitution':True,'source_limits':m['provenance'],'packages':{x:importlib.metadata.version(x) for x in ['numpy','pandas','scipy','rdkit']}})
 for name,spec in m['cohorts'].items():
  tr=spec['train_ids'];qu=spec['query_ids'];require(not set(tr)&set(qu),'Outer overlap');N=read(spec['native_oof'],tr,truth,EP);H=read(spec['h6_oof'],tr,truth,T);y=truth.loc[tr,T].to_numpy(float);lo=truth.loc[tr,[x+'_conf_low' for x in T]].to_numpy(float);hi=truth.loc[tr,[x+'_conf_high' for x in T]].to_numpy(float);new=[];fits={};old=np.array(frozen[name]['feature_weights'])
  for j,target in enumerate(T):
   w,fit=blend_weight(y[:,j:j+1],N[:,j:j+1],H[:,j:j+1],lo[:,j:j+1],hi[:,j:j+1]);require(0<=w<=1,'Nonconvex weight');new.append(w);fits[target]=fit
  new=np.array(new);record={'feature_weight_convention':'(1-w)*original_native+w*frozen_H6_feature_only','refit_original_OOF':new.tolist(),'fixed_P5':old.tolist(),'training_fit':fits,'training_label_masks':spec['label_masks'],'selection_uses_query_labels':False,'tie_rule':'smallest weighted-endpoint-median minimizer','H6_candidate_and_params_frozen':{'candidate':spec['selected_H6_candidate'],'params':spec['selected_H6_params']}};save(out/f'{name}-weights.json',record);allweights[name]=record
  # Outer truth is selected only after the new coefficients are persisted.
  native=read(spec['native_query'],qu,truth,T);head=read(spec['h6_query'],qu,truth,T);native_served=read(spec['native_served'],qu,truth,T);fixed_raw=read(spec['fixed_P5_raw'],qu,truth,T);fixed_served=read(spec['fixed_P5_fixed_original_served'],qu,truth,T);raw={'incumbent':native,'fixed_P5':mix(native,head,old,True),'refit_original_OOF':mix(native,head,new,True)};require(np.allclose(raw['fixed_P5'],fixed_raw,atol=1e-12,rtol=0),'FixedP5 changed');op=frozen[name];mapped=lambda z:fixed_map(z,np.array(op['original_raw_reference_mean']),op['calibration'],op['floor']);require(np.allclose(mapped(native),native_served,atol=1e-12,rtol=0),'Native serving identity');require(np.allclose(mapped(fixed_raw),fixed_served,atol=1e-12,rtol=0),'FixedP5 serving identity');identity.append({'cohort':name,'fixed_P5_raw_max_abs':float(abs(raw['fixed_P5']-fixed_raw).max()),'native_served_max_abs':float(abs(mapped(native)-native_served).max()),'fixed_P5_served_max_abs':float(abs(mapped(fixed_raw)-fixed_served).max())})
  frame=truth.loc[qu];qy=frame[T].to_numpy(float);ql=frame[[x+'_conf_low' for x in T]].to_numpy(float);qh=frame[[x+'_conf_high' for x in T]].to_numpy(float);groups=[]
  for s in frame.SMILES:
   mol=Chem.MolFromSmiles(s);groups.append(Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(mol),isomericSmiles=False) or 'acyclic:'+Chem.MolToInchiKey(mol).split('-')[0])
  groups=np.array(groups);members=[np.flatnonzero(groups==g) for g in np.unique(groups)];rng=np.random.default_rng(c['bootstrap_seed']);draws=[np.concatenate([members[k] for k in rng.integers(0,len(members),len(members))]) for _ in range(c['bootstrap_samples'])]
  for lane in ['raw','fixed_original_served_diagnostic']:
   vectors=raw if lane=='raw' else {key:mapped(z) for key,z in raw.items()};points={};boot={}
   for arm,z in vectors.items():
    data=frame[['SMILES']].reset_index()
    for j,target in enumerate(T):data[target]=z[:,j]
    path=out/f'{name}-{lane}-{arm}.csv'
    if arm=='incumbent':shutil.copyfile(spec['native_query' if lane=='raw' else 'native_served']['path'],path)
    elif arm=='fixed_P5':shutil.copyfile(spec['fixed_P5_raw' if lane=='raw' else 'fixed_P5_fixed_original_served']['path'],path)
    else:data.to_csv(path,index=False,float_format='%.17g')
    points[arm]=scores(qy,z,ql,qh);metrics.append({'cohort':name,'lane':lane,'arm':arm,**points[arm]['macro']});per.extend({'cohort':name,'lane':lane,'arm':arm,'target':target,**value} for target,value in points[arm]['per_cyp'].items());boot[arm]=[]
    for ix in draws:
     sc=scores(qy[ix],z[ix],ql[ix],qh[ix]);boot[arm].append(np.array([[sc['per_cyp'][target][metric] for metric in METRICS] for target in T]))
    boot[arm]=np.array(boot[arm])
   for candidate,control in [('refit_original_OOF','incumbent'),('refit_original_OOF','fixed_P5'),('fixed_P5','incumbent')]:
    distribution=boot[candidate]-boot[control];point=np.array([[points[candidate]['per_cyp'][target][metric]-points[control]['per_cyp'][target][metric] for metric in METRICS] for target in T])
    for target,dd,pp in [('macro',distribution.mean(1),point.mean(0))]+[(target,distribution[:,j],point[j]) for j,target in enumerate(T)]:
     a,b=np.quantile(dd,[.025,.975],axis=0)
     for j,metric in enumerate(METRICS):deltas.append({'cohort':name,'lane':lane,'contrast':candidate+' minus '+control,'target':target,'metric':metric,'delta':pp[j],'lower95':a[j],'upper95':b[j]})
  print(json.dumps({'cohort_complete':name,'weights':record,'raw_metrics':{arm:scores(qy,z,ql,qh)['macro'] for arm,z in raw.items()}}),flush=True)
 pd.DataFrame(metrics).to_csv(out/'metrics.csv',index=False);pd.DataFrame(per).to_csv(out/'per-cyp-metrics.csv',index=False);pd.DataFrame(deltas).to_csv(out/'paired-deltas.csv',index=False);save(out/'IDENTITY_CONTROLS.json',identity);save(out/'COMPLETE.json',{'status':'complete','seconds':time.monotonic()-start,'base_fits':0,'feature_changes':0,'calibration_fits':0,'coefficient_fits':8,'weights':allweights,'raw_primary':True,'serving_diagnostic_only':True,'historical_reused_cohorts':True,'bootstrap_samples':c['bootstrap_samples'],'bootstrap_seed':c['bootstrap_seed'],'bootstrap_unit':'P5 nonisomericMurcko;acyclic connectivity fallback','no_publication':True,'no_submission':True,'source_sha256':sha(__file__),'file_hashes':{f.name:sha(f) for f in out.iterdir() if f.is_file()}});print(json.dumps({'status':'complete','seconds':time.monotonic()-start,'base_fits':0,'coefficient_fits':8}),flush=True)
if __name__=='__main__':main()
