"""Orchestrate the corrected full-data native fit; no implicit submission."""
import argparse,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
import numpy as np,pandas as pd
from . import briford_native as native
from .strict_reference_prepare import sha,save,hash_json
from .strict_fullfit_prepare import strict_groups,EXPECTED_ROWS,FINAL_SHA,AFFECTED,REUSED

TARGETS=[f'{x}_pIC50_direct_inhibition' for x in ('CYP1A2','CYP2C9','CYP2D6','CYP3A4')]
def preflight(cfg,stage=None,training_runtime=False):
 root=Path(stage or cfg['stage_root']);asset=root/'asset-manifest.json'
 assert sha(asset)==cfg['asset_manifest_sha256'],'Staging manifest changed'
 for rel,record in json.loads(asset.read_text()).items():
  p=root/rel;assert p.stat().st_size==record['bytes'] and sha(p)==record['sha256'],rel
 proof=json.loads((root/'purge-and-reuse-manifest.json').read_text());assert native.sources()==proof['source_sha256']
 assert sha(Path(native.__file__))==cfg['native_adapter_sha256']==proof['native_adapter_sha256']
 for rel,digest in cfg['support_source_sha256'].items():assert sha(Path(__file__).resolve().parents[1]/rel)==digest,rel
 assert proof['full_pools_preserved'] and proof['outer_removed_rows']==0 and len(proof['reused_folds'])==10
 assert proof['historical_finalized_submission_sha256']==FINAL_SHA
 assert sha(root/'original-finalized/cyp-ensemble_activity_submission_native_raw_native_strae.csv')==FINAL_SHA
 group=strict_groups(root/'audit');aliases=pd.read_csv(root/'audit/id-map-snapshot.csv',keep_default_na=False)
 ids={(r.source,r.Molecule_Name):r.request_id for r in aliases.itertuples()}
 query=pd.read_csv(root/'query.csv');official=pd.read_csv(root/'official-train.csv');assert len(query)==750 and len(official)==4905
 assert not set(query.Molecule_Name)&set(official.Molecule_Name)
 for member in native.MODELS:
  frame=pd.read_csv(root/'prepared'/f'{member}.csv',float_precision='round_trip');spec=json.loads((root/'prepared'/f'{member}.json').read_text());original=json.loads((root/'original-specs'/f'{member}.json').read_text())
  item=proof['components'][member];assert len(frame)==EXPECTED_ROWS[member] and sha(root/'prepared'/f'{member}.csv')==original['data_sha256']==item['source_data_sha256']==item['new_data_sha256']
  assert spec['hyperparameters']==original['hyperparameters'] and spec['target_counts']==original['target_counts']
  gids=[group.get(ids[(member,n)]) for n in frame.molecule_name]
  for fold,new in enumerate(spec['folds']):
   old=original['folds'][fold];assert new['validation']==old['validation']
   val_groups={gids[i] for i in old['validation'] if gids[i]}
   expected=[i for i in old['train'] if not gids[i] or gids[i] not in val_groups]
   assert new['train']==expected and not set(new['train'])&set(new['validation'])
   assert not ({gids[i] for i in new['train'] if gids[i]}&val_groups)
  assert sorted(i for f in spec['folds'] for i in f['validation'])==list(range(len(frame)))
  if member in REUSED:assert spec==original and item['inner_train_removals']==0 and item['source_spec_sha256']==item['new_spec_sha256']
  if member=='mtaux8':
   aligned=frame.set_index('molecule_name').loc[official.Molecule_Name];assert aligned.smiles.tolist()==official.SMILES.tolist()
   for target in TARGETS:assert np.allclose(aligned[target.lower()].to_numpy(),official[target].to_numpy(),rtol=0,atol=1e-12,equal_nan=True)
 for alias in proof['public_blind_alias_retained']:
  frame=pd.read_csv(root/'prepared'/f"{alias['member']}.csv");assert alias['official_blind_id'] in set(query.Molecule_Name)
  row=frame.set_index('molecule_name').loc[alias['training_molecule_name']]
  assert ids[(alias['member'],alias['training_molecule_name'])]==alias['request_id']
  assert all(pd.isna(row[t]) for t in native.PRIMARY if t in row.index)
  assert alias['public_assay_columns'] and all(pd.notna(row[t]) for t in alias['public_assay_columns'])
 for cert in proof['reused_folds']:
  member,fold=cert['member'],cert['fold'];directory=root/'reuse'/member/f'fold{fold}'
  assert sha(directory/'complete.json')==cert['complete_sha256']
  for rel,digest in cert['files'].items():assert sha(directory/rel)==digest
  frame=pd.read_csv(root/'prepared'/f'{member}.csv');spec=json.loads((root/'prepared'/f'{member}.json').read_text())
  assert hash_json(spec['folds'][fold])==cert['fold_sha256']
  oof=pd.read_csv(directory/'oof.csv');test=pd.read_csv(directory/'test.csv')
  assert oof.molecule_name.tolist()==frame.iloc[spec['folds'][fold]['validation']].molecule_name.tolist()
  assert test.molecule_name.tolist()==query.Molecule_Name.tolist()
  assert list(oof.columns)==list(test.columns)==['molecule_name']+spec['targets']
  assert np.isfinite(oof[spec['targets']].to_numpy()).all() and np.isfinite(test[spec['targets']].to_numpy()).all()
 if training_runtime:
  import torch,importlib.metadata
  expected=json.loads((root/'runtime-packages.json').read_text());actual={name:importlib.metadata.version(name) for name in expected};assert actual==expected,(actual,expected)
  assert torch.cuda.is_available() and len(set(cfg['gpus']))==len(cfg['gpus']) and max(cfg['gpus'])<torch.cuda.device_count()
 result={'event':'strict_fullfit_preflight','fits_launched':0,'full_pools_preserved':True,'outer_removed_rows':0,'inner_train_removed_rows':len(proof['inner_train_removed_rows']),'original_validation_ids_preserved':True,'reused_folds_verified':10,'retrain_folds':10,'strict_inner_group_overlap':0,'public_blind_assay_alias_preserved':True,'finalized_serving_source_verified':True}
 print(json.dumps(result),flush=True);return result

