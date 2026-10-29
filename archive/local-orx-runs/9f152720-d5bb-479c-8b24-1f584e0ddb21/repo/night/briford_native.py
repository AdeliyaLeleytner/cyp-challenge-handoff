"""Execute pinned author algorithms; local adapters replace Workbench storage only."""
from pathlib import Path
import argparse, ast, contextlib, hashlib, importlib.util, json, os, runpy, subprocess, sys, time, types
import numpy as np
import pandas as pd

VENDOR=Path(__file__).resolve().parents[1]/'vendor/briford_native'
MODELS={'union18':'cyp-reg-chemprop-union-p30','mtaux8':'cyp-reg-chemprop-mt-aux-100','2d6isoform6':'cyp-reg-chemprop-2d6-isoform','2d6single':'cyp-reg-chemprop-2d6-single'}
PRIMARY=[f'{i}_pic50_direct_inhibition' for i in ['cyp3a4','cyp2c9','cyp2d6','cyp1a2']]
DATA_KEYS={'comp_chem/openadmet/cyp/training/inhibition':'inhibition.csv','comp_chem/openadmet/cyp/training/single_concentration':'single_concentration.csv','comp_chem/openadmet/cyp/training/tdi':'tdi.csv','comp_chem/openadmet/cyp/training/emax':'emax.csv','comp_chem/chembl/cyp_inhibition/all_isoforms':'chembl_all_isoforms.csv','comp_chem/pubchem/cyp_inhibition/all_isoforms':'pubchem_all_isoforms.csv'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,allow_nan=False,default=lambda x:x.item() if isinstance(x,np.generic) else str(x))+'\n')
def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def packages():
 for name in ['workbench','workbench.api','workbench.utils','workbench.training','workbench.endpoints']:
  m=types.ModuleType(name);m.__path__=[];sys.modules[name]=m
 return sys.modules['workbench.api']
def defaults():
 tree=ast.parse((VENDOR/'chemprop.template').read_text());return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DEFAULT_HYPERPARAMETERS' for t in n.targets))
def sources():return {p.name:sha(p) for p in VENDOR.iterdir() if p.is_file()}
def execute_script(name,args=()):
 old=sys.argv;sys.argv=[name,*args]
 try:return runpy.run_path(str(VENDOR/name),run_name='__main__')
 finally:sys.argv=old

