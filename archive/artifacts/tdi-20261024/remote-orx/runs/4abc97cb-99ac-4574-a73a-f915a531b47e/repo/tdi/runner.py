"""Bounded, immutable TDI recipe comparisons; outer labels enter only final readout."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, signal, subprocess, sys, time
import numpy as np
import pandas as pd
from .data import sha, write_json
from .evaluation import TARGETS, score, fit_native_policy, fit_policy, fit_pool_policy, fit_endpoint_pool_policy, apply_policy

METHODS={
 'jeremy_lgbm':{'learner':'jeremy_lgbm','feature':'X','pca':'none','gpu':False},
 'tabicl_native':{'learner':'jeremy_tabicl','feature':'X_adme','pca':'native_global','gpu':True},
 'tabicl_local':{'learner':'jeremy_tabicl','feature':'X_adme','pca':'fold_local','gpu':True},
 'tabicl_chemeleon_adme':{'learner':'jeremy_tabicl','feature':'X_chemeleon_adme','pca':'fold_local','gpu':True},
 'tabicl_foundation':{'learner':'jeremy_tabicl','feature':'X_foundation','pca':'fold_local','gpu':True},
 'extra_trees':{'learner':'extra_trees','feature':'X','pca':'none','gpu':False},
 'tanimoto_knn':{'learner':'tanimoto_knn','feature':'X','pca':'none','gpu':False},
 'hauser_lgbm':{'learner':'hauser_lgbm','feature':'X_hauser','pca':'none','gpu':False},
}

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def cohort_arrays(prep,cohort,seed):
 d=prep/'cohorts'/cohort;dev=np.load(d/'train_indices.npy')
 query=np.load(d/('query_indices.npy' if cohort=='full' else 'holdout_indices.npy'))
 # Preserve exact author Butina full-CV ruler; strict outer pools have grouped folds.
 folds=np.load(prep/f'folds_native_seed{seed}.npy') if cohort=='full' else np.load(d/f'folds_seed{seed}.npy')
 return dev,query,folds

def component(job):
 from .learners import fit_predict
 import torch,joblib,importlib.metadata
 torch.set_num_threads(2)
 prep=Path(job['prepared_dir']);out=Path(job['out']);out.mkdir(parents=True,exist_ok=True)
 identity=hashlib.sha256(json.dumps(job,sort_keys=True).encode()).hexdigest()
 done=out/'complete.json'
 if done.exists():
  assert json.loads(done.read_text())['job_sha256']==identity;return
 cfg=METHODS[job['method']];dev,query,folds=cohort_arrays(prep,job['cohort'],job['seed']);j=job['target']
 full_y=np.load(prep/'y_train.npy');y=np.full(len(full_y),np.nan);y[dev]=full_y[dev,j]
 X=np.load(prep/f"{cfg['feature']}_train.npy",mmap_mode='r')
 Q=np.load(prep/f"{cfg['feature']}_test.npy",mmap_mode='r')[query] if job['cohort']=='full' else X[query]
 oof=np.full(len(dev),np.nan);hard=np.full(len(dev),np.nan);qp=[];qh=[];metadata=[]
 start=time.time()
 for f in range(6):
  dest=out/f'fit{f}.npz';meta=out/f'fit{f}.json'
  if not dest.exists() or not meta.exists():
   tr=dev if f==5 else dev[folds!=f];va=np.array([],dtype=int) if f==5 else dev[folds==f]
   kwargs={'pca_scope':cfg['pca']} if cfg['gpu'] else {}
   if cfg['pca']=='native_global':kwargs['pca_fit_idx']=dev
   fit=fit_predict(cfg['learner'],X,y,tr,va,Q,seed=job['seed'],device='cuda' if cfg['gpu'] else 'cpu',n_jobs=2,return_model=f==5,**kwargs)
   np.savez_compressed(dest,valid_proba=fit['valid_proba'],valid_hard=fit['valid_hard'],query_proba=fit['query_proba'],query_hard=fit['query_hard'])
   if f==5:
    if not cfg['gpu']:joblib.dump(fit['model'],out/'full_model.joblib',compress=3)
    if fit.get('transform') is not None:joblib.dump(fit['transform'],out/'full_transform.joblib',compress=3)
   write_json(meta,{'job_sha256':identity,'fit':f,'metadata':fit['metadata'],'npz_sha256':sha(dest)})
   print(json.dumps({'event':'fit_done','cohort':job['cohort'],'seed':job['seed'],'method':job['method'],'target':j,'fold':f,'seconds':time.time()-start}),flush=True)
   del fit
   if cfg['gpu']:torch.cuda.empty_cache()
  info=json.loads(meta.read_text());assert info['job_sha256']==identity and sha(dest)==info['npz_sha256']
  a=np.load(dest);metadata.append(info)
  if f<5:oof[folds==f]=a['valid_proba'];hard[folds==f]=a['valid_hard'];qp.append(a['query_proba']);qh.append(a['query_hard'])
  else:fullprob=a['query_proba'];fullhard=a['query_hard']
 assert np.isfinite(oof).all() and np.isfinite(hard).all()
 np.savez_compressed(out/'predictions.npz',oof=oof,hard_oof=hard,query_full=fullprob,query_full_hard=fullhard,query_bag=np.mean(qp,axis=0),query_hard_bag=np.mean(qh,axis=0),dev_indices=dev,query_indices=query)
 write_json(out/'complete.json',{'status':'complete','job_sha256':identity,'seconds':time.time()-start,'prediction_sha256':sha(out/'predictions.npz'),'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scikit-learn','lightgbm','torch','tabicl']}})
 print(json.dumps({'event':'component_done','job':job,'seconds':time.time()-start}),flush=True)

def worker(path):
 job=json.loads(Path(path).read_text())
 if job['kind']=='component':component(job)
 else:
  from .hauser_native import run_native
  run_native(job['prepared_dir'],job['out'],cohort=job['cohort'],raw_screen_path=job['raw_screen'])

def launch(cfg):
 out=Path(cfg['output_dir']);out.mkdir(parents=True,exist_ok=True);write_json(out/'config.json',cfg)
 prep=Path(cfg['prepared_dir'])
 if cfg['prepare']:
  from .data import prepare
  from .embeddings import prepare_embeddings
  if not (prep/'metadata.json').exists():prepare({'assets':cfg['assets'],'output_dir':str(prep.parent),'seeds':cfg['seeds'],'jeremy_splits':str(Path('vendor/jeremy/splits.py').resolve())})
  prepare_embeddings(prep,Path(cfg['assets']['tdi_train']).parent/'weights')
 jobs=[]
 for cohort in cfg['cohorts']:
  for seed in cfg['seeds']:
   for method in cfg['methods']:
    for target in range(2):
     d=out/'results'/cohort/f'seed{seed}'/method/f'target{target}';d.mkdir(parents=True,exist_ok=True)
     job={'kind':'component','cohort':cohort,'seed':seed,'method':method,'target':target,'prepared_dir':str(prep),'out':str(d),'input_manifest_sha256':sha(prep/'metadata.json'),'embedding_manifest_sha256':sha(prep/'embeddings_manifest.json')}
     p=d/'job.json';write_json(p,job)
     if not (d/'complete.json').exists():jobs.append((METHODS[method]['gpu'],p))
 if cfg.get('hauser_native'):
  for cohort in cfg['cohorts']:
   d=out/'hauser_native'/cohort;d.mkdir(parents=True,exist_ok=True)
   job={'kind':'hauser_native','cohort':cohort,'prepared_dir':str(prep),'out':str(d),'raw_screen':str(Path(cfg['assets']['tdi_train']).parent/'single_concentration.csv')};p=d/'job.json';write_json(p,job)
   if not (d/'complete.json').exists():jobs.append((False,p))
 running={};slots=[('gpu'+str(g),True,g) for g in cfg['gpus']]+[('cpu'+str(k),False,None) for k in range(cfg['cpu_slots'])]
 def cancel(signum,frame):raise SystemExit(128+signum)
 signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
 try:
  while jobs or running:
   for slot,isgpu,gpu in slots:
    if slot in running:continue
    eligible=next((i for i,(g,_) in enumerate(jobs) if g==isgpu),None)
    if eligible is None:continue
    _,p=jobs.pop(eligible);log=(p.parent/'worker.log').open('a');env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu) if isgpu else '')
    process=subprocess.Popen([sys.executable,'-u','-m','tdi.runner','--worker',str(p)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);running[slot]=(process,log,p)
    print(json.dumps({'event':'job_started','slot':slot,'path':str(p),'pending':len(jobs)}),flush=True)
   for slot,(proc,log,p) in list(running.items()):
    rc=proc.poll()
    if rc is None:continue
    if rc:raise RuntimeError(f'Worker failed {p}: exit{rc}')
    log.close();del running[slot];print(json.dumps({'event':'job_finished','path':str(p),'pending':len(jobs),'running':len(running)}),flush=True)
   time.sleep(3)
 finally:
  for proc,log,p in running.values():
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
  if running:time.sleep(3)
  for proc,log,p in running.values():
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   proc.wait();log.close()
 collect(cfg)

def load_predictions(root,cohort,seed,method):
 paths=[root/'results'/cohort/f'seed{seed}'/method/f'target{j}' for j in range(2)]
 arrays=[]
 for p in paths:
  d=json.loads((p/'complete.json').read_text());assert sha(p/'predictions.npz')==d['prediction_sha256'];arrays.append(np.load(p/'predictions.npz'))
 return {k:np.column_stack([a[k] for a in arrays]) for k in ['oof','hard_oof','query_full','query_full_hard','query_bag']}

def collect(cfg):
 out=Path(cfg['output_dir']);prep=Path(cfg['prepared_dir']);base=Path(cfg.get('base_results',cfg['output_dir']));train=pd.read_csv(prep/'train.csv');test=pd.read_csv(prep/'test.csv');y=np.load(prep/'y_train.npy');results={}
 caruana=module('native_caruana',Path('vendor/jeremy/caruana.py')).caruana_bagged_ensemble
 candidates=list(dict.fromkeys(['jeremy_lgbm','tabicl_native']+cfg['methods']))
 for cohort in cfg['cohorts']:
  dev,q,folds=cohort_arrays(prep,cohort,42);ids=train.iloc[dev].Molecule_Name.tolist();query_ids=(test if cohort=='full' else train).iloc[q].Molecule_Name.tolist()
  loaded={}
  for method in [n for n in candidates if n!='hauser_native']:
   root=out if method in cfg['methods'] else base
   each=[load_predictions(root,cohort,s,method) for s in cfg['seeds']]
   loaded[method]={k:np.mean([a[k] for a in each],axis=0) for k in each[0]}
  if cfg.get('include_hauser_candidate'):
   hp=base/'hauser_native'/cohort
   assert pd.read_csv(hp/'oof_ids.csv').Molecule_Name.tolist()==ids
   assert pd.read_csv(hp/'query_ids.csv').Molecule_Name.tolist()==query_ids
   loaded['hauser_native']={'oof':np.load(hp/'oof_proba.npy'),'query_bag':np.load(hp/'query_proba.npy')}
   if 'hauser_native' not in candidates:candidates.append('hauser_native')
  native_names=['jeremy_lgbm','tabicl_native'];native=fit_native_policy({n:loaded[n]['hard_oof'] for n in native_names},y[dev],ids=ids,caruana_fn=caruana)
  soft=fit_pool_policy({n:loaded[n]['oof'] for n in candidates},y[dev],folds,ids=ids)
  if cfg.get('endpointwise_selection'):
   alternative=fit_endpoint_pool_policy({n:loaded[n]['oof'] for n in candidates},y[dev],folds,ids=ids)
   if alternative['selection_metrics']['macro_mcc']>soft['selection_metrics']['macro_mcc']:soft=alternative
  single={n:load_predictions(base,cohort,42,n) for n in native_names}
  native42=fit_native_policy({n:single[n]['hard_oof'] for n in native_names},y[dev],ids=ids,caruana_fn=caruana)
  policies={'native_reference':native,'native_seed42':native42,'soft_candidate':soft};predictions={};d=out/'evaluation'/cohort;d.mkdir(parents=True,exist_ok=True)
  for name,policy in policies.items():
   query={n:(single[n]['query_full_hard'] if name=='native_seed42' else loaded[n]['query_full_hard' if name=='native_reference' else 'query_bag']) for n in policy['models']}
   pred=apply_policy(query,policy);prob=apply_policy(query,policy,return_probabilities=True);predictions[name]=pred
   write_json(d/(name+'_policy.json'),policy)
   df=pd.DataFrame(pred,columns=TARGETS);df.insert(0,'Molecule_Name',query_ids);df.to_csv(d/(name+'_predictions.csv'),index=False)
   np.save(d/(name+'_probabilities.npy'),prob)
  hauser_path=base/'hauser_native'/cohort
  if (hauser_path/'complete.json').exists():
   assert pd.read_csv(hauser_path/'query_ids.csv').Molecule_Name.tolist()==query_ids
   predictions['hauser_native']=np.load(hauser_path/'query_hard.npy')
   assert predictions['hauser_native'].shape==(len(q),2)
   hdf=pd.DataFrame(predictions['hauser_native'],columns=TARGETS);hdf.insert(0,'Molecule_Name',query_ids);hdf.to_csv(d/'hauser_native_predictions.csv',index=False)
  # Freeze every setting and prediction before reading/evaluating query labels.
  lock={'outer_labels_used_for_selection':False,'methods':candidates,'seeds':cfg['seeds'],'policy_sha256':{n:sha(d/(n+'_policy.json')) for n in policies},'prediction_sha256':{n:sha(d/(n+'_predictions.csv')) for n in policies},'query_ids':query_ids}
  write_json(d/'prediction-lock.json',lock)
  summary={'cohort':cohort,'dev_rows':len(dev),'query_rows':len(q),'native_seed42_development':native42['selection_metrics'],'native_development':native['selection_metrics'],'candidate_development':soft['selection_metrics'],'selected_candidate_models':soft['models']}
  if cohort!='full':
   summary['holdout']={n:score(y[q],a,query_ids) for n,a in predictions.items()};summary['reference_best']=max((n for n in summary['holdout'] if n!='soft_candidate'),key=lambda n:summary['holdout'][n]['macro_mcc']);summary['macro_delta']=summary['holdout']['soft_candidate']['macro_mcc']-summary['holdout'][summary['reference_best']]['macro_mcc']
  else:
   df=test[['SMILES','Molecule_Name']].copy()
   for j,t in enumerate(TARGETS):df[t]=predictions['soft_candidate'][:,j]
   df.to_csv(out/'submission_tdi.csv',index=False)
  write_json(d/'summary.json',summary);results[cohort]=summary
  print(json.dumps({'event':'tdi_result','cohort':cohort,'delta':summary.get('macro_delta'),'holdout':{n:a['macro_mcc'] for n,a in summary.get('holdout',{}).items()},'candidate_models':soft['models']}),flush=True)
 gate=all(n in results and results[n].get('macro_delta',0)>0 for n in ['own750','briford529'])
 write_json(out/'summary.json',{'results':results,'qualified_on_both_holdouts':gate,'submission_sha256':sha(out/'submission_tdi.csv') if (out/'submission_tdi.csv').exists() else None,'note':'Native reference is two-seed available-kit re-execution, not a guaranteed copy of broader leaderboard ensemble. Soft candidate uses train-OOF selector and fivefold probability bagging.'})
 write_json(out/'complete.json',{'status':'complete','summary_sha256':sha(out/'summary.json')})
 print(json.dumps({'event':'tdi_campaign_stage_complete','qualified':gate}),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--worker');a=parser.parse_args()
 if a.worker:worker(a.worker)
 else:launch(json.loads(Path('tdi_config.json').read_text()))
