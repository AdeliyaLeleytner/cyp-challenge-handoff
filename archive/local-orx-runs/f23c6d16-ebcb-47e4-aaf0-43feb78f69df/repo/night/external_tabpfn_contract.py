"""Content-bound exchange between full CPU selection and isolated TabPFN stages."""
from pathlib import Path
import hashlib,json
from .admet_full_contract_v1 import require,digest
NAME='tabpfn35__admet120'
SPEC={'name':NAME,'family':'tabpfn35','view':'admet','grid':[{'n_estimators':8}]}
SPECS={'admet':SPEC,'adme':{'name':'tabpfn35__adme600','family':'tabpfn35','view':'adme','grid':[{'n_estimators':8}]},'adme_admet':{'name':'tabpfn35__adme600_admet120','family':'tabpfn35','view':'adme_admet','grid':[{'n_estimators':8}]}}
TARGETS=[f'{c}_pIC50_direct_inhibition' for c in ('CYP1A2','CYP2C9','CYP2D6','CYP3A4')]
WEIGHT='ece4d67eadfea42eb0e610df5189bea60cb7f31073d81e9c7a019b76eacf0be3'
RUNTIME={'python':'3.11.13','torch':'2.8.0+cu128','tabpfn':'9.2.0','numpy':'2.2.6','scikit-learn':'1.7.2'}

