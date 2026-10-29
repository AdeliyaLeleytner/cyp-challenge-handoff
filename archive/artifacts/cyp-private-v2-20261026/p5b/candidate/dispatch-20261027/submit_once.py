"""One human-authorized anchored-candidate dispatch; blank report, no publication hooks."""
from pathlib import Path
from datetime import datetime,timezone
import ast,copy,fcntl,hashlib,json,sys,types,argparse,urllib.request

HERE=Path(__file__).resolve().parent
CAND=HERE.parent
TRANSPORT=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026/model-audit/submission-transport')
sys.path.insert(0,str(TRANSPORT))
import live_contract as lc
import h6_submit as old
EXPECTED='6807263f0ccadcb31aa28a5c54653608e12271939a2490a2404d4353aeb0e16d'
def now():return datetime.now(timezone.utc)
def check_guard(private):
    tree=ast.parse((private/'submission.py').read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='submit_predictions')
    branch=next(n for n in fn.body if isinstance(n,ast.If) and isinstance(n.test,ast.Name) and n.test.id=='open_code_checkbox')
    wrapper=ast.parse('def guard(model_tag,open_code_checkbox):\n pass').body[0]
    wrapper.body=[copy.deepcopy(branch),ast.Return(value=ast.Name(id='model_status',ctx=ast.Load()))]
    module=ast.fix_missing_locations(ast.Module(body=[wrapper],type_ignores=[]))
    def forbidden(*a,**kw):raise AssertionError('Report lookup must not run')
    ns={'validate_model_details':forbidden};exec(compile(module,'isolated_report_guard','exec'),ns)
    assert ns['guard']('',False)=='Not submitted'
    return {'blank_report_closed_code_passed':True,'guard_lines':[branch.lineno,branch.end_lineno],'source_sha256':lc.sha(private/'submission.py')}
def prepare():
    contract_path=HERE/'fresh/contract.json';contract=json.loads(contract_path.read_text());private=HERE/'fresh/private'
    assert contract['phase'] in [1,2] and now()<datetime.fromisoformat(contract['final_deadline_utc'])
    assert now()>=datetime.fromisoformat(contract['conservative_public_cooldown_until_utc'])
    # Correct the documented legacy helper's unconditional public-report assumption.
    report=check_guard(private);contract['public_https_model_report_required']=False
    contract['report_policy']='Blank report with open_code=False explicitly verified from current handler; final eligibility is separate.'
    lc.dump(HERE/'reviewed-contract.json',contract)
    for r in contract['source_snapshots'].values():assert lc.sha(r['path'])==r['sha256']
    identity=json.loads((TRANSPORT/'identity.json').read_text());prior=identity['source_intent']
    assert lc.sha(prior['path'])==prior['sha256']
    args=identity['api_arguments_preserved'];previous=json.loads(Path(prior['path']).read_text())['api_arguments_without_file']
    assert args=={k:previous[k] for k in old.IDENTITY_FIELDS}
    assert args['username']=='AdeliyaLL' and args['user_alias']=='AdeliyaLL-CYP'
    assert args['open_code_checkbox'] is False and args['track_select']=='Regression Prediction'
    args={**args,'model_tag':''}
    csv=CAND/'results/incumbent-anchored-H6-served-PRIVATE.csv';assert lc.sha(csv)==EXPECTED
    proof=json.loads((CAND/'VERIFICATION.json').read_text());assert proof['status']=='pass' and proof['candidate_checks']['served']['sha256']==EXPECTED
    m=json.loads((CAND/'stage/manifest.json').read_text());test=m['files']['official_blind'];assert lc.sha(test['path'])==test['sha256']
    validator=CAND/'stage/activity-validator.py';validation=old.validate_csv(csv,test['path'],validator)
    history=old.guard_ledger(old.LEDGER,EXPECTED,now())
    authorization={'utc':now().isoformat(),'source':'Direct human message in this chat','text':'давай попробуем сейчас заслать наш лучший результат, какой рекомендуешь?','interpretation':'User authorizes one recommended submission now; root recommends the previously reviewed exact anchored candidate. No report/code/weights publication authorized.','candidate_sha256':EXPECTED}
    lc.dump(HERE/'HUMAN_AUTHORIZATION.json',authorization)
    body={'protocol':'private_original_anchored_H6_human_authorized_v1','api_arguments_without_file':args,'submission_csv_sha256':EXPECTED,'gradio_client_version':'2.7.2','api_signature':contract['api_signature'],'reviewed_contract':lc.record(HERE/'reviewed-contract.json'),'candidate_verification':lc.record(CAND/'VERIFICATION.json'),'validation':validation,'report_guard':report,'human_authorization':lc.record(HERE/'HUMAN_AUTHORIZATION.json'),'prior_history':history,'transport_wrapper':lc.record(__file__),'no_report_publication':True}
    l=lc.legacy();iid=hashlib.sha256(l._json_bytes(body)).hexdigest();d=old.LEDGER/'intents'/iid
    l._immutable(d/'intent.json',l._json_bytes(body));l._immutable(d/'submission.csv',csv.read_bytes())
    prepared={'intent_id':iid,'intent_dir':str(d),'csv_sha256':EXPECTED,'intent':body,'contract':contract}
    lc.dump(HERE/'prepared.json',prepared)
    approval=json.loads((CAND/'APPROVAL_STATUS.json').read_text());approval.update(status='human_authorized_recommended_candidate',human_authorization=lc.record(HERE/'HUMAN_AUTHORIZATION.json'),no_publication_authorization=True);lc.dump(CAND/'APPROVAL_STATUS.json',approval)
    return prepared
def send():
    prepared=json.loads((HERE/'prepared.json').read_text())
    assert lc.sha(__file__)==prepared['intent']['transport_wrapper']['sha256']
    assert lc.sha(prepared['intent']['human_authorization']['path'])==prepared['intent']['human_authorization']['sha256']
    assert prepared['intent']['api_arguments_without_file']['model_tag']==''
    assert prepared['intent']['api_arguments_without_file']['open_code_checkbox'] is False
    with (old.LEDGER/'.send.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        old.guard_ledger(old.LEDGER,EXPECTED,now())
        with urllib.request.urlopen('https://huggingface.co/api/spaces/openadmet/cyp-challenge',timeout=30) as r:meta=json.load(r)
        assert meta['sha']==prepared['contract']['space_revision'],'Source changed since review'
        assert now()<datetime.fromisoformat(prepared['contract']['final_deadline_utc'])
        transport=lc.legacy().GradioTransport('2.7.2')
        assert lc.legacy()._schema_signature(transport.api_info())==prepared['intent']['api_signature']
        receipt=old.dispatch_once(prepared,transport,old.LEDGER,{'report_url':'','open_code':False,'guard':prepared['intent']['report_guard'],'human_authorization':prepared['intent']['human_authorization']})
        lc.dump(HERE/'receipt.json',receipt)
        return {k:v for k,v in receipt.items() if k not in ['response','message']}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--send',action='store_true');a=p.parse_args()
    if a.send:print(json.dumps(send()))
    else:
        d=prepare();print(json.dumps({'status':'prepared','sha256':EXPECTED,'intent_id':d['intent_id'],'blank_report':True,'no_dispatch':True}))
