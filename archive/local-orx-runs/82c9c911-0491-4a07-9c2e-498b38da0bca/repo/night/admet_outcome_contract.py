"""Scoped official-input gate; terminal outcomes are not all numeric predictions.

Default use requires the full32421 acquisition audit. Early official-only evaluation
must explicitly pass require_full_acquisition=False and a pinned5655 certificate.
"""
import csv,json,math,hashlib
from pathlib import Path
from .admet_full_contract_v1 import ContractError,digest,read_json,require
SUFFIX='::category=Invalid%20Molecule'
BASE_KEYS=['raw_features','numeric_features','feature_schema','queue','id_map','official_train','official_test','data_disposition','output_disposition','reviewed_exceptions','service_rejections','feature_exclusions','reviewed_standardizations']

PINNED_PROTON_TRANSFER={
 'request_id':'c144a5ae385f54b47f0a911da7ebb3ae9830ac594eb61a8654cf52535823ae26',
 'request_smiles':'[N-]=[NH+]N=CC(=O)c1c[nH]c(=O)[nH]c1=O',
 'service_smiles':'N=NN=CC(=O)c1c[nH]c(=O)[nH]c1=O',
 'raw_row_sha256':'23581c841427c031deba5ce32c6a08315519a42ef5eb22ea0e6fdd47a0f49646',
}
REVIEWED_KINDS={'service_rejected':'service_rejections','unresolved_service_structure':'feature_exclusions','reviewed_internal_proton_transfer':'reviewed_standardizations'}

def validate_reviewed_bindings(policy,binding,files,rejected,excluded,standardized):
    manifests=[('service-rejections.json','service_rejections',rejected,'service_rejected_requests','service_rejected'),('feature-eligibility-exclusions.json','feature_exclusions',excluded,'feature_identity_excluded_requests','unresolved_service_structure'),('reviewed-standardizations.json','reviewed_standardizations',standardized,'reviewed_standardization_requests','reviewed_internal_proton_transfer')]
    sets={};expected_kind={}
    for filename,key,records,policy_key,kind in manifests:
        require(policy['files'][filename]['sha256']==files[key]['sha256'],'Exception approval manifest changed: '+key)
        ids=[x['request_id'] for x in records];require(len(ids)==len(set(ids)),'Duplicate reviewed manifest identity')
        declared=policy.get(policy_key,[]);require(len(declared)==len(set(declared)) and set(ids)==set(declared),'Exception ID policy mismatch: '+key)
        sets[key]=set(ids)
        for rid in ids:
            require(rid not in expected_kind,'Reviewed disposition categories overlap');expected_kind[rid]=kind
    require(sets['reviewed_standardizations']=={PINNED_PROTON_TRANSFER['request_id']},'Only the exact parent-approved proton-transfer case is accepted')
    entries=binding['exceptions'];reviewed={x['request_id']:x for x in entries}
    require(len(entries)==len(reviewed) and set(reviewed)==set(expected_kind),'Unreviewed or duplicate exception entry')
    for rid,record in reviewed.items():
        kind=record.get('kind');require(kind in REVIEWED_KINDS and kind==expected_kind[rid],'Reviewed exception kind/disposition mismatch')
        require(record['approval_manifest_sha256']==files[REVIEWED_KINDS[kind]]['sha256'],'Exception approval hash mismatch')
        if kind=='reviewed_internal_proton_transfer':
            require(all(record.get(key)==value for key,value in PINNED_PROTON_TRANSFER.items()),'Exact approved proton-transfer row/strings changed')
    return reviewed,sets['service_rejections'],sets['feature_exclusions'],sets['reviewed_standardizations']

def rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);require(reader.fieldnames is not None and len(reader.fieldnames)==len(set(reader.fieldnames)),'Duplicate/empty CSV headers');return reader.fieldnames,list(reader)

def require_official_coverage(required,present,excluded):
    require(len(required)==5655,'Official membership must contain5655 unique requests')
    require(required<=present,'Missing official input request(s): '+','.join(sorted(required-present)[:3]))
    require(not required&excluded,'An official input is rejected or feature-ineligible')

def validate_status_flags(raw,feature,column_map,approved):
    rejected=[c for c in column_map if raw[c]=='Invalid Molecule']
    rid=feature['request_id'];allowed=approved.get(rid)
    if allowed:
        row_sha=hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        require(row_sha==allowed['raw_row_sha256'] and raw['raw_smiles']==allowed['request_smiles'] and raw['smiles']==allowed['service_smiles'],'Reviewed exception changed')
    full=bool(rejected)
    if full:require(len(rejected)==120 and allowed and allowed['kind']=='service_rejected','Unapproved or partial service rejection')
    if allowed and allowed['kind']=='service_rejected':require(len(rejected)==120,'Approved rejection outcome changed')
    for col,base in column_map.items():
        flag=feature.get(base+SUFFIX,'');flag=float(flag) if flag not in ('',None) else 0.
        require(flag==float(col in rejected),'Invalid rejection indicator')
        if col in rejected:
            require(feature[base] in ('',None) and base+SUFFIX in feature,'Rejected endpoint fabricated or unflagged')
        else:
            try:value=float(feature[base])
            except (TypeError,ValueError):raise ContractError('Nonnumeric unreviewed endpoint')
            require(math.isfinite(value),'Nonfinite unreviewed endpoint')
    return full

