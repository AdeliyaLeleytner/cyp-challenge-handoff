"""One authorized native-reproduction submission; old train-only gate is not asserted."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from . import submit_candidate as transport
from .briford_native import MODELS,sources,sha

def prepare(results,prepared,official_test,validator,source_run,api_schema,source_snapshots,ledger):
 results,prepared=Path(results),Path(prepared)
 done=json.loads((results/'final_complete.json').read_text());cfg=json.loads((results/'config.json').read_text());run=json.loads(Path(source_run).read_text())
 if done['status']!='complete' or done['model_count']!=20 or done['source_sha256']!=sources():raise ValueError('Incomplete native final output or native source drift')
 if done['data_manifest_sha256']!=sha(prepared/'manifest.json'):raise ValueError('Prepared manifest mismatch')
 if run.get('status')!='done' or run.get('experiment_id')!='3218eedb-29ef-4af5-8c82-c166279d0bf3' or run.get('exit_code') not in (None,0):raise ValueError('Matching terminal native-training ORX run required')
 for member,ntasks in [('union18',18),('mtaux8',8),('2d6isoform6',6),('2d6single',1)]:
  spec=json.loads((prepared/f'{member}.json').read_text())
  if len(spec['targets'])!=ntasks or len(spec['folds'])!=5 or spec['hyperparameters']['seed']!=42 or sha(prepared/f'{member}.csv')!=spec['data_sha256']:raise ValueError('Member preparation differs')
  for fold in range(5):
   d=results/member/f'fold{fold}';c=json.loads((d/'complete.json').read_text());meta=json.loads((d/'metadata.json').read_text())
   if c['status']!='complete' or c['source_sha256']!=sources() or meta['member']!=member or meta['fold']!=fold:raise ValueError('Native fold completion mismatch')
   if meta['model_hyperparameters']!=spec['hyperparameters']:raise ValueError('Native effective hyperparameters changed')
   if not any(x.startswith('checkpoints/') and x.endswith('.ckpt') for x in c['files']):raise ValueError('Native trained checkpoint missing')
   for rel,h in c['files'].items():
    path=(d/rel).resolve()
    if not path.is_relative_to(d.resolve()) or sha(path)!=h:raise ValueError('Fold artifact hash mismatch')
 csv=results/Path(done['submission_csv']).name
 if sha(csv)!=done['submission_sha256']:raise ValueError('Final CSV hash mismatch')
 validation=transport._validate_csv(csv,csv.read_bytes(),Path(official_test).read_bytes(),Path(validator))
 def record(p):p=Path(p);return {'path':str(p.resolve()),'sha256':sha(p)}
 snapshots={k:Path(source_snapshots)/f'{k}.py' for k in ['app','submission','config']}
 signature=transport._check_sources({k:p.read_text() for k,p in snapshots.items()},json.loads(Path(api_schema).read_text()))
 placement=json.loads((results/'placement.json').read_text());rho=placement['estimated_blind_pearson']
 if not all(np.isfinite(v) and v>0 for v in rho.values()):raise ValueError('Invalid estimated Pearson; inspect native results')
 body={'schema_version':1,'candidate_name':'briford_native_historical_recipe','authorization_basis':'User explicitly requested exact briford reproduction and leaderboard improvement after previous train-only adaptation; original local-gain gate is not reused or claimed.',
  'api_signature':signature,'api_arguments_without_file':{'username':transport.USERNAME,'user_alias':transport.ALIAS,'anon_checkbox':True,'participant_name':'','discord_username':'','email':'','affiliation':'','model_tag':'Briford native historical 18/8/6/1 D-MPNN recipe; 5 folds seed42; published placement; public data snapshots','paper_checkbox':False,'proprietary_data_checkbox':False,'open_code_checkbox':False,'track_select':'Regression Prediction'},
  'gradio_client_version':'2.7.2','native_completion':record(results/'final_complete.json'),'native_run':record(source_run),'prepared_manifest':record(prepared/'manifest.json'),'source_sha256':sources(),'submission_csv':record(csv),'official_test':record(official_test),'validator':record(validator),'api_schema':record(api_schema),'source_snapshots':{k:record(p) for k,p in snapshots.items()},'validation':validation,'estimated_blind_pearson':rho,'rho_above_one':{k:v for k,v in rho.items() if v>1},'known_limits':done['known_limits'],'disclosures':{'used_proprietary_data':False,'code_published':False,'publication_opt_in':False,'uses_public_leaderboard_derived_calibration':True}}
 identity=hashlib.sha256(transport._json_bytes(body)).hexdigest();directory=Path(ledger).resolve()/'intents'/identity
 transport._immutable(directory/'intent.json',transport._json_bytes(body));transport._immutable(directory/'submission.csv',csv.read_bytes());transport._immutable(directory/'native_final_complete.json',(results/'final_complete.json').read_bytes())
 return {'intent_id':identity,'intent_dir':str(directory),'csv_sha256':sha(csv),'intent':body,'status':'dry_run_verified_native_recipe'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--send',action='store_true');a=p.parse_args();cfg=json.loads(Path(a.config).read_text());prepared=prepare(**cfg)
 if a.send:
  if prepared['intent']['rho_above_one']:raise ValueError('Native estimated correlation >1 requires root review; no automatic clamp or dispatch')
  result=transport.send_prepared(prepared,cfg['ledger']);print(json.dumps(result),flush=True);return 0 if result['status']=='accepted_pending' else 2
 print(json.dumps({k:v for k,v in prepared.items() if k!='intent'}),flush=True);print(json.dumps({'estimated_blind_pearson':prepared['intent']['estimated_blind_pearson'],'rho_above_one':prepared['intent']['rho_above_one']}),flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
