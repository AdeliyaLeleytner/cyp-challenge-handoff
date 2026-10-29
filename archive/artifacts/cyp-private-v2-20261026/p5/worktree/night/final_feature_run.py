"""Gated final official-only CPU fit/export; never publishes or submits."""
from pathlib import Path
import argparse,hashlib,importlib.metadata,importlib.util,json,subprocess,sys,time
from .admet_full_contract_v1 import require,digest,ContractError
from .final_feature_contract import validate,ROOT

def load_inputs(paths,columns):
    import numpy as np
    import pandas as pd
    from rdkit import Chem,RDLogger
    from rdkit.Chem import Descriptors,rdFingerprintGenerator
    from .admet_full_models import feature_groups
    from .final_feature_engine import TARGETS
    from .final_feature_folds import strict_groups,validate_folds
    RDLogger.DisableLog('rdApp.*')
    train=pd.read_csv(paths['official_train']);blind=pd.read_csv(paths['official_test'])
    require(len(train)==4905 and len(blind)==750,'Official sizes changed')
    require(set(blind.columns)=={'Molecule_Name','SMILES'},'Blind table must not contain targets/experimental values')
    require(train.Molecule_Name.is_unique and blind.Molecule_Name.is_unique and not set(train.Molecule_Name)&set(blind.Molecule_Name),'Official ID collision')
    mapping=pd.read_csv(paths['id_map'],dtype=str);frames=[]
    for data,source in ((train,'official-train.csv'),(blind,'official-test.csv')):
        matched=mapping[mapping.source==source].set_index('Molecule_Name');require(matched.index.is_unique,'Duplicate official mapping')
        matched=matched.loc[data.Molecule_Name];data=data.copy();data['request_id']=matched.request_id.to_numpy();data['request_smiles']=matched.request_smiles.to_numpy();frames.append(data)
    train,blind=frames;combined=pd.concat([train[['Molecule_Name','SMILES','request_id','request_smiles']],blind[['Molecule_Name','SMILES','request_id','request_smiles']]],ignore_index=True)
    require(combined.request_id.is_unique,'Official request collision')
    numeric=pd.read_csv(paths['numeric_features']).set_index('request_id');require(numeric.index.is_unique,'Duplicate feature rows')
    admet=numeric.loc[combined.request_id,columns].to_numpy(float);require(admet.shape==(5655,120) and np.isfinite(admet).all(),'Official features must be complete and finite')
    mols=[Chem.MolFromSmiles(s) for s in combined.SMILES];require(all(m is not None for m in mols),'Invalid official input')
    require(all(Chem.MolToSmiles(m)==s for m,s in zip(mols,combined.request_smiles)),'Official original/request graph mismatch')
    generator=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048)
    fp=np.asarray([generator.GetFingerprintAsNumPy(m) for m in mols],dtype=np.float64)
    rd=np.asarray([[fn(m) for _,fn in Descriptors._descList] for m in mols],float);rd[~np.isfinite(rd)]=np.nan
    X={'admet':admet,'admet_groups':feature_groups(columns),'fp':fp,'rd':rd,'structure':np.column_stack([fp,rd])}
    y=train[TARGETS].to_numpy(float);lo=train[[t+'_conf_low' for t in TARGETS]].to_numpy(float);hi=train[[t+'_conf_high' for t in TARGETS]].to_numpy(float)
    observed=np.isfinite(y);require(np.isfinite(lo[observed]).all() and np.isfinite(hi[observed]).all() and np.all(lo[observed]<=hi[observed]),'Observed-label confidence bounds invalid')
    folds=validate_folds(json.loads(paths['folds'].read_text()),train,train.request_id.tolist(),strict_groups(paths['strict_pairs']))
    return train,blind,combined,X,y,lo,hi,folds