def prepare(cfg):
 from rdkit import Chem
 out=Path(cfg['prepared_dir']);raw=Path(cfg['raw_dir'])
 if (out/'complete.json').exists():raise FileExistsError(out)
 out.mkdir(parents=True,exist_ok=True)
 for name,expected in cfg['raw_sha256'].items():
  if sha(raw/name)!=expected:raise ValueError('Raw data hash mismatch:'+name)
 api=packages();frames={'openadmet_cyp_f1':pd.read_csv(raw/'inhibition.csv')};captures={}
 class PublicData:
  def get(self,name):return pd.read_csv(raw/DATA_KEYS[name])
 class Noop:
  def set_owner(self,*a,**k):pass
  def to_endpoint(self,*a,**k):return self
  def test_inference(self):pass
  def cross_fold_inference(self):pass
 class FeatureSet:
  def __init__(self,name):self.name=name
  def pull_dataframe(self):return frames[self.name].copy()
  def to_model(self,**kw):
   captures[kw['name']]={'feature_set':self.name,'target_columns':kw['target_column'],'hyperparameters':kw['hyperparameters'],'model_type':kw['model_type'],'feature_list':kw['feature_list']};return Noop()
 class DataSource:
  def __init__(self,df,**kw):self.df=df
  def to_features(self,name,**kw):frames[name]=self.df.copy()
 api.PublicData=PublicData;api.FeatureSet=FeatureSet;api.DataSource=DataSource
 api.ModelType=types.SimpleNamespace(UQ_REGRESSOR='uq_regressor');api.ModelFramework=types.SimpleNamespace(CHEMPROP='chemprop')
 load_module('workbench.utils.multi_task',VENDOR/'multi_task.py')
 execute_script('cyp_aux_features.py');execute_script('cyp_union_features.py')
 execute_script('cyp_chemprop_mt_aux_100.py');execute_script('cyp_chemprop_union.py',['--public-weight','0.30'])
 for scope in ['isoform','single']:execute_script('cyp_chemprop_2d6.py',['--scope',scope])
 splits=load_module('workbench.training.splits',VENDOR/'splits.py')
 specs={};blind=pd.read_csv(cfg['official_test'])
 for short,model_name in MODELS.items():
  cap=captures[model_name];df=frames[cap['feature_set']];targets=cap['target_columns']
  df=df.dropna(subset=['smiles']);df=df[df[targets].notna().any(axis=1)].copy()
  valid=[i for i,s in enumerate(df.smiles) if isinstance(s,str) and s.strip() and Chem.MolFromSmiles(s) is not None]
  dropped=len(df)-len(valid);df=df.iloc[valid].reset_index(drop=True)
  hp={**defaults(),**cap['hyperparameters']};hp['butina_cutoff']=None
  folds=splits.get_split_indices(df,n_splits=hp['n_folds'],strategy=hp['split_strategy'],test_size=.2,random_state=hp['seed'],butina_cutoff=None)
  # Storage only: pickle preserves native float precision, NaN, row order and column dtypes.
  df.to_pickle(out/f'{short}.pkl');df.to_csv(out/f'{short}.csv',index=False,float_format='%.17g')
  spec={'model_name':model_name,'targets':targets,'hyperparameters':hp,'feature_set':cap['feature_set'],'rows':len(df),'dropped_invalid':dropped,'target_counts':df[targets].notna().sum().astype(int).to_dict(),'data_sha256':sha(out/f'{short}.csv'),'folds':[{'train':a.tolist(),'validation':b.tolist()} for a,b in folds]}
  save(out/f'{short}.json',spec);specs[short]={k:v for k,v in spec.items() if k!='folds'}
  print(json.dumps({'event':'native_dataset_ready','member':short,'rows':len(df),'targets':len(targets),'fold_sizes':[[len(a),len(b)] for a,b in folds]}),flush=True)
 # Audit potential overlap; preserve native author's joining semantics, do not silently purge.
 def key(s):
  m=Chem.MolFromSmiles(s);return Chem.MolToInchiKey(m).split('-')[0] if m is not None else None
 testkeys={key(s) for s in blind.SMILES};train=frames['openadmet_cyp_union_f1'];overlap=train[train.smiles.map(key).isin(testkeys)]
 save(out/'native_overlap_audit.json',{'native_connectivity_test_overlap_rows':len(overlap),'ids':overlap.molecule_name.tolist(),'policy':'Report native-public-data overlap without changing the original recipe; no hidden challenge labels are loaded.'})
 manifest={'source_sha256':sources(),'raw_sha256':cfg['raw_sha256'],'models':specs,'base_official_rows':len(frames['openadmet_cyp_f1']),'union_rows_before_target_filter':len(frames['openadmet_cyp_union_f1']),'official_test_sha256':sha(cfg['official_test']),'known_limits':cfg['known_limits']}
 save(out/'manifest.json',manifest);save(out/'complete.json',{'status':'complete','manifest_sha256':sha(out/'manifest.json')})

def runtime():
 packages();load_module('workbench.endpoints.chemprop_utils',VENDOR/'chemprop_utils.py')
 return load_module('workbench.training.chemprop_core',VENDOR/'chemprop_core.py')

