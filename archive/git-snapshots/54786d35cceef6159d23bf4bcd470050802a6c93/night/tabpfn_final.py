"""Full official TabPFN OOF or selected query refit; never submits or chooses a model."""
from pathlib import Path
import argparse,json,sys,time
from .admet_full_contract_v1 import require,digest,ContractError
from .final_feature_contract import ROOT,validate_artifacts
from .external_tabpfn_contract import SPEC,SPECS,TARGETS,fixed_model_contract,data_binding,write_json,load_selection_bundle

def validate_stage(cfg):
    import uuid
    require(bool(cfg.get('producer_experiment_id')),'ORX producer experiment ID must be set for this stage child')
    uuid.UUID(cfg['producer_experiment_id'])
    require(cfg.get('pipeline_phase') in ('oof','query'),'Unknown final TabPFN stage')
    requested=cfg['expected_tabpfn_model_contract'];view=requested['spec']['view']
    require(view in SPECS and cfg.get('portfolio')==[SPECS[view]] and cfg.get('model_seed')==42,'Only the explicitly selected authorized fixed TabPFN view is allowed')
    predictor=ROOT/('night/tabpfn_admet.py' if view=='admet' else 'night/tabpfn_h5_predictor.py')
    expected=fixed_model_contract(digest(predictor),digest(ROOT/'tabpfn35-LICENSE'),view,requested.get('embedding_assets_sha256'))
    require(cfg.get('expected_tabpfn_model_contract')==expected,'Final TabPFN differs from evaluated model contract')
    require(cfg.get('runtime')==expected['runtime'],'Historical TabPFN runtime changed')
    result=validate_artifacts(cfg)
    if view!='admet':
        from .final_adme_features import validate_training_assets
        validate_training_assets(cfg,expected)
        deadline=cfg.get('lease_deadline_unix');margin=cfg.get('recovery_margin_seconds')
        require(isinstance(deadline,(int,float)) and isinstance(margin,(int,float)) and margin>0 and time.time()<deadline-margin,'H5 final stage requires its own live authorized lease deadline/recovery margin')
    asset=cfg['model_asset'];require(asset['sha256']==expected['checkpoint_sha256'],'Checkpoint pin changed')
    require(Path(asset['path']).is_file() and digest(asset['path'])==asset['sha256'],'Existing cached TabPFN checkpoint required; no download fallback')
    require(asset['license_sha256']==expected['license_sha256'],'Checkpoint license changed')
    if cfg['pipeline_phase']=='query':
        path=cfg.get('selection_bundle_manifest');sha=cfg.get('selection_bundle_manifest_sha256')
        require(path and sha and digest(path)==sha,'Query phase requires hash-pinned selection bundle')
        bundle=json.loads(Path(path).read_text());item=bundle['files']['selection']
        require(digest(item['path'])==item['sha256'],'Selected-query manifest changed')
        from .external_tabpfn_contract import check_selected_tabpfn
        check_selected_tabpfn(json.loads(Path(item['path']).read_text()))
    return result