def save_official_oof(stage,result):
 official=pd.read_csv(stage/'official-train.csv');total=np.zeros((len(official),4));counts=np.zeros_like(total)
 for member in native.MODELS:
  frame=pd.read_csv(result/member/'oof.csv').set_index('molecule_name');assert frame.index.is_unique
  for j,target in enumerate(TARGETS):
   key=target.lower()+'_pred'
   if key not in frame:continue
   values=frame[key].reindex(official.Molecule_Name).to_numpy();mask=np.isfinite(values)
   total[mask,j]+=values[mask];counts[mask,j]+=1
 predictions=np.divide(total,counts,out=np.full_like(total,np.nan),where=counts>0)
 for j,target in enumerate(TARGETS):
  mask=official[target].notna().to_numpy();assert np.all(counts[mask,j]==(4 if '2D6' in target else 2))
 assert np.isfinite(predictions).all()
 frame=official[['Molecule_Name','SMILES']].copy()
 for j,target in enumerate(TARGETS):frame[target]=predictions[:,j]
 frame.to_csv(result/'native_official_training_OOF.csv',index=False,float_format='%.17g')
 save(result/'native_official_training_OOF_provenance.json',{'training_rows':len(frame),'primary_truth_source_sha256':sha(stage/'official-train.csv'),'component_oof_sha256':{m:sha(result/m/'oof.csv') for m in native.MODELS},'same_strict_inner_identity_policy_as_corrected_outer_reference':True,'no_blind_truth_used':True})

