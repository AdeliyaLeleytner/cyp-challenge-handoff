"""Serialization and exact reload checks; learner/preprocessing math stays in its original helper."""
from pathlib import Path
import hashlib,json
import numpy as np
from .admet_full_contract_v1 import require,digest

def identity(spec,params,train,query,target,features,seed,threads,artifact):
    return {'spec':spec,'params':params,'seed':seed,'threads':threads,'target':artifact['target'],'feature_order':artifact['feature_order'],'context':artifact['context'],'training_indices':np.asarray(train).tolist(),'query_indices':np.asarray(query).tolist(),'training_features_sha256':hashlib.sha256(np.ascontiguousarray(features[train]).tobytes()).hexdigest(),'query_features_sha256':hashlib.sha256(np.ascontiguousarray(features[query]).tobytes()).hexdigest(),'target_sha256':hashlib.sha256(np.ascontiguousarray(target).tobytes()).hexdigest()}

def reuse(artifact,expected,query_features):
    import joblib
    out=Path(artifact['directory']);model_path=out/'head.joblib';receipt=out/'receipt.json'
    if not model_path.exists() and not receipt.exists():return None
    require(model_path.exists() and receipt.exists(),'Partial model artifact; recover rather than silently refit')
    old=json.loads(receipt.read_text());require(old['identity']==expected and old['model_sha256']==digest(model_path),'Saved model context/hash changed')
    bundle=joblib.load(model_path);require(bundle['feature_order']==expected['feature_order'],'Saved feature order changed')
    x=bundle['preprocessing']['imputer'].transform(query_features)
    if bundle['preprocessing'].get('scaler') is not None:x=bundle['preprocessing']['scaler'].transform(x);x=np.clip(x,-20,20)
    prediction=np.asarray(bundle['model'].predict(x),float);require(np.isfinite(prediction).all(),'Reloaded head produced nonfinite predictions')
    require(digest(out/'query-predictions.npy')==old['predictions_sha256'],'Saved query-prediction artifact changed')
    original=np.load(out/'query-predictions.npy',allow_pickle=False);require(np.array_equal(prediction,original),'Reloaded model does not exactly reproduce saved query predictions')
    return prediction

def persist(artifact,expected,model,preprocessing,query_features,prediction):
    import joblib,importlib.metadata
    out=Path(artifact['directory']);out.mkdir(parents=True,exist_ok=True)
    require(len(artifact['feature_order'])==query_features.shape[1],'Saved feature order does not cover model inputs')
    bundle={'model':model,'preprocessing':preprocessing,'feature_order':artifact['feature_order'],'identity':expected}
    temporary=out/'head.tmp.joblib';joblib.dump(bundle,temporary,compress=3);temporary.replace(out/'head.joblib')
    reloaded=joblib.load(out/'head.joblib');x=reloaded['preprocessing']['imputer'].transform(query_features)
    if reloaded['preprocessing'].get('scaler') is not None:x=reloaded['preprocessing']['scaler'].transform(x);x=np.clip(x,-20,20)
    check=np.asarray(reloaded['model'].predict(x),float)
    require(np.array_equal(check,prediction),'Serialization reload changed query vectors; no extra fit or approximation allowed')
    np.save(out/'query-predictions.npy',prediction)
    (out/'feature-order.json').write_text(json.dumps(artifact['feature_order'],indent=2)+'\n')
    if hasattr(model,'booster_'):model.booster_.save_model(str(out/'booster.txt'))
    receipt={'identity':expected,'model_sha256':digest(out/'head.joblib'),'predictions_sha256':digest(out/'query-predictions.npy'),'reload_exact':True,'reload_max_abs_error':float(np.max(np.abs(check-prediction))),'training_rows':len(expected['training_indices']),'query_rows':len(prediction),'feature_count':len(artifact['feature_order']),'packages':{n:importlib.metadata.version(n) for n in ('numpy','scikit-learn','lightgbm','joblib')},'additional_refits_for_verification':0}
    temp=out/'receipt.tmp.json';temp.write_text(json.dumps(receipt,indent=2)+'\n');temp.replace(out/'receipt.json')
    return prediction