def validate_feature_snapshot(cfg,require_full_acquisition=True):
    require(cfg.get('supervision_scope')=='official_experimental_targets_only','This gate does not approve fresh external supervision')
    name=cfg.get('snapshot_manifest');pin=cfg.get('snapshot_manifest_sha256')
    require(bool(name) and bool(pin),'Complete scoped snapshot manifest and SHA256 must be pinned before any fit')
    require(digest(name)==pin,'Snapshot manifest hash mismatch');m=read_json(name)
    require(m.get('schema_version')==2 and m.get('source_mode')=='web_default','Expected outcome-aware web_default schema2')
    require(m.get('expected_requests')==32421 and m.get('model_input_scope')=='official_5655' and m.get('model_input_complete') is True,'Acquisition/model scope changed')
    require(m.get('expected_official_train')==4905 and m.get('expected_official_test')==750,'Official counts changed')
    observed=m.get('observed_requests');require(isinstance(observed,int) and 5655<=observed<=32421,'Invalid observed-outcome count')
    require(m.get('pending_requests')==32421-observed and m.get('collection_complete')==(observed==32421),'Scope/completion counts inconsistent')
    if require_full_acquisition:require(observed==32421 and m['collection_complete'],'Final use requires all32421 terminal outcomes')
    if not require_full_acquisition:require(cfg.get('stage')=='evaluate','Partial-acquisition scope is evaluation-only')
    keys=BASE_KEYS+(['full_outcome_audit','outcome_ledger','feature_eligible_ids'] if require_full_acquisition else ['official_scope_certificate','official_membership'])
    files=m.get('files',{});require(set(keys)<=set(files),'Missing feature contract assets')
    paths={}
    for key,item in files.items():
        require(bool(item.get('path')) and bool(item.get('sha256')),'Unpinned asset:'+key)
        path=Path(item['path']);require(path.is_file() and digest(path)==item['sha256'],'Asset missing/changed:'+key);paths[key]=path
    for key,config_key in [('data_disposition','approved_data_disposition_sha256'),('output_disposition','approved_output_disposition_sha256')]:require(cfg.get(config_key)==files[key]['sha256'],'Unreviewed data policy:'+key)
    policy=read_json(paths['output_disposition']);binding=read_json(paths['reviewed_exceptions'])
    require(binding['policy_sha256']==files['output_disposition']['sha256'],'Exception binding policy mismatch')
    rejected=read_json(paths['service_rejections']);excluded=read_json(paths['feature_exclusions']);standardized=read_json(paths['reviewed_standardizations'])
    reviewed,reject_ids,exclude_ids,standard_ids=validate_reviewed_bindings(policy,binding,files,rejected,excluded,standardized)
    _,queue=rows(paths['queue']);require(len(queue)==32421,'Queue count mismatch')
    q={r['request_id']:r['SMILES'] for r in queue};require(len(q)==32421 and len(set(q.values()))==32421,'Duplicate queue identity')
    require(all(hashlib.sha256(s.encode()).hexdigest()==rid for rid,s in q.items()),'Queue request hash mismatch')
    require(binding['queue_sha256']==files['queue']['sha256'],'Reviewed queue changed')
    require(binding['schema_sha256']==files['feature_schema']['sha256'],'Reviewed endpoint schema changed')
    _,mapping=rows(paths['id_map']);official={}
    for r in mapping:
        if r['source'] in ('official-train.csv','official-test.csv'):
            key=(r['source'],r['Molecule_Name']);require(key not in official,'Duplicate official mapping');official[key]=r['request_id']
    required=set(official.values());require(len(official)==len(required)==5655,'Official request identity mismatch')
    for source,key,count in [('official-train.csv','official_train',4905),('official-test.csv','official_test',750)]:
        _,frame=rows(paths[key]);ids=[r['Molecule_Name'] for r in frame]
        require(len(ids)==len(set(ids))==count and set(ids)=={i for s,i in official if s==source},'Official table membership mismatch')
    columns=m.get('feature_columns',[]);require(len(columns)==len(set(columns))==120,'Exactly120 declared model features required')
    rawcols,raw=rows(paths['raw_features']);require(len(raw)==observed and len(rawcols)==122,'Raw outcomes/schema count mismatch')
    rawcols=set(rawcols)-{'raw_smiles','smiles'};schema=read_json(paths['feature_schema'])
    column_map={c:'ADMETLAB::'+'::'.join(schema['web_column_to_endpoint'].get(c,['csv_extra',c])) for c in rawcols}
    require(set(column_map.values())==set(columns),'Unexpected actual endpoint; review rather than silently dropping')
    numcols,numeric=rows(paths['numeric_features']);require(len(numeric)==observed,'Numeric outcome-row count mismatch')
    allowed=set(columns)|{c+SUFFIX for c in columns}|{'request_id','SMILES','service_smiles'}
    require(set(columns)<=set(numcols) and set(numcols)<=allowed,'Unapproved numeric/derived feature column')
    num={r['request_id']:r for r in numeric};require(len(num)==observed,'Duplicate numeric request')
    present=set();observed_reject=set()
    for rawrow in raw:
        rid=hashlib.sha256(rawrow['raw_smiles'].encode()).hexdigest();require(rid not in present and q.get(rid)==rawrow['raw_smiles'],'Raw request duplicate/identity mismatch');present.add(rid)
        require(rid in num,'Missing numeric outcome row');feature=num[rid]
        require(feature['SMILES']==rawrow['raw_smiles'] and feature['service_smiles']==rawrow['smiles'],'Raw/numeric identity mismatch')
        if validate_status_flags(rawrow,feature,column_map,reviewed):observed_reject.add(rid)
    require(set(num)==present,'Numeric rows outside raw outcomes');require(observed_reject==reject_ids,'Approved rejection coverage mismatch')
    require(exclude_ids<=present,'Approved excluded outcome not present')
    require(standard_ids<=present,'Approved standardization outcome not present')
    require(not standard_ids&required,'This approval is external-only; official inputs must remain unchanged')
    require_official_coverage(required,present,reject_ids|exclude_ids)
    for rid in required:require(all(math.isfinite(float(num[rid][c])) for c in columns),'Official model features must all be finite')
    if not require_full_acquisition:
        cert=read_json(paths['official_scope_certificate'])
        require(cert.get('scope')=='official5655_feature_identity_and_finiteness_only','Unapproved early-evaluation scope')
        require(cert.get('snapshot_outcomes')==observed and cert.get('acquisition_goal_scope')==32421 and cert.get('acquisition_goal_complete')==m['collection_complete'],'Scoped certificate count mismatch')
        require(cert.get('official_train_rows')==4905 and cert.get('official_test_rows')==750 and cert.get('all_official_base_features_finite') is True,'Official feature approval missing')
        require(cert.get('official_service_rejections')==cert.get('official_unresolved_service_graphs')==0,'Official exception not allowed')
        require(set(cert['base_feature_columns'])==set(columns),'Scoped feature columns changed')
        for field,key in [('raw_sha256','raw_features'),('features_sha256','numeric_features'),('queue_sha256','queue'),('map_sha256','id_map'),('official_membership_sha256','official_membership')]:require(cert[field]==files[key]['sha256'],'Scoped certificate input mismatch:'+key)
        _,membership=rows(paths['official_membership']);require(len(membership)==5655 and {(r['source'],r['Molecule_Name']):r['request_id'] for r in membership}==official,'Official scope membership mismatch')
        for source,key in [('official-train.csv','official_train'),('official-test.csv','official_test')]:require(cert['official_original_file_bindings'][source]['sha256']==files[key]['sha256'],'Official original file changed')
    else:
        audit=read_json(paths['full_outcome_audit']);require(audit.get('audit_version')=='final-output-v3' and audit.get('outcomes_complete') is True and audit.get('requested_outcomes')==32421,'Full audit not complete')
        require(audit.get('mechanical_checks_passed') is True and audit.get('mechanical_errors')==[],'Full audit has errors')
        require(audit.get('reviewed_standardizations_sha256')==files['reviewed_standardizations']['sha256'] and audit.get('reviewed_standardization_rows')==len(standard_ids) and set(audit.get('reviewed_standardization_request_ids',[]))==standard_ids,'Full audit standardization binding/count mismatch')
        require(audit.get('official_train_eligible')==4905 and audit.get('official_test_eligible')==750,'Full audit official inputs not eligible')
        for field,key in [('raw_sha256','raw_features'),('features_sha256','numeric_features'),('queue_sha256','queue'),('source_map_sha256','id_map'),('reviewed_policy_sha256','output_disposition'),('reviewed_exceptions_binding_sha256','reviewed_exceptions')]:require(audit[field]==files[key]['sha256'],'Full audit input mismatch:'+key)
        _,ledger=rows(paths['outcome_ledger']);require(len(ledger)==32421 and {r['request_id'] for r in ledger}==present,'Full outcome ledger coverage mismatch')
        eligible={r['request_id'] for r in ledger if str(r['chemistry_eligible']).lower()=='true'}
        _,eligible_rows=rows(paths['feature_eligible_ids']);require({r['request_id'] for r in eligible_rows}==eligible and required<=eligible and standard_ids<=eligible and not (reject_ids|exclude_ids)&eligible,'Feature eligibility ledger mismatch')
    return m,paths,sorted(columns)
