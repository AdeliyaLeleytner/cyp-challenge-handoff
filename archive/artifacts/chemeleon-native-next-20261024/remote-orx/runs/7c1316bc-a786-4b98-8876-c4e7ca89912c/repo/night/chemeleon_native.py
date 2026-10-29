"""CheMeleon substitution in the native 18/8/6/1 ensemble on frozen outer folds."""
from pathlib import Path
import json,os,signal,subprocess,sys,time,shutil
from . import briford_native as native
from .briford_holdouts import score

CHECKPOINT_SHA='c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651'
ENCODER={'hidden_dim':2048,'depth':6,'dropout':0.,'aggregation':'mean','trainable':True}

def prepare(config):
 assets=Path(config['assets']);out=Path(config['output_dir']);checkpoint=assets/'weights/chemeleon_mp.pt'
 assert native.sha(checkpoint)==CHECKPOINT_SHA
 configs=[]
 for cohort in ['own750','briford529']:
  source=assets/'frozen_holdouts'/cohort;root=out/cohort;prep=root/'prepared';prep.mkdir(parents=True,exist_ok=True)
  for name in ['truth.csv','query.csv','exclusion-audit.json']:shutil.copy2(source/name,root/name)
  manifest=json.loads((source/'prepared/manifest.json').read_text());assert manifest['source_sha256']==native.sources()
  models={}
  for member in native.MODELS:
   old=json.loads((source/'prepared'/f'{member}.json').read_text());assert native.sha(source/'prepared'/f'{member}.csv')==old['data_sha256']
   assert manifest['outer_exclusion_audit'][member]['remaining_held_id_parent_or_connectivity_overlap']==0
   shutil.copy2(source/'prepared'/f'{member}.csv',prep/f'{member}.csv')
   spec=json.loads(json.dumps(old));hp=spec['hyperparameters'];hp['from_foundation']=str(checkpoint)
   # These native fields are ignored by from_foundation but recorded consistently.
   hp['hidden_dim']=2048;hp['depth']=6
   spec['foundation']={'checkpoint_sha256':CHECKPOINT_SHA,'effective_encoder':ENCODER,'replaced_encoder':{'hidden_dim':700,'depth':5,'dropout':.1,'aggregation':'norm'},'fixed_ffn_dropout':hp['dropout']}
   assert spec['folds']==old['folds'] and spec['targets']==old['targets'] and spec['data_sha256']==old['data_sha256']
   for k in old['hyperparameters']:
    if k not in ['from_foundation','hidden_dim','depth']:assert hp[k]==old['hyperparameters'][k],k
   native.save(prep/f'{member}.json',spec);models[member]={k:v for k,v in spec.items() if k!='folds'}
  native.save(prep/'manifest.json',{**manifest,'models':models,'foundation':{'checkpoint_sha256':CHECKPOINT_SHA,'effective_encoder':ENCODER},'frozen_control_manifest_sha256':native.sha(source/'prepared/manifest.json')})
  cfg={'phase':'train','prepared_dir':str(prep),'output_dir':str(root/'results'),'official_test':str(root/'query.csv'),'validator_path':str(assets/'activity_validation.py'),'known_limits':['Exact frozen native outer data and inner folds. CheMeleon changes architecture and initialization, not only pretrained weights. Native MAE, optimizer schedule, FFN and placement retained. Published placement is TEST-specific.']}
  native.save(root/'config.json',cfg);configs.append(cfg)
 return configs

def run(config):
 configs=prepare(config);jobs=[];output=Path(config['output_dir'])
 # One shared queue lets any free GPU take the next fold from either cohort.
 for member in ['union18','2d6isoform6','mtaux8','2d6single']:
  for fold in range(5):
   for cfg in configs:
    d=Path(cfg['output_dir'])/member/f'fold{fold}';d.mkdir(parents=True,exist_ok=True)
    job={'member':member,'fold':fold,'prepared_dir':cfg['prepared_dir'],'output_dir':str(d),'official_test':cfg['official_test']}
    native.save(d/'job.json',job)
    if (d/'complete.json').exists():
     done=json.loads((d/'complete.json').read_text());assert done['job_identity']==native.job_identity(job), 'Completed fold belongs to a different recipe/source/data'
     for f,h in done['files'].items():assert native.sha(d/f)==h
    else:jobs.append(d/'job.json')
 running={}
 def cancelled(signum,frame):raise SystemExit(128+signum)
 signal.signal(signal.SIGTERM,cancelled);signal.signal(signal.SIGINT,cancelled)
 print(json.dumps({'event':'chemeleon_native_start','jobs_pending':len(jobs),'gpus':config['gpus'],'checkpoint_sha256':CHECKPOINT_SHA,'encoder':ENCODER}),flush=True)
 try:
  while jobs or running:
   for gpu in config['gpus']:
    if gpu not in running and jobs:
     job=jobs.pop(0);log=(job.parent/'worker.log').open('a');env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu))
     proc=subprocess.Popen([sys.executable,'-u','-m','night.briford_native','--worker',str(job)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
     running[gpu]=(proc,log,job);print(json.dumps({'event':'foundation_fold_start','gpu':gpu,'job':str(job)}),flush=True)
   for gpu,(proc,log,job) in list(running.items()):
    rc=proc.poll()
    if rc is None:continue
    if rc:raise RuntimeError(f'Worker failed exit={rc}: {job}')
    log.close();del running[gpu]
    meta=json.loads((job.parent/'metadata.json').read_text());print(json.dumps({'event':'foundation_fold_complete','gpu':gpu,'job':str(job),'seconds':meta['seconds'],'best_epoch':meta['best_epoch'],'remaining':len(jobs)+len(running)}),flush=True)
   time.sleep(2)
 finally:
  for proc,log,job in running.values():
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
  if running:time.sleep(3)
  for proc,log,job in running.values():
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   proc.wait();log.close()
 for cfg in configs:native.collect(cfg)
 score(config)
 native.save(output/'complete.json',{'status':'complete','models':40,'checkpoint_sha256':CHECKPOINT_SHA,'encoder':ENCODER,'control_scores':json.loads((Path(config['assets'])/'control-scores.json').read_text()),'files':{str(p.relative_to(output)):native.sha(p) for p in output.rglob('*') if p.is_file() and p.suffix!='.log' and p.name!='complete.json'}})
if __name__=='__main__':run(json.loads(Path('briford_config.json').read_text()))
