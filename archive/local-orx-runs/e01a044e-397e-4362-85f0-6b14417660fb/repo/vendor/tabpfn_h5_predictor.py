"""Fixed cached-weight ADMET120 TabPFN arm. No network or implicit installation."""
from pathlib import Path
import gc,hashlib,importlib.metadata,json,platform,time
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from .admet_full_contract import digest,require

ROOT=Path(__file__).resolve().parents[1]
WEIGHT_SHA='ece4d67eadfea42eb0e610df5189bea60cb7f31073d81e9c7a019b76eacf0be3'

def feature_groups(columns):
    require(len(columns)==120 and len(set(columns))==120,'Exactly120 distinct ADMET columns required')
    require(all(c.startswith('ADMETLAB::') for c in columns),'Experimental columns cannot enter X')
    cyp=np.array([c.startswith('ADMETLAB::metabolism::CYP') for c in columns])
    require(int(cyp.sum())==13,'Unexpected web_default120 feature regime')
    return {'cyp_only':np.flatnonzero(cyp),'non_cyp':np.flatnonzero(~cyp)}

def validate_native_approval(cfg,manifest):
    p=cfg.get('corrected_native_approval');sha=cfg.get('corrected_native_approval_sha256')
    require(bool(p) and bool(sha),'Corrected native approval and SHA256 must be pinned')
    require(digest(p)==sha,'Corrected native approval hash mismatch')
    approved=json.loads(Path(p).read_text())
    require(approved.get('experiment_id')==cfg['required_native_experiment'],'Wrong corrected native experiment')
    require(approved.get('approved') is True,'Corrected native vectors not approved')
    require(approved.get('cohorts_sha256')==manifest['files']['cohorts']['sha256'],'Corrected native cohort definition mismatch')
    keys=[cohort+'_'+suffix for cohort in ('own750','briford529') for suffix in ('native_raw','native_placed','union18_oof','mtaux8_oof','2d6isoform6_oof','2d6single_oof')]
    require(all(k in manifest['files'] for k in keys),'Missing corrected native prediction asset')
    require(len(keys)==12,'Expected two corrected native raw/placed and eight component OOF assets')
    for k in keys:
        require(approved.get('prediction_sha256',{}).get(k)==manifest['files'][k]['sha256'],'Corrected native approval not bound to '+k)

def validate_assets(cfg,manifest):
    validate_native_approval(cfg,manifest)
    asset=cfg['model_asset'];require(asset['sha256']==WEIGHT_SHA,'Historical checkpoint changed')
    require(digest(asset['path'])==WEIGHT_SHA,'Cached TabPFN checkpoint missing or hash mismatch')
    require(digest(ROOT/asset['license_file'])==asset['license_sha256'],'Checkpoint license changed')
    expected=[{'name':'tabpfn35__'+name,'family':'tabpfn35','view':view,'grid':[{'n_estimators':8}]} for name,view in [('adme600','adme'),('adme600_admet120','adme_admet')]]
    require(cfg['portfolio']==expected,'H5 permits only the two prespecified matched views')
    require(cfg['model_seed']==42,'Historical seed42 required')
    from .h5_features import validate_embedding_assets
    validate_embedding_assets(cfg)

def validate_runtime(cfg):
    actual={k:(platform.python_version() if k=='python' else importlib.metadata.version(k)) for k in cfg['runtime']}
    for k,v in cfg['runtime'].items():require(actual[k]==v,f'Isolated runtime mismatch: {k}: {actual[k]} != {v}')
    import torch
    require(torch.cuda.is_available(),'This arm requires explicitly allocated CUDA; no silent CPU/native-environment fallback')
    require(torch.version.cuda=='12.8','Historical CUDA12.8 runtime required')
    return {'packages':actual,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0)}

def preprocess(train,query):
    """Fit on this endpoint's observed-label training rows only; no PCA at120dims."""
    imputer=SimpleImputer(strategy='median',keep_empty_features=True)
    a=imputer.fit_transform(train);b=imputer.transform(query)
    scale=StandardScaler();a=scale.fit_transform(a);b=scale.transform(b)
    return a.astype(np.float32),b.astype(np.float32),imputer,scale

def predict(spec,params,train,query,target,X,seed,threads):
    require(spec['family']=='tabpfn35' and spec['view'] in ('adme','adme_admet') and params=={'n_estimators':8},'Unsupported H5 arm')
    raw=X[spec['view']];expected_dim={'adme':600,'adme_admet':720}[spec['view']]
    require(raw.ndim==2 and raw.shape[1]==expected_dim and np.isfinite(raw).all(),'Invalid matched feature view')
    require(not set(train)&set(query),'Fit/query overlap')
    cfg=X['tabpfn_config'];out=Path(cfg['output_dir'])/'fit-cache';out.mkdir(parents=True,exist_ok=True)
    identity={'train_indices':np.asarray(train).tolist(),'query_indices':np.asarray(query).tolist(),'seed':seed,'params':params,'view':spec['view'],'feature_count':expected_dim,'snapshot_sha256':cfg['snapshot_manifest_sha256'],'model_sha256':WEIGHT_SHA,'adapter_sha256':digest(__file__)}
    for k,a in [('y',target),('train_x',raw[train]),('query_x',raw[query])]:identity[k+'_sha256']=hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();saved=out/(key+'.npz');receipt=out/(key+'.json')
    if saved.exists() and receipt.exists():
        old=json.loads(receipt.read_text());require(old['identity']==identity and digest(saved)==old['prediction_sha256'],'Fit-cache identity/hash mismatch')
        result=np.load(saved)['prediction'];require(result.shape==(len(query),) and np.isfinite(result).all(),'Invalid cached predictions');return result
    require(time.time()<cfg['lease_deadline_unix']-cfg['recovery_margin_seconds'],'Lease recovery margin reached; stop without starting another model call')
    a,b,imputer,scale=preprocess(raw[train],raw[query]);start=time.time()
    # Explicit existing path plus global HF_HUB_OFFLINE prevent implicit gated downloads.
    model_path=Path(cfg['model_asset']['path']);require(model_path.is_file(),'Pinned cached checkpoint disappeared')
    from tabpfn import TabPFNRegressor
    import torch
    model=TabPFNRegressor(model_path=str(model_path),n_estimators=8,random_state=seed,device='cuda')
    try:
        model.fit(a,target);result=np.asarray(model.predict(b),float)
        require(result.shape==(len(query),) and np.isfinite(result).all(),'TabPFN returned invalid predictions')
    finally:
        del model;gc.collect();torch.cuda.empty_cache()
    temp=saved.with_suffix('.tmp.npz');np.savez_compressed(temp,prediction=result,imputer_statistics=imputer.statistics_,scaler_mean=scale.mean_,scaler_scale=scale.scale_);temp.replace(saved)
    info={'identity':identity,'prediction_sha256':digest(saved),'seconds':time.time()-start,'training_rows':len(train),'query_rows':len(query),'feature_count':expected_dim,'view':spec['view'],'preprocessing':'median+standardscale train-only; no PCA','real_model_fit':True}
    temp=receipt.with_suffix('.tmp.json');temp.write_text(json.dumps(info,indent=2)+'\n');temp.replace(receipt)
    print(json.dumps({'event':'tabpfn_endpoint_complete','key':key,'view':spec['view'],'feature_count':expected_dim,'seconds':info['seconds'],'training_rows':len(train),'query_rows':len(query)}),flush=True)
    return result