def load_inputs(paths,columns):
    import numpy as np
    import pandas as pd
    from rdkit import Chem
    from .final_feature_folds import strict_groups,validate_folds
    train=pd.read_csv(paths['official_train']);blind=pd.read_csv(paths['official_test'])
    require(len(train)==4905 and len(blind)==750 and set(blind.columns)=={'Molecule_Name','SMILES'},'Wrong official train/test contract')
    require(train.Molecule_Name.is_unique and blind.Molecule_Name.is_unique and not set(train.Molecule_Name)&set(blind.Molecule_Name),'Official ID collision')
    mapping=pd.read_csv(paths['id_map'],dtype=str);frames=[]
    for data,source in ((train,'official-train.csv'),(blind,'official-test.csv')):
        m=mapping[mapping.source==source].set_index('Molecule_Name');require(m.index.is_unique,'Duplicate official mapping');m=m.loc[data.Molecule_Name]
        data=data.copy();data['request_id']=m.request_id.to_numpy();data['request_smiles']=m.request_smiles.to_numpy();frames.append(data)
    train,blind=frames;combined=pd.concat([f[['Molecule_Name','SMILES','request_id','request_smiles']] for f in frames],ignore_index=True)
    require(combined.request_id.is_unique,'Official request collision')
    for smi,requested in zip(combined.SMILES,combined.request_smiles):
        mol=Chem.MolFromSmiles(smi);require(mol is not None and Chem.MolToSmiles(mol)==requested,'Official/request molecular graph mismatch')
    numeric=pd.read_csv(paths['numeric_features']).set_index('request_id');require(numeric.index.is_unique,'Duplicate ADMET feature rows')
    values=numeric.loc[combined.request_id,columns].to_numpy(float);require(values.shape==(5655,120) and np.isfinite(values).all(),'Official ADMET120 must be finite and complete')
    y=train[TARGETS].to_numpy(float);lo=train[[t+'_conf_low' for t in TARGETS]].to_numpy(float);hi=train[[t+'_conf_high' for t in TARGETS]].to_numpy(float)
    observed=np.isfinite(y);require(np.isfinite(lo[observed]).all() and np.isfinite(hi[observed]).all() and np.all(lo[observed]<=hi[observed]),'Invalid official confidence bounds')
    folds=validate_folds(json.loads(paths['folds'].read_text()),train,train.request_id.tolist(),strict_groups(paths['strict_pairs']))
    return train,blind,{'admet':values},y,lo,hi,folds

def oof_contexts(y,folds):
    import numpy as np
    n=len(y);require(len(folds)==5,'Exactlyfive OOF folds required');require(sorted(np.concatenate([v for _,v in folds]).tolist())==list(range(n)),'Full official OOF coverage mismatch')
    for fold,(train,val) in enumerate(folds):
        require(not set(train)&set(val) and set(train)<=set(range(n)) and set(val)<=set(range(n)),'Training OOF boundary violation')
        for j in range(4):
            fit=train[np.isfinite(y[train,j])];require(len(fit)>=2,'Insufficient target labels');yield fold,j,fit,val

def query_contexts(y,query_indices,selection):
    import numpy as np
    from .external_tabpfn_contract import check_selected_tabpfn
    check_selected_tabpfn(selection);require(list(query_indices)==list(range(len(y),len(y)+750)),'Wrong blind query index boundary/order')
    for j in range(4):
        fit=np.flatnonzero(np.isfinite(y[:,j]));require(len(fit)>=2,'Insufficient final target labels');yield j,fit,query_indices

def native_oof(paths,train):
    import numpy as np
    import pandas as pd
    f=pd.read_csv(paths['native_official_oof']);require(f.Molecule_Name.is_unique and set(f.Molecule_Name)==set(train.Molecule_Name),'Native OOF IDs differ')
    f=f.set_index('Molecule_Name').loc[train.Molecule_Name];require(f.SMILES.tolist()==train.SMILES.tolist(),'Native OOF graph identity differs')
    values=f[TARGETS].to_numpy(float);require(np.isfinite(values).all(),'Native OOF incomplete');return values

def emit_predictions(path,frame,pred):
    import numpy as np
    require(pred.shape==(len(frame),4) and np.isfinite(pred).all(),'Incomplete TabPFN predictions')
    f=frame[['Molecule_Name','SMILES','request_id']].copy()
    for j,t in enumerate(TARGETS):f[t]=pred[:,j]
    f.to_csv(path,index=False,float_format='%.17g')