def cached_predict(out,input_identity,source_sha,predict):
    import numpy as np
    from .final_feature_engine import save
    cache=Path(out)/'prediction-cache';cache.mkdir(exist_ok=True)
    def wrapped(spec,params,train,query,target,X,seed,threads):
        identity={'inputs':input_identity,'source':source_sha,'spec':spec,'params':params,'train':np.asarray(train).tolist(),'query':np.asarray(query).tolist(),'target_sha':hashlib.sha256(np.ascontiguousarray(target).tobytes()).hexdigest(),'seed':seed,'threads':threads}
        key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();array=cache/(key+'.npy');receipt=cache/(key+'.json')
        if receipt.exists() and array.exists():
            stored=json.loads(receipt.read_text());require(stored['identity']==identity and stored['sha256']==digest(array),'Prediction cache identity mismatch')
            result=np.load(array)
        else:
            started=time.time();result=np.asarray(predict(spec,params,train,query,target,X,seed,threads),float)
            require(result.shape==(len(query),) and np.isfinite(result).all(),'Learner returned invalid predictions')
            tmp=array.with_suffix('.tmp.npy');np.save(tmp,result);tmp.replace(array)
            save(receipt,{'identity':identity,'sha256':digest(array),'seconds':time.time()-started})
            print(json.dumps({'event':'final_feature_fit_complete','recipe':spec['name'],'fit_rows':len(train),'query_rows':len(query),'seconds':time.time()-started}),flush=True)
        require(result.shape==(len(query),) and np.isfinite(result).all(),'Cached predictions invalid');return result
    return wrapped

