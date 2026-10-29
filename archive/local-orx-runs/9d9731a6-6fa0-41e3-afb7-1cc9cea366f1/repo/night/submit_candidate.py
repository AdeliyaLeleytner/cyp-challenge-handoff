"""Prepare a frozen CYP submission intent; default is offline dry-run.

Only the root may later invoke --send after reviewing the pass certificate and
final package. This module never trains, publishes code, invents identity, retries
an upload, or resolves an ambiguous submission outcome automatically.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import ast
import csv
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
import re
import numpy as np
import pandas as pd

SPACE='https://openadmet-cyp-challenge.hf.space'
API_NAME='/submit_predictions'
USERNAME='AdeliyaLL'
ALIAS='AdeliyaLL-CYP'
TARGETS=[f'{c}_pIC50_direct_inhibition' for c in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
PARAMETERS=['username','user_alias','anon_checkbox','participant_name','discord_username','email',
            'affiliation','model_tag','paper_checkbox','proprietary_data_checkbox','open_code_checkbox',
            'track_select','file_input']
REQUIRED_COHORTS={'own750','briford529'}
REQUIRED_SEEDS={'42','142'}
REFERENCE_MEMBERS={'union18','mtaux8','2d6isoform6','2d6single'}
GATE_CODE_SHA256='3d3d0a3422247ef12553959db508c8af1e61a7993a98911b117ac5aa89cd3705'
OFFICIAL_TEST_MAPPING_SHA256='1976cf8d7719a928419e408d87fd2aa6bd0abeee3da3e7ae98169cb557efe738'
VALIDATOR_SHA256='276a53d7f22ff973aaf567e64d977202995e91ba3cef2bbdc4de71c13bdebcb2'


def _now(): return datetime.now(timezone.utc).isoformat()
def _sha_bytes(value): return hashlib.sha256(value).hexdigest()
def _sha(path): return _sha_bytes(Path(path).read_bytes())
def _json_bytes(value): return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def _immutable(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=value: raise FileExistsError(f'Immutable artifact differs: {path}')
        return
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream: stream.write(value)

def _record(record,base,label):
    if not isinstance(record,dict) or not re.fullmatch(r'[a-fA-F0-9]{64}',str(record.get('sha256',''))):
        raise ValueError(f'{label}: explicit path/SHA256 record required')
    path=Path(record['path']).expanduser()
    if not path.is_absolute(): path=base/path
    path=path.resolve();raw=path.read_bytes();sha=_sha_bytes(raw)
    if sha!=record['sha256'].lower(): raise ValueError(f'{label}: SHA256 mismatch')
    return path,raw,{'path':str(path),'sha256':sha,'bytes':len(raw)}

def _schema_signature(info):
    endpoint=info['named_endpoints'][API_NAME]
    parameters=endpoint['parameters']
    if [p['parameter_name'] for p in parameters]!=PARAMETERS:
        raise ValueError('Submission API drift: expected the verified13 named arguments')
    kinds=[p.get('component') for p in parameters]
    if kinds!=['Textbox','Textbox','Checkbox','Textbox','Textbox','Textbox','Textbox','Textbox',
               'Checkbox','Checkbox','Checkbox','Radio','File']:
        raise ValueError('Submission API component signature drift')
    defaults={p['parameter_name']:p.get('parameter_default') for p in parameters if p.get('parameter_has_default')}
    for key,value in {'anon_checkbox':True,'paper_checkbox':False,'proprietary_data_checkbox':False,'open_code_checkbox':False}.items():
        if defaults.get(key) is not value: raise ValueError(f'Unexpected API checkbox default: {key}')
    tracks=parameters[11].get('type',{}).get('enum',[])
    if 'Regression Prediction' not in tracks: raise ValueError('Regression track absent from live API')
    return {'api_name':API_NAME,'parameters':PARAMETERS,'components':kinds,'track_choices':tracks,
        'defaults':defaults,'returns':[r.get('component') for r in endpoint['returns']]}

def _check_sources(sources,schema):
    module=ast.parse(sources['submission'])
    function=next(n for n in module.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=='submit_predictions')
    if [a.arg for a in function.args.args]!=PARAMETERS: raise ValueError('Pinned server source signature does not match API')
    constants={}
    for node in ast.parse(sources['config']).body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            try: constants[node.targets[0].id]=ast.literal_eval(node.value)
            except (ValueError,TypeError): pass
    if constants.get('CURRENT_PHASE') not in [1,2]: raise ValueError('Pinned challenge source is not an open phase')
    if constants.get('HOURS_BETWEEN_SUBMISSIONS')!=12 or constants.get('MIN_PREDICTION_STD')!=.01:
        raise ValueError('Pinned cooldown/variance rule changed; root must review source')
    if constants.get('ACTIVITY_DATASET_SIZE')!=750 or constants.get('REGRESSION_ENDPOINTS')!=TARGETS:
        raise ValueError('Pinned activity schema changed')
    return _schema_signature(schema)

def _check_gate(cert,candidate):
    if cert.get('schema_version')!=1 or cert.get('status')!='pass' or cert.get('passed') is not True or cert.get('reasons')!=[]:
        raise ValueError('An unblocked schema1 PASS gate certificate is mandatory')
    if cert.get('gate_source_sha256')!=GATE_CODE_SHA256: raise ValueError('Unreviewed promotion-gate implementation hash')
    if set(cert.get('required_cohorts',[]))!=REQUIRED_COHORTS or set(map(str,cert.get('required_seeds',[])))!=REQUIRED_SEEDS:
        raise ValueError('Gate must cover own750, briford529 and matched seeds42,142')
    if cert.get('targets')!=TARGETS: raise ValueError('Gate must cover all4 canonical targets')
    if cert.get('candidate_name')!=candidate or cert.get('reference_name')!='briford_reference':
        raise ValueError('Qualified candidate/reference identity mismatch')
    if set(cert.get('reference_recipe_members',[]))!=REFERENCE_MEMBERS: raise ValueError('Wrong reference recipe')
    rows=cert.get('score_table',[])
    if len(rows)!=4 or {(r['cohort'],str(r['seed'])) for r in rows}!={(c,s) for c in REQUIRED_COHORTS for s in REQUIRED_SEEDS}:
        raise ValueError('Gate score table lacks required cohort/seed combinations')
    def macro(measured):
        if measured.get('defined') is not True or set(measured.get('endpoints',{}))!=set(TARGETS):
            raise ValueError('Gate score lacks defined all4-target metrics')
        value=measured.get('macro_ST_RAE',float('nan'))
        if not np.isfinite(value) or not all(np.isfinite(v.get('ST_RAE',float('nan'))) for v in measured['endpoints'].values()):
            raise ValueError('Gate score has a nonfinite metric')
        if not np.isclose(value,np.mean([v['ST_RAE'] for v in measured['endpoints'].values()]),rtol=0,atol=1e-12):
            raise ValueError('Gate macro metric is inconsistent with its4 target metrics')
        return value
    row_deltas={cohort:[] for cohort in REQUIRED_COHORTS}
    for row in rows:
        difference=macro(row['candidate'])-macro(row['reference'])
        if not np.isclose(difference,row['delta'],rtol=0,atol=1e-12): raise ValueError('Gate row delta is inconsistent')
        row_deltas[row['cohort']].append(difference)
    for cohort in REQUIRED_COHORTS:
        for field in ['comparisons','averaged_prediction_scores']:
            entry=cert[field][cohort];delta=entry['delta_candidate_minus_reference']
            if not isinstance(delta,(int,float)) or not np.isfinite(delta) or not delta<0:
                raise ValueError(f'{cohort}: {field} improvement is not strictly negative')
            expected=np.mean(row_deltas[cohort]) if field=='comparisons' else macro(entry['candidate'])-macro(entry['reference'])
            if not np.isclose(delta,expected,rtol=0,atol=1e-12): raise ValueError('Gate aggregate delta is inconsistent with scores')
    evidence=cert.get('evidence_hashes')
    if not isinstance(evidence,dict) or not evidence: raise ValueError('Gate has no hashed evidence')
    for record in evidence.values():
        if not isinstance(record,dict) or not record.get('path') or not re.fullmatch(r'[a-fA-F0-9]{64}',str(record.get('sha256',''))):
            raise ValueError('Malformed gate evidence hash record')

def _check_final_provenance(prov,manifest,assets,base):
    expected={'candidate_name':manifest['candidate_name'],'recipe_sha256':assets['qualified_recipe']['sha256'],
        'gate_certificate_sha256':assets['gate_certificate']['sha256'],
        'submission_csv_sha256':assets['submission_csv']['sha256'],
        'official_test_sha256':assets['official_test']['sha256']}
    if prov.get('status') not in {'done','completed'}: raise ValueError('Final training provenance is not completed')
    for key,value in expected.items():
        if prov.get(key)!=value: raise ValueError(f'Final training provenance {key} mismatch')
    if prov.get('training_scope')!='full_official_train' or prov.get('actual_test_scored') is not False:
        raise ValueError('Provenance must certify full official TRAIN fit and no actual TEST scoring')
    if set(map(str,prov.get('seeds',[])))!=REQUIRED_SEEDS or prov.get('targets')!=TARGETS:
        raise ValueError('Final prediction ensemble must match seeds42+142/all4targets qualification')
    if prov.get('recipe_match_verified') is not True: raise ValueError('Root recipe-match review must be recorded in final provenance')
    runs=prov.get('source_runs')
    if not isinstance(runs,list) or not runs: raise ValueError('Final completed ORX source-run evidence required')
    checked=[]
    for index,run in enumerate(runs):
        if run.get('status') not in {'done','completed'} or not run.get('run_id'): raise ValueError('Incomplete final source run')
        _,raw,record=_record(run.get('evidence'),base,f'final source run{index}')
        state=json.loads(raw);state=state.get('run',state)
        if state.get('status')!='done' or str(state.get('run_id',state.get('id')))!=str(run['run_id']) or state.get('exit_code') not in (None,0):
            raise ValueError('Final ORX source evidence is not matching terminal success')
        checked.append(record)
    return checked

def _validate_csv(path,raw,test_raw,validator_path):
    test=pd.read_csv(io.BytesIO(test_raw),dtype={'Molecule_Name':str,'SMILES':str})
    prediction=pd.read_csv(io.BytesIO(raw),dtype={'Molecule_Name':str,'SMILES':str})
    expected_columns={'Molecule_Name','SMILES',*TARGETS}
    if len(prediction)!=750 or len(prediction.columns)!=6 or set(prediction)!=expected_columns:
        raise ValueError('Submission must have exactly750 rows and the6 required columns')
    for frame,label in [(test,'official TEST'),(prediction,'submission')]:
        if len(frame)!=750 or frame[['Molecule_Name','SMILES']].isna().any().any() or frame.Molecule_Name.duplicated().any():
            raise ValueError(f'{label}: invalid actual TEST identifiers')
    mapping=sorted(test[['Molecule_Name','SMILES']].values.tolist())
    mapping_sha=_sha_bytes(json.dumps(mapping,separators=(',',':'),ensure_ascii=False).encode())
    if mapping_sha!=OFFICIAL_TEST_MAPPING_SHA256: raise ValueError('This is not the pinned actual blinded TEST750 structure mapping')
    if set(prediction.Molecule_Name)!=set(test.Molecule_Name): raise ValueError('Submission IDs are not actual TEST750 IDs')
    aligned=prediction.set_index('Molecule_Name').loc[test.Molecule_Name]
    if aligned.SMILES.tolist()!=test.SMILES.tolist(): raise ValueError('SMILES must match official TEST exactly for each ID')
    std={}
    for target in TARGETS:
        if not pd.api.types.is_numeric_dtype(prediction[target]) or pd.api.types.is_bool_dtype(prediction[target]):
            raise ValueError(f'{target}: pIC50 values must be numeric')
        values=prediction[target].to_numpy(float)
        if not np.isfinite(values).all(): raise ValueError(f'{target}: nonfinite values')
        std[target]=float(prediction[target].std(ddof=1))
        if prediction[target].nunique()<=1 or std[target]<.01: raise ValueError(f'{target}: constant/near-constant predictions')
    # Run the pinned official tutorial validator, then retain the stronger exact
    # column/mapping and current Space std checks above (the tutorial omits std).
    if _sha(validator_path)!=VALIDATOR_SHA256: raise ValueError('Unreviewed official-validator source hash')
    spec=importlib.util.spec_from_file_location('_cyp_official_submission_validator',validator_path)
    validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
    if _sha(path)!=_sha_bytes(raw): raise ValueError('CSV changed during offline validation')
    valid,errors=validator.validate_activity_submission(path,expected_ids=set(test.Molecule_Name))
    if _sha(path)!=_sha_bytes(raw): raise ValueError('CSV changed during official validation')
    if not valid: raise ValueError('Official validator failed: '+str(errors))
    return {'rows':750,'columns':prediction.columns.tolist(),'std_ddof1':std,
        'official_test_mapping_sha256':mapping_sha,'official_validator_passed':True,
        'independent_id_smiles_check_passed':True,'extra_current_space_std_check_passed':True}

def prepare(manifest_path,ledger_dir):
    """Offline verification and immutable intent; no client is imported or contacted."""
    manifest_path=Path(manifest_path).resolve();base=manifest_path.parent
    raw_manifest=manifest_path.read_bytes();manifest=json.loads(raw_manifest)
    if manifest.get('schema_version')!=1 or not manifest.get('candidate_name'): raise ValueError('Submission manifest schema1/candidate_name required')
    required=['qualified_recipe','gate_certificate','final_training_provenance','submission_csv','official_test','official_validator','api_schema']
    assets={};raw={};paths={}
    for key in required:
        paths[key],raw[key],assets[key]=_record(manifest.get(key),base,key)
    source_text={};source_assets={}
    for key in ['app','submission','config']:
        _,text,source_assets[key]=_record(manifest.get('source_snapshots',{}).get(key),base,'source '+key)
        source_text[key]=text.decode()
    signature=_check_sources(source_text,json.loads(raw['api_schema']))
    certificate=json.loads(raw['gate_certificate']);_check_gate(certificate,manifest['candidate_name'])
    recipe=json.loads(raw['qualified_recipe'])
    if recipe.get('candidate_name')!=manifest['candidate_name']: raise ValueError('Qualified recipe candidate_name mismatch')
    provenance=json.loads(raw['final_training_provenance'])
    runs=_check_final_provenance(provenance,manifest,assets,paths['final_training_provenance'].parent)
    validation=_validate_csv(paths['submission_csv'],raw['submission_csv'],raw['official_test'],paths['official_validator'])
    tag=manifest.get('model_tag')
    if not isinstance(tag,str) or not tag.strip(): raise ValueError('A truthful actual model_tag is required')
    disclosures=manifest.get('disclosures',{})
    proprietary=disclosures.get('used_proprietary_data',False)
    open_code=disclosures.get('open_source_code',False)
    if type(proprietary) is not bool or type(open_code) is not bool: raise ValueError('Disclosure flags must be explicit booleans')
    if disclosures.get('publication_opt_in',False) is not False: raise ValueError('Publication inclusion is not authorized by this preparation')
    if open_code:
        published=manifest.get('published_code',{})
        if published.get('verified_public') is not True or published.get('url')!=tag or not tag.startswith('https://'):
            raise ValueError('OpenCode requires an actual already-public URL with root verification')
    args={'username':USERNAME,'user_alias':ALIAS,'anon_checkbox':True,'participant_name':'',
        'discord_username':'','email':'','affiliation':'','model_tag':tag.strip(),
        'paper_checkbox':False,'proprietary_data_checkbox':proprietary,'open_code_checkbox':open_code,
        'track_select':'Regression Prediction'}
    body={'schema_version':1,'candidate_name':manifest['candidate_name'],'space':SPACE,'api_signature':signature,
        'api_arguments_without_file':args,'assets':assets,'source_snapshots':source_assets,
        'final_source_runs':runs,'validation':validation,'submission_manifest_sha256':_sha_bytes(raw_manifest),
        'gradio_client_version':manifest.get('gradio_client_version'),
        'disclosure_semantics':'proprietary_data_checkbox=True means nonpublic/proprietary training data WAS used; it is not a permission checkbox.',
        'gate_qualification':'Observed gains on reused cohorts and matched seeds, not a guarantee of blinded TEST success.'}
    intent_id=_sha_bytes(_json_bytes(body));directory=Path(ledger_dir).resolve()/'intents'/intent_id
    _immutable(directory/'intent.json',_json_bytes(body))
    _immutable(directory/'submission.csv',raw['submission_csv'])
    _immutable(directory/'gate_certificate.json',raw['gate_certificate'])
    _immutable(directory/'submission_manifest.json',raw_manifest)
    return {'intent_id':intent_id,'intent_dir':str(directory),'csv_sha256':assets['submission_csv']['sha256'],
        'intent':body,'status':'dry_run_verified_no_network'}

class GradioTransport:
    """Official gradio_client adapter; instantiated only by explicit --send."""
    def __init__(self,expected_version):
        if not expected_version: raise ValueError('Pin installed gradio_client_version in submission manifest before --send')
        actual=importlib.metadata.version('gradio_client')
        if actual!=expected_version: raise ValueError('Installed gradio_client differs from the pinned manifest version')
        from gradio_client import Client,handle_file
        self.client=Client(SPACE,verbose=False);self.handle_file=handle_file
    def api_info(self):
        return self.client.view_api(print_info=False,return_format='dict')
    def submit_once(self,arguments,file_path):
        values=[arguments[name] for name in PARAMETERS[:-1]]+[self.handle_file(str(file_path))]
        return self.client.predict(*values,api_name=API_NAME)

def classify_response(response):
    if isinstance(response,dict) and isinstance(response.get('value'),str): message=response['value']
    elif isinstance(response,str): message=response
    elif isinstance(response,(list,tuple)) and len(response)==1: return classify_response(response[0])
    else: return 'unknown',None
    if message.startswith('Submission received from ') and 'being processed' in message:
        return 'accepted_pending',message
    if message.startswith('Error:'): return 'rejected',message
    return 'unknown',message

def _guard_ledger(ledger,csv_sha,now):
    attempt_root=ledger/'attempts'
    if (attempt_root/csv_sha).exists(): raise RuntimeError('This CSV hash already had a dispatch attempt; no duplicate/retry is permitted')
    for path in attempt_root.glob('*/attempt.json'):
        attempt=json.loads(path.read_text());receipt_path=path.parent/'receipt.json'
        receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'status':'unknown'}
        if receipt['status'] in {'accepted_pending','unknown'}:
            reconciliation=path.parent/'reconciliation.json'
            if not reconciliation.exists(): raise RuntimeError('Prior accepted-pending/unknown dispatch must be reconciled before another submission')
            record=json.loads(reconciliation.read_text())
            if record.get('csv_sha256')!=attempt['csv_sha256'] or record.get('status') not in {'processed','rejected','not_received'}:
                raise RuntimeError('Invalid audited prior-submission reconciliation')
            _record(record.get('evidence'),reconciliation.parent,'submission reconciliation')
        sent=datetime.fromisoformat(attempt['dispatched_utc'])
        if sent.tzinfo is None: raise RuntimeError('Ledger timestamp is not timezone-aware')
        if (now-sent).total_seconds()<12*3600: raise RuntimeError('12-hour per-track local cooldown is still active')

def send_prepared(prepared,ledger_dir,transport=None):
    """One explicit root-controlled dispatch; ambiguous outcomes are never retried."""
    import fcntl
    ledger=Path(ledger_dir).resolve();ledger.mkdir(parents=True,exist_ok=True)
    with (ledger/'.send.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        now=datetime.now(timezone.utc);sha=prepared['csv_sha256'];_guard_ledger(ledger,sha,now)
        body=prepared['intent'];directory=Path(prepared['intent_dir']);csv_path=directory/'submission.csv'
        if _sha(csv_path)!=sha or _sha_bytes(_json_bytes(body))!=prepared['intent_id']:
            raise RuntimeError('Frozen intent/CSV changed before dispatch')
        # Read-only live API check occurs before recording/attempting upload.
        if transport is None: transport=GradioTransport(body['gradio_client_version'])
        signature=_schema_signature(transport.api_info())
        if signature!=body['api_signature']: raise RuntimeError('Live API signature differs from reviewed snapshot; do not upload')
        target=ledger/'attempts'/sha;target.mkdir(parents=True,exist_ok=False)
        attempt={'schema_version':1,'csv_sha256':sha,'intent_id':prepared['intent_id'],
            'username':USERNAME,'track':'regression','dispatched_utc':_now(),'status':'dispatch_started',
            'one_dispatch_only':True}
        _immutable(target/'attempt.json',_json_bytes(attempt))
        try:
            response=transport.submit_once(body['api_arguments_without_file'],csv_path)
            status,message=classify_response(response)
            receipt={'status':status,'received_utc':_now(),'csv_sha256':sha,'intent_id':prepared['intent_id'],
                'response':response,'message':message,'submission_id':None,
                'submission_id_note':'Current13-argument endpoint does not return the backend submission ID; do not invent one.',
                'retry_permitted':False,'next_action':'Root verifies receipt/leaderboard; accepted or ambiguous pending requests are not retried.'}
        except Exception as exc:
            # Exception text can contain transport headers; retain only its type.
            receipt={'status':'unknown','received_utc':_now(),'csv_sha256':sha,'intent_id':prepared['intent_id'],
                'exception_type':type(exc).__name__,'retry_permitted':False,
                'next_action':'Reconcile remote receipt before any further submission; do not retry.'}
        _immutable(target/'receipt.json',_json_bytes(receipt))
        return receipt

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--ledger-dir',required=True)
    parser.add_argument('--send',action='store_true',help='Root only, after actual pass and live rule/leaderboard review; performs one upload')
    args=parser.parse_args();prepared=prepare(args.manifest,args.ledger_dir)
    if not args.send:
        print(json.dumps({k:v for k,v in prepared.items() if k!='intent'}),flush=True)
        return 0
    receipt=send_prepared(prepared,args.ledger_dir)
    print(json.dumps(receipt),flush=True)
    return 0 if receipt['status']=='accepted_pending' else 2

if __name__=='__main__': raise SystemExit(main())
