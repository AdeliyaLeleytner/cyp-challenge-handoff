"""Official-only evaluation scope plus the fixed corrected legacy-expert certificate."""
from .admet_full_contract_v1 import ContractError,digest,read_json,require
from .admet_outcome_contract import validate_feature_snapshot

def validate_reference(cfg,m,paths):
    files=m['files'];keys=['cohorts','reference_certificate','reference_stage_manifest','reference_purge_manifest']
    for c in ('own750','briford529'):keys += [c+'_native_raw',c+'_native_placed',c+'_reference_truth',c+'_reference_query',c+'_reference_exclusion']+[c+'_'+x+'_oof' for x in ('union18','mtaux8','2d6isoform6','2d6single')]
    require(set(keys)<=set(paths),'Missing corrected outer reference assets')
    cert=read_json(paths['reference_certificate'])
    require(cfg.get('reference_usage')=='conditional_fixed_legacy_expert','Frozen reference source policy not explicit')
    require(cert.get('experiment_id')==cfg.get('reference_experiment_id')=='31f8a64a-174d-4f92-95e8-2ada73c2176d' and cert.get('status')=='done_verified','Wrong/unverified corrected reference')
    require(cert.get('strict_outer_and_inner_purges_verified') is True,'Strict purge certificate missing')
    require(cert['stage_manifest_sha256']==files['reference_stage_manifest']['sha256'] and cert['purge_manifest_sha256']==files['reference_purge_manifest']['sha256'],'Corrected reference stage/purge changed')
    scope=read_json(paths['official_scope_certificate'])
    for c in ('own750','briford529'):
        item=cert['cohorts'][c]
        for key,lane in [(c+'_native_raw','raw'),(c+'_native_placed','native_published_placement')]:require(item['predictions'][lane]['sha256']==files[key]['sha256'],'Reference prediction changed:'+key)
        for member in ('union18','mtaux8','2d6isoform6','2d6single'):require(item['component_oof'][member]['sha256']==files[c+'_'+member+'_oof']['sha256'],'Reference OOF changed')
        require(item['truth_sha256']==files[c+'_reference_truth']['sha256'] and item['query_sha256']==files[c+'_reference_query']['sha256'],'Reference truth/query changed')
        required_hashes={files[c+'_reference_'+kind]['sha256'] for kind in ('truth','query','exclusion')}
        require(required_hashes<=set(scope['cohort_bindings'][c].values()),'Scoped official certificate/reference binding mismatch')

def validate(cfg):
    require(cfg.get('stage')=='evaluate','Only evaluation stage is implemented; no implicit refit/submission')
    result=validate_feature_snapshot(cfg,require_full_acquisition=False)
    validate_reference(cfg,*result[:2]);return result