def execute(cfg,manifest,paths,columns,final_manifest):
    import numpy as np
    import pandas as pd
    from .final_feature_engine import TARGETS,save,native_vectors,select_training_oof,final_predict,export_submission
    from .admet_full_models import predict
    from .admet_full_math import place,placement_constants
    out=Path(cfg['output_dir']);require(not (out/'complete.json').exists(),'Completed output is immutable; use a new child')
    if out.exists() and any(out.iterdir()):require((out/'run-identity.json').exists(),'Unrecognized existing output directory')
    out.mkdir(parents=True,exist_ok=True)
    runtime={n:importlib.metadata.version(n) for n in ('numpy','scipy','pandas','scikit-learn','lightgbm','rdkit','torch','chemprop')}
    identity={'config':cfg,'feature_manifest_sha256':cfg['snapshot_manifest_sha256'],'final_manifest_sha256':cfg['final_manifest_sha256'],'goal_terminal_count':32421,'official_training_rows':4905,'blind_rows':750,'runtime':runtime}
    old=out/'run-identity.json'
    if old.exists():require(json.loads(old.read_text())==identity,'Existing output belongs to another run identity')
    save(old,identity)
    print(json.dumps({'event':'finalfit_effective_configuration','identity':identity}),flush=True)
    train,blind,combined,X,y,lo,hi,folds=load_inputs(paths,columns)
    # Validate real companion before any new model inference/fitting.
    native_oof,native_raw,native_placed=native_vectors(paths,train,blind)
    constants=placement_constants(ROOT/'vendor/briford_native/cyp_recalibrate.py')
    placed,meta=place(y,native_oof,native_raw,TARGETS,constants)
    require(placed is not None and np.allclose(placed,native_placed,atol=1e-6,rtol=1e-6),'Final native placement parity failed')
    save(out/'native-parity.json',{'max_abs_difference':float(np.max(np.abs(placed-native_placed))),'placement':meta,'native_component_folds_are_not_shared':True})
    from .external_tabpfn_contract import data_binding,load_oof,load_selection_bundle,load_query,create_query_request
    binding=data_binding(paths,columns);model_contract=cfg['expected_tabpfn_model_contract']
    if cfg['bridge_phase']=='finalize_external':
        selection,selected_oof,request,request_sha=load_selection_bundle(cfg['selection_bundle_manifest'],cfg['selection_bundle_manifest_sha256'],binding,model_contract,train,native_oof)
        tab_query,provenance=load_query(cfg['external_tabpfn_query_manifest'],cfg['external_tabpfn_query_manifest_sha256'],request,request_sha,binding,model_contract,blind)
        chosen=selection['chosen'];raw=tab_query if chosen['mode']=='standalone' else native_raw+(tab_query-native_raw)*np.asarray(chosen['weight'])
        save(out/'full-data-selection.json',selection);require(digest(out/'full-data-selection.json')==request['selection_sha256'],'Selection serialization changed')
        save(out/'external-query-provenance.json',provenance)
        finish_export(cfg,paths,out,blind,y,selected_oof,raw,selection,constants,identity,runtime)
        return
    external=None
    if cfg.get('use_external_tabpfn',True):
        external=load_oof(cfg['external_tabpfn_oof_manifest'],cfg['external_tabpfn_oof_manifest_sha256'],binding,model_contract,train)
        (out/'external_tabpfn_oof.csv').write_bytes(Path(external['prediction_source']).read_bytes())
    if any(spec['view'] in ('adme','adme_admet') for spec in cfg['portfolio']):
        from .final_adme_features import build_views as build_adme_views
        decision=json.loads(Path(cfg['adme_final_recipe_decision']).read_text())
        required={spec['name'] for spec in cfg['portfolio'] if spec['view'] in ('adme','adme_admet')}
        require(decision.get('decided_before_finalfit') is True and set(decision.get('eligible_adme_recipes',[]))==required,'H6 final recipe declaration changed')
        feature_cfg={**cfg,'expected_tabpfn_model_contract':{'embedding_assets_sha256':cfg['adme_feature_asset_sha256']}}
        views,proof=build_adme_views(train,blind,X['admet'],feature_cfg,'query',cfg['adme_final_recipe_decision_sha256'],digest(paths['official_test']),'final_recipe');X.update(views);save(out/'adme-feature-provenance.json',proof)
        X['final_feature_order']=[f'ADME600::coordinate_{i:03d}' for i in range(600)]+columns
    combined[['Molecule_Name','SMILES','request_id']].to_csv(out/'feature-input-identities.csv',index=False)
    save(out/'feature-columns.json',columns)
    if any(s['family']=='chemeleon_ridge' for s in cfg['portfolio']):
        subprocess.run([sys.executable,'-u','-m','night.admet500_embed',str(out/'feature-input-identities.csv'),str(paths['chemeleon']),str(out/'frozen-chemeleon.npy')],check=True)
        X['chemeleon']=np.load(out/'frozen-chemeleon.npy');require(X['chemeleon'].shape==(5655,2048) and np.isfinite(X['chemeleon']).all(),'Frozen embedding alignment/shape mismatch')
    call=cached_predict(out,[cfg['snapshot_manifest_sha256'],cfg['final_manifest_sha256']],cfg['source_sha256'],predict)
    if cfg.get('final_selection_mode')=='global_three_expert':
        require(external is None,'H7 cannot add another expert/candidate family')
        from .final_feature_engine import select_three_expert_oof,final_predict_three
        selection,selected_oof=select_three_expert_oof(cfg,train,y,lo,hi,X,folds,native_oof,call,out,constants)
        raw=final_predict_three(cfg,selection,train,y,X,np.arange(4905,5655),native_raw,call,out)
        finish_export(cfg,paths,out,blind,y,selected_oof,raw,selection,constants,identity,runtime)
        return
    selection,selected_oof=select_training_oof(cfg,train,y,lo,hi,X,folds,native_oof,call,out,constants,external_candidates=[external] if external else [])
    if selection['chosen'].get('recipe') and selection['recipes'][selection['chosen']['recipe']].get('external_candidate'):
        save(out/'producer-config.json',cfg)
        request=create_query_request(out,selection,binding,model_contract)
        save(out/'complete.json',{'status':'awaiting_tabpfn_query','producer_experiment_id':cfg['producer_experiment_id'],'selected_option':selection['chosen']['name'],'query_request_sha256':digest(out/'tabpfn-query-request.json'),'training_OOF_metrics':selection['chosen']['training_OOF']['macro'],'blind_predictions_generated':False,'no_submission':True})
        print(json.dumps({'event':'selected_tabpfn_requires_query_stage','request':str(out/'tabpfn-query-request.json'),'endpoint_calls_requested':4,'no_export':True}),flush=True)
        return
    raw=final_predict(cfg,selection,train,y,X,np.arange(4905,5655),native_raw,call,out)
    finish_export(cfg,paths,out,blind,y,selected_oof,raw,selection,constants,identity,runtime)

