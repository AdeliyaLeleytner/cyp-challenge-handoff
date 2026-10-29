"""Finalfit is stricter than early official-only evaluation: full goal and real native companion."""
from pathlib import Path
import json
from .admet_full_contract_v1 import require,digest,ContractError
ROOT=Path(__file__).resolve().parents[1]
NATIVE_EXPERIMENT='8421e31b-790d-4c13-9f29-d3b9bdc1ee59'
NATIVE_OUTPUTS={
'native_official_oof':'results/native_official_training_OOF.csv',
'native_official_oof_provenance':'results/native_official_training_OOF_provenance.json',
'native_blind_raw':'results/cyp-ensemble_activity_submission_native_raw.csv',
'native_blind_placed':'results/cyp-ensemble_activity_submission_native_raw_native_strae.csv',
'native_placement':'results/placement.json',
'native_final_complete':'results/final_complete.json'}
for _m in ('union18','mtaux8','2d6isoform6','2d6single'):
    NATIVE_OUTPUTS[_m+'_oof']='results/'+_m+'/oof.csv'
    NATIVE_OUTPUTS[_m+'_blind_raw']='results/'+_m+'/test_raw.csv'

def read_pinned(path,sha,label):
    require(bool(path) and bool(sha),label+' and SHA256 must be pinned')
    require(Path(path).is_file() and digest(path)==sha,label+' missing or hash mismatch')
    return json.loads(Path(path).read_text())

def check_common_configuration(cfg):
    require(cfg.get('stage')=='finalfit','Only explicitly configured finalfit stage accepted')
    require(cfg.get('submission_lane')=='native_published_placement','Parent locked published-placement serving lane; no raw fallback')
    require(cfg.get('placement_source_sha256')=='7f8834425973369531cb21805fe54c966e72e47a5c764c49395a1d7dc7a9aec6','Published placement source differs from locked recipe')
    mode=cfg.get('final_selection_mode')
    require(mode in (None,'global_three_expert','validated_global_pair'),'Unreviewed final selection mode')
    allowed_blends=['global_three_expert'] if mode=='global_three_expert' else ['global'] if mode=='validated_global_pair' else ['global','per_target']
    require(cfg.get('model_seed')==42 and cfg.get('blend_modes')==allowed_blends,'Evaluated selection setting changed')
    for name,sha in cfg['source_sha256'].items():require(digest(ROOT/name)==sha,'Pinned evaluator source changed: '+name)

def check_configuration(cfg):
    check_common_configuration(cfg)
    frozen=json.loads((ROOT/'full_feature_config.json').read_text())['portfolio']
    if (ROOT/'h6_feature_portfolio.json').is_file():frozen+=json.loads((ROOT/'h6_feature_portfolio.json').read_text())
    known={x['name']:x for x in frozen}
    names=[s.get('name') for s in cfg.get('portfolio',[])]
    require(names and len(names)==len(set(names)),'Nonempty unique eligible portfolio required')
    for spec in cfg['portfolio']:
        require(spec['family'] in ('lightgbm','kernel','chemeleon_ridge'),'Unsupported family; TabPFN requires its separate runtime adapter, never substitute CPU learner')
        require(known.get(spec['name'])==spec,'Recipe/grid differs from pinned evaluated portfolio')

def validate_full_goal(approval,feature_files,final_files):
    require(approval.get('approved_for_finalfit') is True,'Full collection/chemistry finalfit approval missing')
    require(approval.get('terminal_count')==approval.get('audited_requests')==32421 and approval.get('pending_count')==0,'Partial acquisition cannot unlock finalfit')
    require(approval.get('successful_numeric_count',-1)+approval.get('service_failed_count',-1)==32421,'Terminal outcome accounting mismatch')
    require(approval.get('official_eligible_rows')==5655,'All5655 official feature rows must be chemically approved')
    bind=['raw_features','numeric_features','queue','id_map','official_train','official_test','feature_schema','full_outcome_audit','outcome_ledger','feature_eligible_ids','data_disposition','output_disposition','reviewed_exceptions','service_rejections','feature_exclusions']
    for key in bind:require(approval.get('input_sha256',{}).get(key)==feature_files[key]['sha256'],'Full audit not bound to '+key)
    for key in ('folds','strict_pairs'):require(approval.get('input_sha256',{}).get(key)==final_files[key]['sha256'],'Full audit not bound to '+key)