def worker(jobpath):
 import torch,importlib.metadata
 job=json.loads(Path(jobpath).read_text());prep=Path(job['prepared_dir']);out=Path(job['output_dir']);out.mkdir(parents=True,exist_ok=True)
 if (out/'complete.json').exists():raise FileExistsError(out)
 manifest=json.loads((prep/'manifest.json').read_text())
 if sources()!=manifest['source_sha256']:raise ValueError('Native source mismatch')
 short=job['member'];spec=json.loads((prep/f'{short}.json').read_text());assert sha(prep/f'{short}.csv')==spec['data_sha256']
 df=pd.read_csv(prep/f'{short}.csv',float_precision='round_trip');f=spec['folds'][job['fold']];targets=spec['targets'];y=df[targets].values.astype(np.float32)
 core=runtime();torch.set_num_threads(4)
 fs=core.FoldSpec(hyperparameters=spec['hyperparameters'],task='regression',model_type='uq_regressor',smiles_column='smiles',n_targets=len(targets),target_columns=targets,task_weights=np.asarray(spec['hyperparameters']['task_weights'],dtype=np.float32) if len(targets)>1 else None,num_workers=2,concurrent=True,enable_progress_bar=False,verbose=True)
 start=time.time()
 model,valid=core.train_chemprop_fold(fs,df.iloc[f['train']].reset_index(drop=True),df.iloc[f['validation']].reset_index(drop=True),y[f['train']],y[f['validation']],fold_idx=job['fold'],checkpoint_dir=str(out/'checkpoints'))
 blind=pd.read_csv(job['official_test']);q=blind.rename(columns={'Molecule_Name':'molecule_name','SMILES':'smiles'})
 pred=core.predict_chemprop_frame(model,fs,q)
 assert valid.shape==(len(f['validation']),len(targets)) and pred.shape==(len(q),len(targets)) and np.isfinite(valid).all() and np.isfinite(pred).all()
 for label,ids,values in [('oof',df.iloc[f['validation']].molecule_name,valid),('test',q.molecule_name,pred)]:
  table=pd.DataFrame(values,columns=targets);table.insert(0,'molecule_name',list(ids));table.to_csv(out/f'{label}.csv',index=False,float_format='%.17g')
 checkpoints=list((out/'checkpoints').glob('*.ckpt'));assert len(checkpoints)==1
 ck=torch.load(checkpoints[0],map_location='cpu',weights_only=False)
 save(out/'metadata.json',{'member':short,'fold':job['fold'],'seconds':time.time()-start,'best_epoch':ck['epoch'],'native_training_source':sha(VENDOR/'chemprop_core.py'),'training_rows':len(f['train']),'validation_rows':len(f['validation']),'packages':{n:importlib.metadata.version(n) for n in ['torch','chemprop','lightning','rdkit','numpy','pandas','scikit-learn']},'operational_changes':{'num_workers':2,'concurrent':True,'progress_bar':False,'torch_threads':4},'model_hyperparameters':spec['hyperparameters']})
 save(out/'complete.json',{'status':'complete','source_sha256':sources(),'files':{str(x.relative_to(out)):sha(x) for x in out.rglob('*') if x.is_file() and x.name not in {'complete.json','worker.log'}}})
 print(json.dumps({'event':'native_fold_complete','member':short,'fold':job['fold'],'best_epoch':ck['epoch'],'seconds':time.time()-start}),flush=True)

def collect(cfg):
 out=Path(cfg['output_dir']);prep=Path(cfg['prepared_dir']);blind=pd.read_csv(cfg['official_test']);frame_by_name={};test_by_name={}
 for short,name in MODELS.items():
  spec=json.loads((prep/f'{short}.json').read_text());df=pd.read_csv(prep/f'{short}.csv',float_precision='round_trip');targets=spec['targets'];oofs=[];qs=[]
  for f in range(5):
   d=out/short/f'fold{f}';done=json.loads((d/'complete.json').read_text());assert done['status']=='complete'
   for rel,h in done['files'].items():assert sha(d/rel)==h,(d,rel)
   oofs.append(pd.read_csv(d/'oof.csv').set_index('molecule_name'));q=pd.read_csv(d/'test.csv').set_index('molecule_name');qs.append(q.loc[blind.Molecule_Name,targets].to_numpy(dtype=np.float32))
  oof=pd.concat(oofs).loc[df.molecule_name,targets];assert oof.index.is_unique and np.isfinite(oof.to_numpy()).all()
  merged=df[['molecule_name']+targets].copy()
  for t in targets:merged[t+'_pred']=oof[t].to_numpy()
  merged.to_csv(out/short/'oof.csv',index=False,float_format='%.17g');frame_by_name[name]=merged
  q=pd.DataFrame(np.mean(qs,axis=0).astype(np.float64),columns=[t+'_pred' for t in targets]);q.insert(0,'molecule_name',blind.Molecule_Name.to_numpy())
  q.to_csv(out/short/'test_raw.csv',index=False,float_format='%.17g');test_by_name[name]=q
 api=packages()
 class PublicData:
  def get(self,name):assert name=='comp_chem/openadmet/cyp/testing/blinded';return blind.rename(columns={'Molecule_Name':'molecule_name','SMILES':'smiles'})
 class Model:
  def __init__(self,name):self.name=name
  def list_inference_runs(self):return ['cv_'+t for t in PRIMARY if t in frame_by_name[self.name]]
  def get_inference_predictions(self,run):
   t=run[3:];df=frame_by_name[self.name];return df[['molecule_name',t,t+'_pred']].rename(columns={t+'_pred':'prediction'})
 class Endpoint:
  def __init__(self,name):self.name=name
  def inference(self,query):return test_by_name[self.name].set_index('molecule_name').loc[query.molecule_name].reset_index()
 api.PublicData=PublicData;api.Model=Model;api.Endpoint=Endpoint
 validator=load_module('openadmet_validation',Path(cfg['validator_path']))
 native=load_module('cyp_recalibrate',VENDOR/'cyp_recalibrate.py')
 # Unchanged native assembly script, AST changes ONLY output directory to avoid writing vendor tree.
 tree=ast.parse((VENDOR/'cyp_ensemble_submit.py').read_text())
 for n in tree.body:
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OUT' for t in n.targets):n.value=ast.parse('Path('+repr(str(out))+')',mode='eval').body
 for n in tree.body:
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='N_TEST' for t in n.targets):n.value=ast.Constant(value=len(blind))
 ast.fix_missing_locations(tree);old=sys.argv;sys.argv=['cyp_ensemble_submit.py','--tag','native_raw']
 try:exec(compile(tree,str(VENDOR/'cyp_ensemble_submit.py'),'exec'),{'__name__':'__main__','__file__':str(VENDOR/'cyp_ensemble_submit.py')})
 finally:sys.argv=old
 raw=out/'cyp-ensemble_activity_submission_native_raw.csv'
 rho=native.oof_pearson(','.join(MODELS.values()));cal=native.place(pd.read_csv(raw),rho,strae=True)
 final=native.recalibrate(raw,out,'native_strae',cal)
 save(out/'placement.json',{'estimated_blind_pearson':rho,'calibration':cal,'BLIND_MOMENTS':native.BLIND_MOMENTS,'OOF_TO_BLIND':native.OOF_TO_BLIND,'STRAE_MOMENTS':native.STRAE_MOMENTS,'uses_published_leaderboard_derived_constants':True,'not_an_independent_hidden_test_evaluation':True})
 save(out/'final_complete.json',{'status':'complete','submission_csv':str(final),'submission_sha256':sha(final),'source_sha256':sources(),'data_manifest_sha256':sha(prep/'manifest.json'),'model_count':20,'fold_reduction_dtype':'float32, then endpoint columns float64 as initialized by native predict_fn','aggregation':'Native flat mean, then native oof_pearson + place(strae=True) + recalibrate; no learned stack or extra seed','known_limits':cfg['known_limits']})
 print(json.dumps({'event':'native_submission_ready','path':str(final),'sha256':sha(final)}),flush=True)