def finish_export(cfg,paths,out,blind,y,selected_oof,raw,selection,constants,identity,runtime):
    import numpy as np
    from .final_feature_engine import TARGETS,save,export_submission
    from .admet_full_math import place
    model_manifest=None
    if cfg.get('save_final_models'):
        import pandas as pd
        from .final_feature_engine import align_prediction
        models={};head_predictions=[]
        for target in TARGETS:
            directory=out/'final-models'/target;receipt=json.loads((directory/'receipt.json').read_text())
            require(receipt.get('reload_exact') is True and receipt['query_rows']==750 and receipt['feature_count']==720,'Final saved head verification incomplete')
            require(receipt['model_sha256']==digest(directory/'head.joblib') and receipt['predictions_sha256']==digest(directory/'query-predictions.npy'),'Final saved model/predictions changed')
            require(receipt['identity']['context']['selection_sha256']==digest(out/'full-data-selection.json'),'Saved head bound to another selection')
            head_predictions.append(np.load(directory/'query-predictions.npy',allow_pickle=False));models[target]={'model_sha256':receipt['model_sha256'],'receipt_sha256':digest(directory/'receipt.json'),'reload_max_abs_error':receipt['reload_max_abs_error'],'training_rows':receipt['training_rows']}
        native=align_prediction(pd.read_csv(paths['native_blind_raw']),blind);weights=np.asarray(selection['chosen']['weight'])
        restored=(1-weights)*native+weights*np.column_stack(head_predictions)
        require(np.array_equal(restored,raw),'Saved-head reconstruction differs from final raw blend')
        model_manifest={'models':models,'feature_order_sha256':digest(out/'final-models'/TARGETS[0]/'feature-order.json'),'native_blend_weights':dict(zip(TARGETS,weights.tolist())),'selection_sha256':digest(out/'full-data-selection.json'),'raw_blend_reconstruction_exact':True,'model_refits_for_reload_verification':0}
        save(out/'final-models/manifest.json',model_manifest)
    raw_receipt=export_submission(out/'final-test-raw.csv',blind,raw,require_spread=cfg['submission_lane']=='raw')
    placed,placement_meta=place(y,selected_oof,raw,TARGETS,constants)
    # Numerical helper is unchanged; this wrapper records actual final serving use.
    placement_meta={**placement_meta,'diagnostic_only':False,'usage':'locked_final_serving_policy','uses_published_leaderboard_derived_constants':True,'independently_validated_local_calibration':False,'numerical_helper_unchanged':True}
    save(out/'final-placement.json',placement_meta)
    placed_receipt=None
    if placed is not None:placed_receipt=export_submission(out/'final-test-placed.csv',blind,placed,require_spread=cfg['submission_lane']=='native_published_placement')
    if cfg['submission_lane']=='native_published_placement':require(placed_receipt is not None,'Locked placed lane is undefined; no silent raw fallback')
    chosen=placed_receipt if cfg['submission_lane']=='native_published_placement' else raw_receipt
    validator_spec=importlib.util.spec_from_file_location('pinned_activity_validator',ROOT/'vendor/final_activity_validation.py');validator=importlib.util.module_from_spec(validator_spec);validator_spec.loader.exec_module(validator)
    ok,errors=validator.validate_activity_submission(Path(chosen['path']),expected_ids=set(blind.Molecule_Name));require(ok,'Official validator rejected export: '+str(errors))
    save(out/'submission-validation.json',{'valid':True,'lane':cfg['submission_lane'],'chosen':chosen,'raw':raw_receipt,'placed':placed_receipt,'official_validator_sha256':digest(ROOT/'vendor/final_activity_validation.py'),'no_submission':True})
    save(out/'complete.json',{'status':'ready_for_report_and_submission_review','selected_option':selection['chosen']['name'],'submission_lane':cfg['submission_lane'],'submission_csv':chosen['path'],'submission_sha256':chosen['sha256'],'selection_sha256':digest(out/'full-data-selection.json'),'input_identity':identity,'packages':runtime,'saved_final_models':model_manifest,'no_submission':True,'no_publication':True,'no_blind_labels_loaded':True})
    print(json.dumps({'event':'final_feature_export_ready','path':chosen['path'],'sha256':chosen['sha256'],'selected_option':selection['chosen']['name'],'training_OOF_metrics':selection['chosen']['training_OOF']['macro'],'metrics_are_selection_estimates':True,'no_submission':True}),flush=True)