def validate(cfg):
    check_configuration(cfg)
    return validate_artifacts(cfg)

def validate_artifacts(cfg):
    check_common_configuration(cfg)
    # Block on null pins before importing an unfinished/shared adapter or any model.
    read_pinned(cfg.get('snapshot_manifest'),cfg.get('snapshot_manifest_sha256'),'Complete final snapshot manifest')
    try:from .admet_outcome_contract import validate_feature_snapshot
    except ImportError as exc:raise ContractError('Shared outcome contract not yet pinned; finalfit remains blocked') from exc
    manifest,paths,columns=validate_feature_snapshot(cfg,require_full_acquisition=True)
    require(manifest.get('expected_requests')==32421,'Finalfit requires all32421 requested structures')
    if any(spec['family']=='chemeleon_ridge' for spec in cfg['portfolio']):require('chemeleon' in paths,'Frozen CheMeleon checkpoint must be hash-pinned in the feature manifest')
    final=read_pinned(cfg.get('final_manifest'),cfg.get('final_manifest_sha256'),'Finalfit companion manifest')
    require(final.get('schema_version')==1,'Unsupported finalfit contract')
    require(final.get('feature_snapshot_sha256')==cfg['snapshot_manifest_sha256'],'Final contract bound to different snapshot')
    needed=['folds','strict_pairs','full_goal_approval','native_approval','native_run_complete']+list(NATIVE_OUTPUTS)
    files=final.get('files',{});require(set(needed)<=set(files),'Missing finalfit companion assets')
    extra={}
    for key,item in files.items():
        require(item.get('path') and item.get('sha256'),'Unpinned final asset: '+key)
        path=Path(item['path']);require(path.is_file() and digest(path)==item['sha256'],'Missing/changed final asset: '+key);extra[key]=path
    approval=json.loads(extra['full_goal_approval'].read_text())
    validate_full_goal(approval,manifest['files'],files)
    native=json.loads(extra['native_approval'].read_text());complete=json.loads(extra['native_run_complete'].read_text())
    require(native.get('approved') is True and native.get('experiment_id')==NATIVE_EXPERIMENT,'Actual corrected full-native companion not approved')
    require(bool(native.get('source_commit')) and bool(native.get('orx_run_id')),'Missing native run/source provenance')
    require(native.get('strict_inner_purges_approved') is True and native.get('qualified_legacy_source_policy_approved') is True,'Native legacy-source/inner-purge review missing')
    require(native.get('official_train_sha256')==manifest['files']['official_train']['sha256'] and native.get('official_test_sha256')==manifest['files']['official_test']['sha256'],'Native official inputs mismatch')
    require(native.get('run_complete_sha256')==files['native_run_complete']['sha256'],'Native approval not bound to actual complete receipt')
    require(complete.get('status')=='complete' and complete.get('retrained_folds')==10 and complete.get('reused_folds')==10,'Native companion incomplete')
    for key,rel in NATIVE_OUTPUTS.items():
        require(complete.get('files',{}).get(rel)==files[key]['sha256'],'Asset not part of native completed run: '+key)
        require(native.get('prediction_sha256',{}).get(key)==files[key]['sha256'],'Native approval not bound to '+key)
    fold_manifest=json.loads(extra['folds'].read_text())
    for key in ('official_train','id_map'):require(fold_manifest['input_sha256'][key]==manifest['files'][key]['sha256'],'Feature fold inputs mismatch: '+key)
    require(fold_manifest['input_sha256']['strict_pairs']==files['strict_pairs']['sha256'],'Feature fold strict-group source changed')
    return manifest,{**paths,**extra},columns,final
