"""Storage/orchestration adapter around the unchanged native worker and collector."""
import argparse,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
import numpy as np,pandas as pd
from . import briford_native as native
from .strict_reference_prepare import sha,save,hash_json

COHORTS=['own750','briford529'];AFFECTED=['union18','2d6isoform6'];REUSED=['mtaux8','2d6single']
def preflight(cfg,stage=None,training_runtime=False):
 root=Path(stage or cfg['stage_root']);manifest=root/'asset-manifest.json'
 assert sha(manifest)==cfg['asset_manifest_sha256'],'Staging manifest changed'
 entries=json.loads(manifest.read_text())
 for rel,record in entries.items():
  p=root/rel;assert p.stat().st_size==record['bytes'] and sha(p)==record['sha256'],rel
 proof=json.loads((root/'purge-and-reuse-manifest.json').read_text());assert native.sources()==proof['source_sha256']
 assert sha(Path(native.__file__))==cfg['native_adapter_sha256'],'Native worker/collector adapter changed'
 for rel,digest in cfg['support_source_sha256'].items():assert sha(Path(__file__).resolve().parents[1]/rel)==digest,rel
 assert len(proof['outer_removed_rows'])==12 and len(proof['reused_folds'])==20
 for cohort in COHORTS:
  for member in REUSED:
   item=proof['components'][cohort+'/'+member]
   assert item['source_data_sha256']==item['new_data_sha256'] and item['source_spec_sha256']==item['new_spec_sha256']
   assert item['outer_removed_count']==item['inner_train_removals']==0
 from .briford_holdouts import keys
 aliases=pd.read_csv(root/'audit/id-map-snapshot.csv',keep_default_na=False)
 official=aliases[aliases.source=='official-train.csv'].set_index('Molecule_Name')
 cohorts=json.loads((root/'cohorts.json').read_text())['cohorts']
 alias_ids={(r.source,r.Molecule_Name):r.request_id for r in aliases.itertuples()}
 pairs=pd.read_csv(root/'audit/tautomer-pair-chemical-details.csv',keep_default_na=False);group={}
 for row in pairs.to_dict('records'):
  if str(row['stereo_preserving_tautomer_key_equal'])!='True':continue
  ids=row['request_ids'].split(';')
  for rid in ids:group[rid]=min(ids)
 assert len(set(group.values()))==13
 for cohort in COHORTS:
  excluded=set(cohorts[cohort]['test_ids'])|set(cohorts[cohort]['outer_parent_purged_ids'])
  forbidden_keys=[keys(official.loc[i,'SMILES']) for i in excluded]
  parents={x[0] for x in forbidden_keys};connectivity={x[1] for x in forbidden_keys}
  held_groups={group[alias_ids[('official-train.csv',i)]] for i in excluded if alias_ids[('official-train.csv',i)] in group}
  for member in native.MODELS:
   data=pd.read_csv(root/'corrected'/cohort/'prepared'/f'{member}.csv')
   spec=json.loads((root/'corrected'/cohort/'prepared'/f'{member}.json').read_text())
   gids=[group.get(alias_ids[(member,n)]) for n in data.molecule_name]
   assert not({x for x in gids if x}&held_groups)
   for fold in spec['folds']:
    train_groups={gids[i] for i in fold['train'] if gids[i]};val_groups={gids[i] for i in fold['validation'] if gids[i]}
    assert not(train_groups&val_groups)
  for member in REUSED:
   data=pd.read_csv(root/'corrected'/cohort/'prepared'/f'{member}.csv')
   assert not(set(data.molecule_name)&excluded)
   assert all(p not in parents and k not in connectivity for p,k in map(keys,data.smiles))
 for cert in proof['reused_folds']:
  d=root/'reuse'/cert['cohort']/cert['member']/f"fold{cert['fold']}"
  assert sha(d/'complete.json')==cert['complete_sha256']
  for rel,digest in cert['checkpoint_prediction_and_metadata_hashes'].items():assert sha(d/rel)==digest
  spec=json.loads((root/'corrected'/cert['cohort']/'prepared'/f"{cert['member']}.json").read_text())
  fold=spec['folds'][cert['fold']]
  assert hash_json(fold)==cert['fold_sha256']
  data=pd.read_csv(root/'corrected'/cert['cohort']/'prepared'/f"{cert['member']}.csv")
  query=pd.read_csv(root/'corrected'/cert['cohort']/'query.csv')
  oof=pd.read_csv(d/'oof.csv');pred=pd.read_csv(d/'test.csv')
  assert oof.molecule_name.tolist()==data.iloc[fold['validation']].molecule_name.tolist()
  assert pred.molecule_name.tolist()==query.Molecule_Name.tolist()
  assert list(oof.columns)==['molecule_name']+spec['targets'] and list(pred.columns)==['molecule_name']+spec['targets']
  assert np.isfinite(oof[spec['targets']].to_numpy(float)).all() and np.isfinite(pred[spec['targets']].to_numpy(float)).all()
 if training_runtime:
  import torch,importlib.metadata
  expected=json.loads((root/'runtime-packages.json').read_text())
  actual={name:importlib.metadata.version(name) for name in expected}
  assert actual==expected,(actual,expected)
  assert torch.cuda.is_available() and len(set(cfg['gpus']))==len(cfg['gpus'])
  assert max(cfg['gpus'])<torch.cuda.device_count()
 result={'event':'corrected_reference_preflight','data_verified':True,'reused_folds':20,'retrain_folds':20,'outer_removed_rows':12,'inner_train_removed_rows':len(proof['inner_train_removed_rows']),'native_sources_unchanged':True,'reused_outer_purges_recomputed':True,'reused_prediction_ids_match_folds':True,'strict_outer_and_inner_group_overlap':0,'fits_launched':0}
 print(json.dumps(result),flush=True);return result