def validate_bridge_config(cfg):
    from .external_tabpfn_contract import fixed_model_contract
    import uuid
    require(bool(cfg.get('producer_experiment_id')),'ORX producer experiment ID must be set for this child')
    uuid.UUID(cfg['producer_experiment_id'])
    require(cfg.get('bridge_phase') in ('select','finalize_external'),'Unknown external bridge phase')
    requested=cfg['expected_tabpfn_model_contract'];view=requested['spec']['view']
    predictor=ROOT/('vendor/tabpfn_final_predictor.py' if view=='admet' else 'vendor/tabpfn_h5_predictor.py')
    expected=fixed_model_contract(digest(predictor),digest(ROOT/'tabpfn35-LICENSE'),view,requested.get('embedding_assets_sha256'))
    require(cfg.get('expected_tabpfn_model_contract')==expected,'Expected TabPFN model contract changed')
    require(cfg.get('use_external_tabpfn',True) or cfg['bridge_phase']=='select','External export phase requires explicit TabPFN support')
    if cfg.get('final_selection_mode')=='validated_per_target_pair':
        require(cfg.get('use_external_tabpfn') is False and len(cfg['portfolio'])==1 and cfg['portfolio'][0]['name']=='lightgbm__adme720','Final H6 recipe cannot switch family')
        path=cfg.get('validated_recipe_decision');sha=cfg.get('validated_recipe_decision_sha256')
        require(path and sha and digest(path)==sha,'Parent final recipe decision must be pinned')
        d=json.loads(Path(path).read_text());require(d.get('selected_recipe')=='H6 lightgbm__adme720 with native_blend_per_target' and d.get('blend_modes')==['per_target'] and d.get('grid')==cfg['portfolio'][0]['grid'] and d.get('model_seed')==42 and d.get('serving_lane')==cfg['submission_lane'],'Final H6 recipe decision changed')
    if cfg.get('final_selection_mode')=='validated_global_pair':
        require(cfg.get('use_external_tabpfn') is False and len(cfg['portfolio'])==1,'Validated pair requires one explicit existing recipe')
        path=cfg.get('validated_recipe_decision');sha=cfg.get('validated_recipe_decision_sha256')
        require(path and sha and digest(path)==sha,'Validated final recipe decision must be pinned')
        decision=json.loads(Path(path).read_text());require(decision.get('declared_before_finalfit') is True and decision.get('model_name')==cfg['portfolio'][0]['name'] and decision.get('mode')=='native_blend_global','Final recipe decision does not match fixed pair')
    if cfg.get('final_selection_mode')=='global_three_expert':
        require({k:importlib.metadata.version(k) for k in ('numpy','scipy')}==cfg.get('required_simplex_runtime'),'H7 final solver runtime differs from verified evaluation')
        require(cfg.get('use_external_tabpfn') is False and {s['name'] for s in cfg['portfolio']}=={'lightgbm__admet','lightgbm__adme720'},'H7 permits only its fixed three experts')
    keys=(['external_tabpfn_oof_manifest'] if cfg.get('use_external_tabpfn',True) else []) if cfg['bridge_phase']=='select' else ['selection_bundle_manifest','external_tabpfn_query_manifest']
    if any(spec['view'] in ('adme','adme_admet') for spec in cfg['portfolio']):
        require(cfg.get('adme_feature_asset_sha256')==json.loads((ROOT/'h6_embedding_asset_sha256.json').read_text()),'H6 embedding provenance differs from evaluated assets')
        keys+=['adme_final_recipe_decision','adme_blind_embedding_manifest']
    for key in keys:
        require(bool(cfg.get(key)) and bool(cfg.get(key+'_sha256')),'External phase artifact must be pinned: '+key)
        require(digest(cfg[key])==cfg[key+'_sha256'],'External phase artifact changed: '+key)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preflight',action='store_true');args=parser.parse_args()
    cfg=json.loads((ROOT/'final_feature_config.json').read_text())
    try:
        manifest,paths,columns,final_manifest=validate(cfg)
        validate_bridge_config(cfg)
        if args.preflight:
            print(json.dumps({'event':'finalfit_input_contract_ready','fits_started':0,'terminal_outcomes':32421}));return
        require(cfg.get('training_enabled') is True,'Preparation-only node: commit training_enabled=true after input/budget review')
    except (ContractError,OSError) as exc:
        print(json.dumps({'event':'finalfit_blocked','error':str(exc),'fits_started':0}));raise SystemExit(2)
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=cfg['threads']):execute(cfg,manifest,paths,columns,final_manifest)
if __name__=='__main__':main()
