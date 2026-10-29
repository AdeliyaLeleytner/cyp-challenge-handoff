"""Locked H6 submission wrapper. Default offline; only an explicit root --send dispatches.

Uses only schema/CSV/immutable-storage/Gradio mechanics from the pinned historical
transport. Its old two-seed promotion and prepare functions are NEVER called.
No training, model re-fit, code publication or automatic submission retry exists.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,fcntl,hashlib,io,ipaddress,json,os,sqlite3,subprocess,sys,time,urllib.parse,urllib.request,socket
import numpy as np,pandas as pd
from live_contract import ROOT,SPACE,LEGACY,LEGACY_SHA,legacy,record,sha,dump,refresh
PROJECT='6678888c-9305-4203-9fce-6bdaed527e9a'
NODE='b64f3a0f-3bb5-4e17-95c1-3fff9342a6a9'
RECIPE='lightgbm__adme720__native_blend_per_target'
ORX=Path('/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store')
REPO=Path('/Users/adeliyaleleytner/.local/share/openresearch/projects/cyp-chemeleon-baseline-20261023')
LEDGER=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/submission-ledger')
TARGETS=[f'{c}_pIC50_direct_inhibition' for c in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
IDENTITY_FIELDS=['username','user_alias','anon_checkbox','participant_name','discord_username','email','affiliation','paper_checkbox','proprietary_data_checkbox','open_code_checkbox','track_select']
class GuardError(ValueError):pass
def need(value,message):
 if not value:raise GuardError(message)
def now():return datetime.now(timezone.utc)
def pin(item,label):
 need(isinstance(item,dict) and item.get('path') and item.get('sha256'),label+' is unpinned')
 p=Path(item['path']);need(p.is_file() and sha(p)==item['sha256'],label+' missing or changed');return p

def capture_run(run_id,destination):
 c=sqlite3.connect('file:'+str(ORX/'orx.db')+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 r=c.execute('select id,experiment_id,project_id,status,command,created_at,ended_at,exit_code,commit_sha from runs where id=?',(run_id,)).fetchone();need(r is not None,'Unknown ORX run');r=dict(r)
 need(r['experiment_id']==NODE and r['project_id']==PROJECT and r['status']=='done' and r['command']=='bash run.sh' and r['ended_at'] is not None,'Matching completed locked-H6 ORX run required')
 base=ORX/'local-runs'/run_id;need((base/'exit_code').read_text().strip()=='0','ORX exit receipt is not zero');source=base/'repo';cfg=json.loads((source/'final_feature_config.json').read_text())
 files=set(cfg.get('source_sha256',{}))|{'run.sh','night/locked_h6_final.py','night/final_feature_run.py','night/final_feature_contract.py','night/final_model_artifacts.py','final_feature_config.json'};source_records={}
 for rel in sorted(files):
  p=(source/rel).resolve();need(p.is_relative_to(source.resolve()),'Unsafe source path')
  b=subprocess.run(['git','-C',str(REPO),'show',r['commit_sha']+':'+rel],capture_output=True,check=True).stdout
  need(hashlib.sha256(b).hexdigest()==sha(p),'Source differs from actual ORX commit: '+rel);source_records[rel]=record(p)
 value={'schema_version':1,'recorded_utc':now().isoformat(),'evidence':'Read-only ORX database row + exit receipt + Git blob parity','run':r,'source_root':str(source),'source_files':source_records,'exit_receipt':record(base/'exit_code'),'run_log':record(base/'log')};dump(destination,value);return value

def valid_public_url(url,resolve=False):
 p=urllib.parse.urlsplit(url);need(p.scheme=='https' and p.hostname and not p.username and not p.password,'Public HTTPS report URL required')
 need(p.hostname not in ['localhost'] and not p.hostname.endswith(('.local','.internal')),'Report must be public')
 try:address=ipaddress.ip_address(p.hostname)
 except ValueError:address=None
 if address is not None:need(address.is_global,'Report IP is not public')
 elif resolve:
  ips={x[4][0] for x in socket.getaddrinfo(p.hostname,p.port or 443)};need(ips and all(ipaddress.ip_address(x).is_global for x in ips),'Report resolves to a nonpublic address')
 return url

def check_report(url,csv_sha,destination):
 valid_public_url(url,True)
 class SafeRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,headers,newurl):valid_public_url(newurl,True);return super().redirect_request(req,fp,code,msg,headers,newurl)
 opener=urllib.request.build_opener(SafeRedirect())
 with opener.open(urllib.request.Request(url,headers={'User-Agent':'CYP-H6-report-verification/1'}),timeout=30) as response:
  need(response.status==200,'Report URL is not publicly readable');valid_public_url(response.url,True);body=response.read(10*1024*1024+1);need(len(body)<=10*1024*1024,'Report exceeds bounded verification download');final=response.url
 value={'schema_version':1,'public_https_verified':True,'verified_without_credentials':True,'checked_utc':now().isoformat(),'url':url,'resolved_url':final,'http_status':200,'response_bytes':len(body),'response_sha256':hashlib.sha256(body).hexdigest(),'submission_csv_sha256':csv_sha,'limit':'Reachability check; root reviews report content and scientific claims separately'};dump(destination,value);return value

def model_path(value,source_root):
 # Model config paths are relative to the actual ORX source working directory.
 # Caller-supplied CLI paths retain normal caller-CWD semantics.
 p=Path(value);return (p if p.is_absolute() else Path(source_root)/p).resolve()

def build_manifest(run_receipt,report_url,report_receipt,destination,live_contract=None):
 run=json.loads(Path(run_receipt).read_text());source=Path(run['source_root']);cfg=json.loads((source/'final_feature_config.json').read_text());out=model_path(cfg['output_dir'],source);done=json.loads((out/'complete.json').read_text())
 files={'run_receipt':record(run_receipt),'decision':record(model_path(cfg['validated_recipe_decision'],source)),'identity':record(ROOT/'identity.json'),'live_contract':record(live_contract or ROOT/'current-contract.json'),'final_config':record(source/'final_feature_config.json'),'final_complete':record(out/'complete.json'),'submission_validation':record(out/'submission-validation.json'),'selection':record(out/'full-data-selection.json'),'model_manifest':record(out/'final-models/manifest.json'),'placement':record(out/'final-placement.json'),'submission_csv':record(out/Path(done['submission_csv']).name),'raw_csv':record(out/'final-test-raw.csv'),'selected_oof':record(out/'selected__training_OOF.csv'),'public_report_receipt':record(report_receipt)}
 value={'schema_version':1,'protocol':'goal-20261026_locked_H6_v1','expected_final_experiment':NODE,'serving_lane':'native_published_placement','ledger':str(LEDGER),'report_url':report_url,'gradio_client_version':'2.7.2','files':files,'legacy_mechanics':{'path':str(LEGACY),'sha256':LEGACY_SHA},'old_two_seed_gate_used':False};dump(destination,value);return value

def validate_csv(csv_path,official_test,validator):
 csv_path=Path(csv_path);official_test=Path(official_test);p=pd.read_csv(csv_path);b=pd.read_csv(official_test)
 need(p.Molecule_Name.tolist()==b.Molecule_Name.tolist() and p.SMILES.tolist()==b.SMILES.tolist(),'Exact official query order/SMILES required')
 return legacy()._validate_csv(csv_path,csv_path.read_bytes(),official_test.read_bytes(),Path(validator))

def verify_heads(out,selection,complete,cfg,manifest,final):
 models=json.loads((out/'final-models/manifest.json').read_text());need(models==complete['saved_final_models'] and set(models['models'])==set(TARGETS),'Four saved heads and completion manifest must agree')
 need(models['raw_blend_reconstruction_exact'] is True and models['model_refits_for_reload_verification']==0,'Reload/raw reconstruction proof missing')
 selection_sha=sha(out/'full-data-selection.json');need(models['selection_sha256']==selection_sha,'Head selection binding mismatch')
 train=pd.read_csv(pin(manifest['files']['official_train'],'official train'));blind=pd.read_csv(pin(manifest['files']['official_test'],'official test'));columns=manifest['feature_columns'];expected_order=[f'ADME600::coordinate_{i:03d}' for i in range(600)]+columns
 weights=np.asarray(selection['chosen']['weight'],float);need(weights.shape==(4,) and np.isfinite(weights).all() and np.all((0<=weights)&(weights<=1)),'Invalid per-CYP convex weights')
 need([models['native_blend_weights'][t] for t in TARGETS]==weights.tolist(),'Stored blend weights differ')
 predictions=[];assets={}
 for t in TARGETS:
  d=out/'final-models'/t;r=json.loads((d/'receipt.json').read_text());m=models['models'][t]
  need(sha(d/'receipt.json')==m['receipt_sha256'] and sha(d/'head.joblib')==r['model_sha256']==m['model_sha256'],'Head/receipt hash mismatch')
  need(r.get('reload_exact') is True and r.get('reload_max_abs_error')==m['reload_max_abs_error']==0 and r.get('additional_refits_for_verification')==0,'Exact head reload receipt missing')
  need(all(r['packages'][k]==complete['packages'][k] for k in ['numpy','scikit-learn','lightgbm']),'Saved head runtime differs from final run')
  need(r['query_rows']==750 and r['feature_count']==720 and r['training_rows']==m['training_rows']==int(train[t].notna().sum()),'Head training/query counts mismatch')
  identity=r['identity'];need(identity['target']==t and identity['seed']==42 and identity['params']==selection['chosen']['params'] and identity['spec']==cfg['portfolio'][0],'Head recipe differs from selected H6')
  need(identity['context']['selection_sha256']==selection_sha and identity['query_indices']==list(range(4905,5655)) and identity['training_indices']==np.flatnonzero(train[t].notna()).tolist(),'Head row/selection identity mismatch')
  order=json.loads((d/'feature-order.json').read_text());need(order==expected_order==identity['feature_order'] and sha(d/'feature-order.json')==models['feature_order_sha256'],'Wrong720 feature order')
  need(sha(d/'query-predictions.npy')==r['predictions_sha256'],'Saved head prediction hash mismatch');p=np.load(d/'query-predictions.npy',allow_pickle=False);need(p.shape==(750,) and np.isfinite(p).all(),'Invalid head predictions');predictions.append(p)
  for name in ['head.joblib','booster.txt','receipt.json','feature-order.json','query-predictions.npy']:assets[t+'/'+name]=record(d/name)
 native=pd.read_csv(pin(final['files']['native_blind_raw'],'native raw')).set_index('Molecule_Name').loc[blind.Molecule_Name,TARGETS].to_numpy();raw=pd.read_csv(out/'final-test-raw.csv')
 need(raw.Molecule_Name.tolist()==blind.Molecule_Name.tolist() and raw.SMILES.tolist()==blind.SMILES.tolist(),'Raw identity/order mismatch')
 need(np.allclose((1-weights)*native+weights*np.column_stack(predictions),raw[TARGETS].to_numpy(),atol=1e-12,rtol=0),'Saved-head/native reconstruction differs from raw CSV')
 return assets,blind

def verify_deep_contract(source,config):
 # Read-only checks in the actual run's committed source; never calls evaluator or fit.
 code="""import json,sys\nfrom pathlib import Path\nfrom night.locked_h6_final import check_locked_config\nfrom night.final_feature_run import validate_bridge_config\nfrom night.final_feature_contract import validate_artifacts\ncfg=json.loads(Path(sys.argv[1]).read_text());check_locked_config(cfg);validate_bridge_config(cfg);m,p,c,f=validate_artifacts(cfg);print(json.dumps({'validated':True,'features':len(c),'requested':m['expected_requests'],'terminal':m['observed_requests'],'fits_started':0}))"""
 r=subprocess.run([sys.executable,'-c',code,str(config)],cwd=source,capture_output=True,text=True,timeout=90)
 need(r.returncode==0,'Final source input/recipe gate failed; inspect actual final receipts')
 v=json.loads(r.stdout.strip().splitlines()[-1]);need(v=={'validated':True,'features':120,'requested':32421,'terminal':32421,'fits_started':0},'Full32421 input approval missing');return v

def guard_ledger(ledger,csv_sha,when):
 need(not (ledger/'attempts'/csv_sha).exists(),'This exact CSV already had a dispatch attempt; no automatic retry')
 latest=None;records=[]
 for p in sorted((ledger/'attempts').glob('*/attempt.json')):
  a=json.loads(p.read_text())
  if a.get('username')!='AdeliyaLL' or a.get('track')!='regression':continue
  rp=p.parent/'receipt.json';r=json.loads(rp.read_text()) if rp.exists() else {'status':'unknown'};status=r.get('status','unknown')
  if status in ['accepted_pending','unknown']:
   cp=p.parent/'reconciliation.json';need(cp.is_file(),'Unreconciled accepted/ambiguous prior submission blocks another dispatch');v=json.loads(cp.read_text());need(v.get('csv_sha256')==a['csv_sha256'] and v.get('status') in ['processed','rejected','not_received'],'Invalid reconciliation');pin(v.get('evidence'),'prior submission reconciliation');status=v['status']
  sent=datetime.fromisoformat(a['dispatched_utc']);need(sent.tzinfo is not None,'Naive ledger timestamp')
  if status not in ['rejected','not_received']:latest=max(latest,sent) if latest else sent
  records.append({'attempt':record(p),'receipt':record(rp) if rp.exists() else None,'reconciled_status':status})
 if latest:need((when-latest).total_seconds()>=43200,'12-hour per-track cooldown is still active')
 return {'last_counted_local_dispatch_utc':latest.isoformat() if latest else None,'records':records}

def prepare(manifest_path):
 manifest_path=Path(manifest_path);m=json.loads(manifest_path.read_text());need(m.get('protocol')=='goal-20261026_locked_H6_v1' and m.get('old_two_seed_gate_used') is False,'Wrong submission protocol')
 paths={k:pin(v,k) for k,v in m['files'].items()};l=legacy();contract=json.loads(paths['live_contract'].read_text())
 for k,r in contract['source_snapshots'].items():pin(r,'live source '+k)
 pin(contract['api_schema'],'live API schema');need(now()<datetime.fromisoformat(contract['final_deadline_utc']),'Official final deadline has passed');need(contract['phase'] in [1,2] and contract['rows']==750 and contract['cooldown_hours_per_track']==12,'Reviewed rules differ')
 signature=l._check_sources({k:Path(contract['source_snapshots'][k]['path']).read_text() for k in ['app','submission','config']},json.loads(Path(contract['api_schema']['path']).read_text()));need(signature==contract['api_signature'],'API contract mismatch')
 run=json.loads(paths['run_receipt'].read_text());row=run['run'];need(row['experiment_id']==m['expected_final_experiment']==NODE and row['status']=='done' and row['command']=='bash run.sh','Actual completed H6 ORX run missing')
 for k,r in run['source_files'].items():pin(r,'actual run source '+k)
 pin(run['exit_receipt'],'ORX exit');pin(run['run_log'],'ORX log');need(Path(run['exit_receipt']['path']).read_text().strip()=='0','Nonzero final run')
 c=sqlite3.connect('file:'+str(ORX/'orx.db')+'?mode=ro',uri=True);live=c.execute('select experiment_id,status,command,commit_sha from runs where id=?',(row['id'],)).fetchone();need(live==(NODE,'done','bash run.sh',row['commit_sha']),'ORX source/status no longer matches receipt')
 source=Path(run['source_root']);need(source.resolve()==(ORX/'local-runs'/row['id']/'repo').resolve(),'Source is not the actual ORX run snapshot');need(paths['final_config'].resolve()==(source/'final_feature_config.json').resolve(),'Final config not from actual run source')
 cfg=json.loads(paths['final_config'].read_text());need(cfg.get('training_enabled') is True,'Final run was not enabled')
 decision=json.loads(paths['decision'].read_text());need(sha(paths['decision'])==cfg['validated_recipe_decision_sha256'],'Decision binding mismatch')
 need(decision['selected_recipe']=='H6 lightgbm__adme720 with native_blend_per_target' and decision['serving_lane']=='native_published_placement' and decision['blend_modes']==['per_target'],'Not the locked H6 decision')
 deep=verify_deep_contract(source,paths['final_config']);snapshot_path=model_path(cfg['snapshot_manifest'],source);need(sha(snapshot_path)==cfg['snapshot_manifest_sha256'],'Snapshot hash mismatch');snapshot=json.loads(snapshot_path.read_text());final_path=model_path(cfg['final_manifest'],source);need(sha(final_path)==cfg['final_manifest_sha256'],'Final manifest hash mismatch');final=json.loads(final_path.read_text())
 audit=json.loads(pin(snapshot['files']['full_outcome_audit'],'full v3 output audit').read_text());need(audit.get('audit_version')=='final-output-v3','Final v3 audit required')
 approval=json.loads(pin(final['files']['full_goal_approval'],'full-goal approval').read_text());need(approval['approved_for_finalfit'] is True and approval['terminal_count']==approval['audited_requests']==32421 and approval['pending_count']==0 and approval['official_eligible_rows']==5655,'Whole-goal approval incomplete')
 done=json.loads(paths['final_complete'].read_text());out=paths['final_complete'].parent;need(out.resolve()==model_path(cfg['output_dir'],source),'Output directory differs from final config')
 need(done['status']=='ready_for_report_and_submission_review' and done['selected_option']==RECIPE and done['submission_lane']==m['serving_lane']=='native_published_placement','Actual final H6 export not complete')
 need(done['no_submission'] is True and done['no_publication'] is True and done['no_blind_labels_loaded'] is True,'Unexpected final-run side effects')
 ident=done['input_identity'];need(ident['config']==cfg and ident['goal_terminal_count']==32421 and ident['official_training_rows']==4905 and ident['blind_rows']==750,'Final input identity mismatch')
 need(ident['feature_manifest_sha256']==cfg['snapshot_manifest_sha256'] and ident['final_manifest_sha256']==cfg['final_manifest_sha256'] and ident['runtime']==done['packages'],'Final input/runtime binding mismatch')
 need(all(done['packages'][k]==v for k,v in cfg['required_runtime'].items()),'Final runtime differs from locked H6')
 selection=json.loads(paths['selection'].read_text());need(sha(paths['selection'])==done['selection_sha256'] and selection['chosen']['name']==RECIPE and selection['chosen']['mode']=='per_target' and selection['submission_lane']=='native_published_placement','Final selection mismatch')
 recipe=selection['recipes']['lightgbm__adme720'];best=min(recipe['candidates'],key=lambda x:(x['training_OOF']['macro']['ST_RAE'],x['candidate']));need(len(recipe['candidates'])==2 and best==recipe['selected'] and selection['chosen']['params']==best['params'] and recipe['spec']==cfg['portfolio'][0],'Final H6 grid selection mismatches training OOF')
 heads,blind=verify_heads(out,selection,done,cfg,snapshot,final);validation=json.loads(paths['submission_validation'].read_text());csv_path=paths['submission_csv'];csv_sha=sha(csv_path)
 need(csv_sha==done['submission_sha256']==validation['chosen']['sha256'] and validation['valid'] is True and validation['lane']=='native_published_placement','Final CSV validation receipt mismatch')
 for key in ['exact_official_order','exact_smiles','finite','spread_valid']:need(validation['chosen'][key] is True,'Missing CSV check:'+key)
 need(validation['chosen']['rows']==750,'CSV row receipt mismatch');pred=pd.read_csv(csv_path);need(pred.Molecule_Name.tolist()==blind.Molecule_Name.tolist() and pred.SMILES.tolist()==blind.SMILES.tolist(),'Exact official query order/SMILES required')
 validator=source/'vendor/final_activity_validation.py';need(sha(validator)==validation['official_validator_sha256'],'Official validator differs');csv_checks=validate_csv(csv_path,snapshot['files']['official_test']['path'],validator)
 placement=json.loads(paths['placement'].read_text());need(placement.get('usage')=='locked_final_serving_policy' and placement.get('diagnostic_only') is False and placement.get('uses_published_leaderboard_derived_constants') is True,'Serving placement declaration mismatch')
 identity=json.loads(paths['identity'].read_text());prior=json.loads(pin(identity['source_intent'],'prior actual intent').read_text())['api_arguments_without_file'];args=identity['api_arguments_preserved'];need(set(args)==set(IDENTITY_FIELDS) and args=={k:prior[k] for k in IDENTITY_FIELDS},'Identity/contact/consent settings changed')
 for k in ['anon_checkbox','paper_checkbox','proprietary_data_checkbox','open_code_checkbox']:need(isinstance(args[k],bool),'Checkbox must remain explicit boolean')
 need(args['username']=='AdeliyaLL' and args['user_alias']=='AdeliyaLL-CYP' and args['track_select']=='Regression Prediction','Prior identity mismatch')
 report=json.loads(paths['public_report_receipt'].read_text());valid_public_url(m['report_url']);need(report.get('public_https_verified') is True and report.get('verified_without_credentials') is True and report['url']==m['report_url'] and report['submission_csv_sha256']==csv_sha,'Public HTTPS report verification missing')
 args={**args,'model_tag':m['report_url']};ledger=Path(m['ledger']);need(ledger==LEDGER,'Use shared prior submission ledger');history=guard_ledger(ledger,csv_sha,now())
 body={'schema_version':2,'protocol':m['protocol'],'recipe':RECIPE,'serving_lane':'native_published_placement','old_two_seed_gate_used':False,'api_signature':signature,'api_arguments_without_file':args,'gradio_client_version':m['gradio_client_version'],'manifest':record(manifest_path),'transport_wrapper':record(__file__),'live_contract_helper':record(ROOT/'live_contract.py'),'legacy_mechanics':record(LEGACY),'assets':{k:record(p) for k,p in paths.items()},'actual_source_commit':row['commit_sha'],'actual_orx_run_id':row['id'],'actual_orx_experiment':row['experiment_id'],'snapshot_manifest':record(snapshot_path),'final_manifest':record(final_path),'full_goal_approval':record(final['files']['full_goal_approval']['path']),'full_v3_audit':record(snapshot['files']['full_outcome_audit']['path']),'deep_input_contract':deep,'saved_heads':heads,'validation':csv_checks,'submission_csv_sha256':csv_sha,'identity_source':identity['source_intent'],'live_contract_revision':contract['space_revision'],'prior_history':history,'disclosures':{'qualified_legacy_native_source_policy':True,'published_leaderboard_placement':True,'reused_development_selection':True,'ADME_and_ADMET_pretraining_membership_unknown':True}}
 intent_id=hashlib.sha256(l._json_bytes(body)).hexdigest();directory=ledger/'intents'/intent_id;l._immutable(directory/'intent.json',l._json_bytes(body));l._immutable(directory/'submission.csv',csv_path.read_bytes())
 if not (directory/'preparation.json').exists():l._immutable(directory/'preparation.json',l._json_bytes({'prepared_utc':now().isoformat(),'intent_id':intent_id,'csv_sha256':csv_sha,'protocol':m['protocol'],'no_submission':True,'explicit_root_send_required':True}))
 return {'status':'offline_verified_H6_intent','intent_id':intent_id,'intent_dir':str(directory),'csv_sha256':csv_sha,'intent':body,'contract':contract}

def dispatch_once(prepared,transport,ledger,report_check):
 """Only called after explicit --send; no retries, even after ambiguous upload/POST."""
 l=legacy();csv_sha=prepared['csv_sha256'];guard_ledger(ledger,csv_sha,now());d=Path(prepared['intent_dir']);need(sha(d/'submission.csv')==csv_sha and hashlib.sha256(l._json_bytes(prepared['intent'])).hexdigest()==prepared['intent_id'],'Frozen intent changed')
 target=ledger/'attempts'/csv_sha;target.mkdir(parents=True,exist_ok=False);start=time.monotonic();attempt={'schema_version':2,'protocol':prepared['intent']['protocol'],'csv_sha256':csv_sha,'intent_id':prepared['intent_id'],'username':'AdeliyaLL','track':'regression','dispatched_utc':now().isoformat(),'status':'dispatch_started','one_dispatch_only':True,'report_check':report_check};l._immutable(target/'attempt.json',l._json_bytes(attempt))
 try:
  response=transport.submit_once(prepared['intent']['api_arguments_without_file'],d/'submission.csv');status,message=l.classify_response(response);receipt={'status':status,'response':response,'message':message}
 except Exception as exc:receipt={'status':'unknown','exception_type':type(exc).__name__}
 receipt.update({'received_utc':now().isoformat(),'transport_elapsed_seconds':time.monotonic()-start,'csv_sha256':csv_sha,'intent_id':prepared['intent_id'],'submission_id':None,'submission_id_note':'API does not return backend ID; not invented','retry_permitted':False,'accepted_is_not_scored':True,'next_action':'Root reconciles actual receipt/leaderboard; no automatic retry after ambiguous request'})
 l._immutable(target/'receipt.json',l._json_bytes(receipt));return receipt

def send(prepared):
 ledger=LEDGER;ledger.mkdir(parents=True,exist_ok=True)
 with (ledger/'.send.lock').open('a') as lock:
  fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);guard_ledger(ledger,prepared['csv_sha256'],now())
  stamp=now().strftime('%Y%m%dT%H%M%S%fZ');live_path=refresh(ROOT/'live-checks'/stamp);live=json.loads(live_path.read_text());old=prepared['contract']
  need(live['space_revision']==old['space_revision'] and live['api_signature']==old['api_signature'] and all(live['source_snapshots'][k]['sha256']==v['sha256'] for k,v in old['source_snapshots'].items()),'Official code/API drift; review and prepare a new intent before upload')
  need(live['phase'] in [1,2] and now()<datetime.fromisoformat(live['final_deadline_utc']),'Challenge is closed')
  need(now()>=datetime.fromisoformat(live['conservative_public_cooldown_until_utc']),'Public latest submission is still within cooldown')
  receipt=check_report(prepared['intent']['api_arguments_without_file']['model_tag'],prepared['csv_sha256'],ROOT/'live-checks'/stamp/'report.json');transport=legacy().GradioTransport(prepared['intent']['gradio_client_version'])
  need(legacy()._schema_signature(transport.api_info())==prepared['intent']['api_signature'],'Live API differs just before send')
  return dispatch_once(prepared,transport,ledger,{'live_contract':record(live_path),'public_report':record(ROOT/'live-checks'/stamp/'report.json')})

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest');p.add_argument('--send',action='store_true',help='Explicit root dispatch only; never automatic');p.add_argument('--refresh-live',action='store_true');p.add_argument('--capture-run');p.add_argument('--check-report');p.add_argument('--csv-sha');p.add_argument('--build-manifest',action='store_true');p.add_argument('--run-receipt');p.add_argument('--report-url');p.add_argument('--report-receipt');p.add_argument('--live-contract');p.add_argument('--output');a=p.parse_args()
 if a.refresh_live:print(json.dumps({'contract':str(refresh(a.output or ROOT/'live-checks'/now().strftime('%Y%m%dT%H%M%S%fZ'))),'submission_performed':False}));return
 if a.capture_run:capture_run(a.capture_run,a.output);print(json.dumps({'run_receipt':a.output,'submission_performed':False}));return
 if a.check_report:check_report(a.check_report,a.csv_sha,a.output);print(json.dumps({'public_report_receipt':a.output,'submission_performed':False}));return
 if a.build_manifest:build_manifest(a.run_receipt,a.report_url,a.report_receipt,a.output,a.live_contract);print(json.dumps({'manifest':a.output,'submission_performed':False}));return
 need(a.manifest,'--manifest is required');prepared=prepare(a.manifest)
 if a.send:
  result=send(prepared);print(json.dumps({k:v for k,v in result.items() if k not in ['response','message']}));return 0 if result['status']=='accepted_pending' else 2
 print(json.dumps({k:v for k,v in prepared.items() if k not in ['intent','contract']}))
if __name__=='__main__':
 try:raise SystemExit(main() or 0)
 except Exception as exc:
  # Do not print network/header-bearing exception details or credentials.
  print(json.dumps({'status':'blocked_or_failed','exception_type':type(exc).__name__,'reason':str(exc) if isinstance(exc,GuardError) else 'Inspect private receipts; no automatic retry','submission_retry_permitted':False}));raise SystemExit(2)