def object_sha(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write_json(path,obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def data_binding(paths,columns):
    # Content, not host paths: identical staged inputs can live on Mac/Linux.
    ignored={'chemeleon'}
    return {'files':{k:digest(v) for k,v in sorted(paths.items()) if k not in ignored},'feature_columns':columns,'rows':{'train':4905,'test':750,'terminal_outcomes':32421}}

def fixed_model_contract(predictor_sha,license_sha,view='admet',embedding_assets_sha256=None):
    require(view in SPECS,'Only the authorized ADMET120/ADME600/ADME720 views are supported')
    model={'spec':SPECS[view],'seed':42,'checkpoint_sha256':WEIGHT,'license_sha256':license_sha,'predictor_source_sha256':predictor_sha,'runtime':RUNTIME,'preprocessing':'train-only median+StandardScaler; noPCA','features':'exact120web_default','targets':TARGETS}
    if view!='admet':
        require(isinstance(embedding_assets_sha256,dict) and set(embedding_assets_sha256)=={'adme_matrix','adme_source_rows','adme_checkpoint','adme_preparation_record','adme_producer_source','adme_provenance','adme_runtime_lock'},'H5 requires exact encoder/cache/order/protocol/runtime provenance')
        expected={'adme_matrix':'e0216aeaad3f8b9a34ea124b0eb90bd36ae671ae79b1d30268feccf5f8731378','adme_source_rows':'b7391fb28af2972a7f5070f253ee914dc4baef010177adaa87489673e23350fe','adme_checkpoint':'b8137a0d202669baa9747f21eac4ef78b000afe68a3f100d25c849c41ad8a3d5','adme_producer_source':'588e331659515e8ba0d5797f6172b3339946da960bb10ec30217214424857104','adme_runtime_lock':'252b616dd6ae1e90a35717e88fecef10f552af9cd96497ae1e43bfd41723f2e8'}
        require(all(embedding_assets_sha256.get(k)==v for k,v in expected.items()),'H5 cached encoder/feature provenance changed')
        require(all(isinstance(v,str) and len(v)==64 for v in embedding_assets_sha256.values()),'Unpinned H5 asset')
        model.update(features='frozenADME600' if view=='adme' else 'frozenADME600_then_sortedADMET120',feature_count=600 if view=='adme' else 720,embedding_assets_sha256=embedding_assets_sha256)
    else:require(embedding_assets_sha256 in (None,{}),'ADMET-only view cannot silently add encoder features')
    return model

def require_fixed_model(actual,expected):
    require(actual==expected,'TabPFN model/runtime/checkpoint/preprocessing provenance mismatch')
    require(actual['spec'] in SPECS.values() and actual['seed']==42 and actual['checkpoint_sha256']==WEIGHT and actual['runtime']==RUNTIME,'Unsupported TabPFN setting')

def load_pinned_manifest(path,sha):
    require(bool(path) and bool(sha),'External artifact manifest and SHA256 must be pinned')
    require(Path(path).is_file() and digest(path)==sha,'External manifest missing or changed')
    m=json.loads(Path(path).read_text());require(m.get('schema_version')==1,'Unsupported external artifact schema')
    require(bool(m.get('producer_commit')) and bool(m.get('producer_orx_run_id')),'External result must identify its actual ORX producer run/commit')
    files={}
    for k,v in m['files'].items():
        p=Path(v['path']);require(p.is_file() and digest(p)==v['sha256'],'External file missing or changed: '+k);files[k]=p
    require({'receipt','predictions'}<=set(files),'Incomplete external result files')
    receipt=json.loads(files['receipt'].read_text())
    require(receipt.get('status')=='complete','External producer did not complete')
    require(receipt.get('predictions_sha256')==m['files']['predictions']['sha256'],'Producer receipt does not bind prediction file')
    require(receipt.get('producer_experiment_id')==m.get('producer_experiment_id'),'External experiment identity mismatch')
    return m,files,receipt

def align_exact_predictions(frame,official,expected_rows):
    import numpy as np
    require(len(official)==expected_rows and len(frame)==expected_rows,'External prediction row count mismatch')
    require(list(frame.columns)==['Molecule_Name','SMILES','request_id']+TARGETS,'External prediction schema changed')
    require(frame.Molecule_Name.is_unique and set(frame.Molecule_Name)==set(official.Molecule_Name),'External prediction IDs mismatch')
    aligned=frame.set_index('Molecule_Name').loc[official.Molecule_Name]
    require(aligned.SMILES.tolist()==official.SMILES.tolist() and aligned.request_id.tolist()==official.request_id.tolist(),'External graph/request identity mismatch')
    values=aligned[TARGETS].to_numpy(float);require(np.isfinite(values).all(),'External predictions must be finite');return values

def load_oof(path,sha,expected_binding,expected_model,official):
    import pandas as pd
    m,files,r=load_pinned_manifest(path,sha)
    require(r.get('phase')=='oof' and r.get('endpoint_calls')==20,'Not a completed20-call training OOF stage')
    require(r.get('data_binding')==expected_binding,'External OOF data/fold/native-companion binding mismatch')
    require_fixed_model(r['model_contract'],expected_model)
    require(r.get('runtime',{}).get('packages')==expected_model['runtime'],'Producer runtime does not match fixed TabPFN environment')
    require(r.get('folds_sha256')==expected_binding['files']['folds'],'External OOF folds differ from full feature folds')
    require(r.get('blind_predictions_generated') is False,'OOF stage must not perform blind query inference')
    return {'spec':expected_model['spec'],'params':{'n_estimators':8},'oof':align_exact_predictions(pd.read_csv(files['predictions']),official,4905),'prediction_source':str(files['predictions']),'provenance':{'manifest_sha256':sha,'receipt_sha256':m['files']['receipt']['sha256'],'predictions_sha256':m['files']['predictions']['sha256'],'producer_commit':m['producer_commit'],'producer_orx_run_id':m['producer_orx_run_id'],'model_contract':r['model_contract'],'data_binding_sha256':object_sha(expected_binding)}}

def check_selected_tabpfn(selection):
    chosen=selection['chosen'];require(chosen.get('recipe') in {s['name'] for s in SPECS.values()},'TabPFN query refits are forbidden unless selected')
    require(chosen.get('mode') in ('standalone','global','per_target'),'Unsupported TabPFN selection mode')
    recipe=selection['recipes'][chosen['recipe']];require(recipe['spec'] in SPECS.values() and recipe['spec']['name']==chosen['recipe'] and recipe['selected']['params']=={'n_estimators':8},'Selected TabPFN recipe changed')
    require(recipe.get('external_candidate') is True,'Selection does not originate from pinned external OOF')
    require(selection['submission_lane']=='native_published_placement','Query request serving lane changed')
    return chosen

def create_query_request(out,selection,binding,model):
    out=Path(out);chosen=check_selected_tabpfn(selection)
    require(selection['recipes'][chosen['recipe']]['spec']==model['spec'],'Selected feature view differs from query model')
    lock=json.loads((out/'selection-lock.json').read_text());require(lock['selection_sha256']==digest(out/'full-data-selection.json'),'CPU selection file differs from lock')
    request={'schema_version':1,'status':'awaiting_separate_runtime_query','selection_sha256':lock['selection_sha256'],'selection_lock_sha256':digest(out/'selection-lock.json'),'selected_oof_sha256':digest(out/'selected__training_OOF.csv'),'data_binding':binding,'model_contract':model,'selected_option':chosen['name'],'expected_query_rows':750,'expected_endpoint_calls':4,'oof_provenance':selection['recipes'][selection['chosen']['recipe']]['external_provenance'],'submission_lane':'native_published_placement'}
    write_json(out/'tabpfn-query-request.json',request);return request

def validate_query_request(request,selection,selection_sha,lock,lock_sha,binding,model):
    check_selected_tabpfn(selection)
    require(selection['recipes'][selection['chosen']['recipe']]['spec']==model['spec'],'Selected feature view differs from query model')
    require(request.get('submission_lane')==selection['submission_lane'],'Query request serving lane changed')
    require(request.get('status')=='awaiting_separate_runtime_query' and request.get('expected_endpoint_calls')==4 and request.get('expected_query_rows')==750,'Invalid selected query stage request')
    require(request['selection_sha256']==selection_sha==lock['selection_sha256'],'Query request selection hash mismatch')
    require(request['selection_lock_sha256']==lock_sha,'Query request lock changed')
    require(request['data_binding']==binding,'Query request uses different data/folds')
    require_fixed_model(request['model_contract'],model)
    require(request['selected_option']==selection['chosen']['name'],'Selected option changed')
    require(request['oof_provenance']==selection['recipes'][selection['chosen']['recipe']]['external_provenance'],'Selected OOF provenance changed')

def load_query(path,sha,request,request_sha,binding,model,blind):
    import pandas as pd
    m,files,r=load_pinned_manifest(path,sha)
    require(r.get('phase')=='query' and r.get('endpoint_calls')==4,'Not a completed4-call selected query stage')
    require(r.get('query_request_sha256')==request_sha and r.get('selection_sha256')==request['selection_sha256'],'Query result is not from this locked selection')
    require(r['data_binding']==binding,'Query result data/fold/native-companion binding mismatch')
    require_fixed_model(r['model_contract'],model)
    require(r.get('runtime',{}).get('packages')==model['runtime'],'Query producer runtime mismatch')
    if model['spec']['view']!='admet':
        proof=r.get('extra_feature_provenance',{});pins=model['embedding_assets_sha256']
        require(proof.get('kind')=='verified_ADME600_query' and proof.get('query_request_sha256')==request_sha,'Missing selected-view blind embedding proof')
        require(proof.get('encoder_checkpoint_sha256')==pins['adme_checkpoint'] and proof.get('training_matrix_sha256')==pins['adme_matrix'] and proof.get('encoder_producer_source_sha256')==pins['adme_producer_source'],'Query embeddings differ from selected H5 encoder')
    return align_exact_predictions(pd.read_csv(files['predictions']),blind,750),{'manifest_sha256':sha,'receipt_sha256':m['files']['receipt']['sha256'],'predictions_sha256':m['files']['predictions']['sha256'],'producer_orx_run_id':m['producer_orx_run_id'],'producer_commit':m['producer_commit']}

def load_selection_bundle(path,sha,binding,model,official,native_oof):
    import numpy as np
    import pandas as pd
    require(path and sha and digest(path)==sha,'Selection bundle manifest missing or changed')
    m=json.loads(Path(path).read_text());require(m.get('schema_version')==1 and m.get('kind')=='selection','Invalid selection bundle')
    require(m.get('producer_commit') and m.get('producer_orx_run_id'),'Selection bundle needs actual ORX producer provenance')
    required={'selection','selection_lock','selected_oof','query_request','producer_config','external_oof'};require(set(m['files'])==required,'Selection bundle files mismatch')
    paths={}
    for k,v in m['files'].items():
        p=Path(v['path']);require(p.is_file() and digest(p)==v['sha256'],'Selection bundle file changed: '+k);paths[k]=p
    selection=json.loads(paths['selection'].read_text());lock=json.loads(paths['selection_lock'].read_text());request=json.loads(paths['query_request'].read_text());original_cfg=json.loads(paths['producer_config'].read_text())
    require(hashlib.sha256(json.dumps(original_cfg,sort_keys=True).encode()).hexdigest()==selection['configuration_sha256'],'Selection configuration not the original locked config')
    require(original_cfg['submission_lane']=='native_published_placement','Original serving lane changed')
    validate_query_request(request,selection,digest(paths['selection']),lock,digest(paths['selection_lock']),binding,model)
    require(request['selected_oof_sha256']==lock['selected_oof_sha256']==digest(paths['selected_oof']),'Selected OOF hash mismatch')
    require(digest(paths['external_oof'])==request['oof_provenance']['predictions_sha256'],'TabPFN OOF differs from selected producer artifact')
    tab_oof=align_exact_predictions(pd.read_csv(paths['external_oof']),official,4905)
    selected_oof=align_exact_predictions(pd.read_csv(paths['selected_oof']),official,4905)
    chosen=selection['chosen'];weight=np.asarray(chosen['weight'])
    require(weight.shape in ((),(4,)) and np.isfinite(weight).all() and ((weight>=0)&(weight<=1)).all(),'Invalid convex blend coefficient')
    reconstructed=tab_oof if chosen['mode']=='standalone' else native_oof+(tab_oof-native_oof)*weight
    require(np.allclose(reconstructed,selected_oof,atol=1e-12,rtol=1e-12),'Selected OOF does not match locked native/TabPFN blend')
    return selection,selected_oof,request,digest(paths['query_request'])