def run(cfg):
 if cfg['phase']=='prepare':return prepare(cfg)
 if cfg['phase']=='collect':
  import shutil
  target=Path(cfg['output_dir']);source=Path(cfg['trained_dir'])
  if target.exists():raise FileExistsError(target)
  for member in MODELS:
   for fold in range(5):
    shutil.copytree(source/member/f'fold{fold}',target/member/f'fold{fold}',copy_function=os.link)
  save(target/'config.json',cfg);collect(cfg);return
 out=Path(cfg['output_dir']);out.mkdir(parents=True,exist_ok=True);save(out/'config.json',cfg)
 jobs=[]
 for short in ['union18','2d6isoform6','mtaux8','2d6single']:
  for f in range(5):
   d=out/short/f'fold{f}';d.mkdir(parents=True,exist_ok=True)
   job={'member':short,'fold':f,'prepared_dir':cfg['prepared_dir'],'output_dir':str(d),'official_test':cfg['official_test']};save(d/'job.json',job)
   if not (d/'complete.json').exists():jobs.append(d/'job.json')
 running={}
 while jobs or running:
  for gpu in cfg['gpus']:
   if gpu not in running and jobs:
    job=jobs.pop(0);log=(job.parent/'worker.log').open('a');env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu))
    proc=subprocess.Popen([sys.executable,'-u','-m','night.briford_native','--worker',str(job)],env=env,stdout=log,stderr=subprocess.STDOUT);running[gpu]=(proc,log,job)
    print(json.dumps({'event':'native_fold_start','gpu':gpu,'job':str(job)}),flush=True)
  for gpu,(proc,log,job) in list(running.items()):
   status=proc.poll()
   if status is None:continue
   log.close();del running[gpu]
   if status:
    for other,_,_ in running.values():other.terminate()
    raise RuntimeError(f'Worker failed exit{status}: {job}')
  time.sleep(2)
 collect(cfg)

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',default='briford_config.json');p.add_argument('--worker');args=p.parse_args()
 if args.worker:return worker(args.worker)
 run(json.loads(Path(args.config).read_text()))
if __name__=='__main__':main()