def run(cfg):
 assert cfg.get('training_enabled') is True,'Preparation-only node: parent must explicitly enable/commit training after budget review'
 preflight(cfg,training_runtime=True);stage=Path(cfg['stage_root']);out=Path(cfg['output_root']);out.mkdir(parents=True,exist_ok=True)
 if (out/'effective-config.json').exists():assert json.loads((out/'effective-config.json').read_text())==cfg
 elif any(out.iterdir()):raise FileExistsError('Unrecognized existing output directory')
 save(out/'effective-config.json',cfg);results=out/'results';results.mkdir(exist_ok=True)
 config={'prepared_dir':str(stage/'prepared'),'output_dir':str(results),'official_test':str(stage/'query.csv'),'validator_path':str(stage/'activity_validation.py'),'known_limits':['Full native training pools retained; train-side strict tautomer exclusion inside original folds.','Historical published placement is a separate lane with leaderboard-derived constants.','Legitimate public Veith blinded-structure overlap retained; no hidden challenge labels.','Unchanged components reused only with exact data/spec/fold/source/package/prediction proofs.']}
 save(out/'native-config.json',config)
 for member in REUSED:
  for fold in range(5):
   src=stage/'reuse'/member/f'fold{fold}';dest=results/member/f'fold{fold}'
   if not dest.exists():shutil.copytree(src,dest)
   done=json.loads((dest/'complete.json').read_text())
   for rel,digest in done['files'].items():assert sha(dest/rel)==digest
 jobs=[]
 for member in ['union18','2d6isoform6']:
  for fold in range(5):
   dest=results/member/f'fold{fold}';dest.mkdir(parents=True,exist_ok=True)
   if (dest/'complete.json').exists():
    done=json.loads((dest/'complete.json').read_text())
    for rel,digest in done['files'].items():assert sha(dest/rel)==digest
    continue
   job={'member':member,'fold':fold,'prepared_dir':config['prepared_dir'],'output_dir':str(dest),'official_test':config['official_test']};save(dest/'job.json',job);jobs.append(dest/'job.json')
 running={}
 def cancel(signum,frame):raise KeyboardInterrupt('Full-fit run interrupted')
 signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
 try:
  while jobs or running:
   for gpu in cfg['gpus']:
    if gpu not in running and jobs:
     job=jobs.pop(0);log=(job.parent/'worker.log').open('a');env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu))
     proc=subprocess.Popen([sys.executable,'-u','-m','night.briford_native','--worker',str(job)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
     running[gpu]=(proc,log,job);print(json.dumps({'event':'strict_fullfit_fold_start','gpu':gpu,'job':str(job)}),flush=True)
   for gpu,(proc,log,job) in list(running.items()):
    status=proc.poll()
    if status is None:continue
    log.close();del running[gpu]
    if status:raise RuntimeError(f'Native fold failed:{job},exit{status}')
    print(json.dumps({'event':'strict_fullfit_fold_complete','job':str(job)}),flush=True)
   time.sleep(2)
 finally:
  for proc,log,job in running.values():
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
  for proc,log,job in running.values():
   try:proc.wait(timeout=20)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   log.close()
 native.collect(config);save_official_oof(stage,results)
 save(out/'complete.json',{'status':'complete','retrained_folds':10,'reused_folds':10,'asset_manifest_sha256':cfg['asset_manifest_sha256'],'native_adapter_sha256':cfg['native_adapter_sha256'],'source_sha256':native.sources(),'no_submission':True,'no_blind_truth_used':True,'files':{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='complete.json' and p.suffix!='.log'}})
 print(json.dumps({'event':'strict_fullfit_complete','retrained_folds':10,'reused_folds':10,'no_submission':True,'output':str(out)}),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--preflight-only',action='store_true');p.add_argument('--stage');a=p.parse_args();cfg=json.loads(Path('strict_fullfit_config.json').read_text())
 if a.preflight_only:preflight(cfg,a.stage)
 else:run(cfg)
if __name__=='__main__':main()