def metrics(truth,pred):
 from .evaluation import score
 from scipy.stats import spearmanr,kendalltau
 from sklearn.metrics import r2_score
 result=score(truth,pred)
 joined=pred.set_index('Molecule_Name').loc[truth.Molecule_Name]
 for col,row in result['endpoints'].items():
  mask=np.isfinite(truth[col].to_numpy(float));y=truth.loc[mask,col].to_numpy(float);p=joined.loc[truth.loc[mask,'Molecule_Name'],col].to_numpy(float)
  row.update(R2=float(r2_score(y,p)),Spearman=float(spearmanr(y,p).statistic),Kendall=float(kendalltau(y,p).statistic))
 result['macro_metrics']={key:float(np.mean([v[key] for v in result['endpoints'].values()])) for key in ['ST_RAE','MAE','R2','Spearman','Kendall']}
 return result

def run(cfg):
 preflight(cfg,training_runtime=True);stage=Path(cfg['stage_root']);out=Path(cfg['output_root']);out.mkdir(parents=True,exist_ok=True)
 if (out/'effective-config.json').exists():assert json.loads((out/'effective-config.json').read_text())==cfg,'Refuse stale outputs from another configuration'
 elif any(out.iterdir()):raise FileExistsError('Unrecognized existing output directory')
 save(out/'effective-config.json',cfg)
 jobs=[];cohort_configs={}
 for cohort in COHORTS:
  root=out/cohort;results=root/'results';results.mkdir(parents=True,exist_ok=True)
  corrected=stage/'corrected'/cohort
  config={'prepared_dir':str(corrected/'prepared'),'output_dir':str(results),'official_test':str(corrected/'query.csv'),'validator_path':str(stage/'activity_validation.py'),'known_limits':['Fixed outer cohorts and surviving validation assignments; strict audited tautomer exclusions only.','Historical native placement remains a separate output using its published constants.','Unchanged component folds reused only after data/spec/fold/checkpoint/prediction verification.']}
  cohort_configs[cohort]=config;save(root/'config.json',config)
  for member in REUSED:
   for fold in range(5):
    src=stage/'reuse'/cohort/member/f'fold{fold}';dest=results/member/f'fold{fold}'
    if not dest.exists():shutil.copytree(src,dest)
    # Do not rewrite historical job.json: its hash is part of the reuse certificate.
    done=json.loads((dest/'complete.json').read_text())
    for rel,h in done['files'].items():assert sha(dest/rel)==h
 for member in AFFECTED:
  for cohort in COHORTS:
   config=cohort_configs[cohort]
   for fold in range(5):
    dest=Path(config['output_dir'])/member/f'fold{fold}';dest.mkdir(parents=True,exist_ok=True)
    if (dest/'complete.json').exists():
     done=json.loads((dest/'complete.json').read_text())
     for rel,h in done['files'].items():assert sha(dest/rel)==h
     continue
    job={'member':member,'fold':fold,'prepared_dir':config['prepared_dir'],'output_dir':str(dest),'official_test':config['official_test']}
    save(dest/'job.json',job);jobs.append(dest/'job.json')
 running={}
 def cancel(signum,frame):raise KeyboardInterrupt('Run interrupted')
 signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
 try:
  while jobs or running:
   for gpu in cfg['gpus']:
    if gpu not in running and jobs:
     job=jobs.pop(0);log=(job.parent/'worker.log').open('a');env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu))
     proc=subprocess.Popen([sys.executable,'-u','-m','night.briford_native','--worker',str(job)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
     running[gpu]=(proc,log,job);print(json.dumps({'event':'corrected_fold_start','gpu':gpu,'job':str(job)}),flush=True)
   for gpu,(proc,log,job) in list(running.items()):
    status=proc.poll()
    if status is None:continue
    log.close();del running[gpu]
    if status:raise RuntimeError(f'Native worker failed: {job}, exit{status}')
    print(json.dumps({'event':'corrected_fold_complete','job':str(job)}),flush=True)
   time.sleep(2)
 finally:
  for proc,log,job in running.values():
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
  for proc,log,job in running.values():
   try:proc.wait(timeout=20)
   except subprocess.TimeoutExpired:
    os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   log.close()
 scores={}
 for cohort,config in cohort_configs.items():
  native.collect(config)
  truth=pd.read_csv(stage/'corrected'/cohort/'truth.csv');result=Path(config['output_dir'])
  scores[cohort]={}
  for variant,name in [('raw','cyp-ensemble_activity_submission_native_raw.csv'),('native_published_placement','cyp-ensemble_activity_submission_native_raw_native_strae.csv')]:
   scores[cohort][variant]=metrics(truth,pd.read_csv(result/name))
  save(out/cohort/'scores.json',scores[cohort])
 save(out/'scores.json',scores)
 save(out/'complete.json',{'status':'complete','retrained_folds':20,'reused_folds':20,'asset_manifest_sha256':cfg['asset_manifest_sha256'],'source_sha256':native.sources(),'files':{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='complete.json' and p.suffix!='.log'}})
 print(json.dumps({'event':'corrected_reference_summary','scores':scores,'retrained_folds':20,'reused_folds':20}),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--preflight-only',action='store_true');p.add_argument('--stage');a=p.parse_args();cfg=json.loads(Path('strict_reference_config.json').read_text())
 if a.preflight_only:preflight(cfg,a.stage)
 else:run(cfg)
if __name__=='__main__':main()