def execute(cfg,manifest,paths,columns,final):
    import numpy as np
    view=cfg['expected_tabpfn_model_contract']['spec']['view'];spec=cfg['expected_tabpfn_model_contract']['spec']
    if view=='admet':from .tabpfn_admet import predict,validate_runtime
    else:from .tabpfn_h5_predictor import predict,validate_runtime
    from .tabpfn_metrics import scores
    out=Path(cfg['output_dir']);require(not (out/'complete.json').exists(),'Completed stage immutable; create child/output')
    if out.exists() and any(out.iterdir()):require((out/'run-identity.json').exists(),'Unknown output directory')
    out.mkdir(parents=True,exist_ok=True);binding=data_binding(paths,columns)
    train,blind,X,y,lo,hi,folds=load_inputs(paths,columns)
    selection=request=request_sha=None
    # Selection proof precedes runtime/model access, so a losing TabPFN cannot query-refit.
    if cfg['pipeline_phase']=='query':
        selection,selected_oof,request,request_sha=load_selection_bundle(cfg['selection_bundle_manifest'],cfg['selection_bundle_manifest_sha256'],binding,cfg['expected_tabpfn_model_contract'],train,native_oof(paths,train))
    extra_features={'kind':'ADMET120_only'}
    if view!='admet':
        from .final_adme_features import build_views
        views,extra_features=build_views(train,blind,X['admet'],cfg,cfg['pipeline_phase'],request_sha,digest(paths['official_test']));X.update(views)
    runtime=validate_runtime(cfg)
    identity={'config':cfg,'data_binding':binding,'runtime':runtime}
    saved=out/'run-identity.json'
    if saved.exists():require(json.loads(saved.read_text())==identity,'Stage context/runtime changed')
    write_json(saved,identity);X['tabpfn_config']=cfg
    started=time.time();calls=0;phase=cfg['pipeline_phase']
    if phase=='oof':
        predictions=np.full_like(y,np.nan)
        for fold,j,fit,val in oof_contexts(y,folds):
            predictions[val,j]=predict(spec,{'n_estimators':8},fit,val,y[fit,j],X,42,cfg['threads']);calls+=1
        frame=train;metrics=scores(y,predictions,lo,hi);write_json(out/'training-OOF-metrics.json',metrics)
        print(json.dumps({'event':'tabpfn_final_OOF_metrics','macro':metrics['macro'],'per_cyp':metrics['per_cyp'],'not_independent_validation':True}),flush=True)
    else:
        predictions=np.empty((750,4));frame=blind
        for j,fit,query in query_contexts(y,np.arange(4905,5655),selection):
            predictions[:,j]=predict(spec,{'n_estimators':8},fit,query,y[fit,j],X,42,cfg['threads']);calls+=1
    require(calls==(20 if phase=='oof' else 4),'Unexpected number of endpoint contexts')
    predfile=out/('tabpfn-'+phase+'-predictions.csv');emit_predictions(predfile,frame,predictions)
    receipt={'status':'complete','phase':phase,'producer_experiment_id':cfg['producer_experiment_id'],'endpoint_calls':calls,'predictions_sha256':digest(predfile),'data_binding':binding,'model_contract':cfg['expected_tabpfn_model_contract'],'extra_feature_provenance':extra_features,'folds_sha256':digest(paths['folds']),'runtime':runtime,'blind_predictions_generated':phase=='query','seconds':time.time()-started,'no_submission':True,'no_new_hyperparameters':True}
    if phase=='query':receipt.update(query_request_sha256=request_sha,selection_sha256=request['selection_sha256'])
    write_json(out/'complete.json',receipt);print(json.dumps({'event':'tabpfn_final_stage_complete','phase':phase,'endpoint_calls':calls,'output':str(out),'seconds':receipt['seconds'],'no_submission':True}),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');args=p.parse_args();cfg=json.loads((ROOT/'tabpfn_final_config.json').read_text())
    try:
        result=validate_stage(cfg)
        if args.preflight:print(json.dumps({'event':'tabpfn_final_preflight_ready','phase':cfg['pipeline_phase'],'fits_started':0}));return
        require(cfg.get('training_enabled') is True,'Preparation-only final TabPFN node; commit enabling after full input/budget review')
    except (ContractError,OSError) as exc:
        print(json.dumps({'event':'tabpfn_final_blocked','error':str(exc),'fits_started':0}));raise SystemExit(2)
    execute(cfg,*result)
if __name__=='__main__':main()
