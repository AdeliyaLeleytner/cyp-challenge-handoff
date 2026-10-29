"""Optional interval-endpoint forest candidate; independent of the R0 reference.

For l<=u, |p-l|+|p-u| = (u-l)+2*distance(p,[l,u]). Training an
absolute-error tree on two IDENTICAL feature rows labelled l and u therefore
minimizes the official interval loss up to a constant. bootstrap=False keeps each
endpoint pair together. Forest averaging is an ensemble of these tree predictors,
not a claim to solve a globally optimal conditional interval problem.

Inputs are frozen raw base-model TRAIN OOF predictions. Gate/test predictions are
only transformed after all forest fits and development selection. Chemical feature
columns are optional and must not contain assay measurements. No network or GPU.
"""
from collections.abc import Mapping
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from .evaluation import score
from .reference import CANONICAL

CANDIDATE_NAME = 'interval_endpoint_forest'
DEFAULT_CONFIG = {'n_estimators':128,'min_samples_leaf':20,'max_features':1.0,
                  'max_depth':None,'seed':42,'n_jobs':1,
                  'blend_weights':[0.,.25,.5,.75,1.]}

def _id_list(df,name):
    if 'Molecule_Name' not in df or df.Molecule_Name.isna().any() or df.Molecule_Name.duplicated().any():
        raise ValueError(f'{name}: unique non-null Molecule_Name required')
    return df.Molecule_Name.astype(str).tolist()

def _aligned(df,ids,cols,name):
    supplied = _id_list(df,name)
    if set(supplied)!=set(ids): raise ValueError(f'{name}: ID sets differ')
    d=df.assign(Molecule_Name=supplied).set_index('Molecule_Name').loc[ids,cols]
    x=d.to_numpy(np.float32)
    if not np.isfinite(x).all(): raise ValueError(f'{name}: nonfinite features or predictions')
    return x

def _fit_forest(x,low,high,cfg,seed):
    from sklearn.ensemble import ExtraTreesRegressor
    if len(x)<2: raise ValueError('Too few observed fit intervals')
    model=ExtraTreesRegressor(n_estimators=int(cfg['n_estimators']),criterion='absolute_error',
        min_samples_leaf=int(cfg['min_samples_leaf'])*2,max_features=cfg['max_features'],
        max_depth=cfg['max_depth'],bootstrap=False,n_jobs=int(cfg['n_jobs']),random_state=seed)
    # min_samples_leaf is expressed in MOLECULES in config; tree rows are doubled.
    model.fit(np.repeat(x,2,axis=0),np.column_stack([low,high]).reshape(-1))
    return model

def _diagnose_intervals(y,low,high):
    width=high-low
    corr=float(np.corrcoef(y,width)[0,1]) if np.std(y)>0 and np.std(width)>0 else None
    return {'n':len(y),'width_quantiles':dict(zip(['min','q10','median','q90','q99','max'],np.quantile(width,[0,.1,.5,.9,.99,1]).tolist())),
            'midpoint_minus_point_quantiles':np.quantile((low+high)/2-y,[.1,.5,.9]).tolist(),
            'point_width_correlation':corr}

def run_candidate(oof_truth,oof_predictions,query_predictions,development_folds,*,
                  allowed_fit_ids,forbidden_fit_ids=None,training_features=None,
                  query_features=None,config=None,output_dir=None):
    """Return (query_predictions, metadata) after train-only crossfit selection.

    development_folds: mapping ID -> fixed development fold. Base predictions must
    be genuine raw OOF values, not a calibration fit to those same OOF labels.
    Optional feature DataFrames contain Molecule_Name plus identical numeric
    chemistry-feature columns. Their row order may differ; alignment is by ID.

    Blend weights are selected once, globally across targets, by development OOF
    ST-RAE. The full forest is then fit on all allowed development rows. This is
    internal tuning; only the untouched outer holdout estimates final performance.
    """
    cfg=dict(DEFAULT_CONFIG);cfg.update(config or {})
    ids=_id_list(oof_truth,'OOF truth');qids=_id_list(query_predictions,'query predictions')
    if set(ids)&set(qids): raise ValueError('Development OOF and gate/test query IDs overlap')
    if not set(ids)<=set(map(str,allowed_fit_ids)): raise ValueError('Fit IDs are outside frozen allowed training cohort')
    if set(ids)&set(map(str,forbidden_fit_ids if forbidden_fit_ids is not None else [])): raise ValueError('Forbidden gate/test IDs present in fit')
    targets=[t for t in CANONICAL if t in oof_predictions]
    if not targets: raise ValueError('No recognized OOF prediction targets')
    base=_aligned(oof_predictions,ids,targets,'OOF predictions')
    query_base=_aligned(query_predictions,qids,targets,'query predictions')
    x,qx=base.copy(),query_base.copy()
    feature_names=['base_oof_'+t for t in targets]
    if (training_features is None)!=(query_features is None): raise ValueError('Provide both training and query features, or neither')
    if training_features is not None:
        cols=[c for c in training_features if c!='Molecule_Name']
        if not cols or set(cols)!=set(query_features)-{'Molecule_Name'}: raise ValueError('Chemical feature columns differ')
        # A naming guard supplements the caller's source-provenance responsibility.
        forbidden=[c for c in cols if any(s in c.lower() for s in ['pic50','conf_low','conf_high','ci_lower','ci_upper','log2fc','emax','is_tdi'])]
        if forbidden: raise ValueError(f'Assay-like input features are forbidden: {forbidden}')
        x=np.column_stack([x,_aligned(training_features,ids,cols,'training chemistry features')])
        qx=np.column_stack([qx,_aligned(query_features,qids,cols,'query chemistry features')])
        feature_names+=cols
    if not isinstance(development_folds,Mapping): raise TypeError('development_folds must map ID to fold')
    folds_by_id={str(k):v for k,v in development_folds.items()}
    if not set(ids)<=set(folds_by_id): raise ValueError('Development folds omit OOF rows')
    folds=np.asarray([folds_by_id[i] for i in ids]);unique=pd.unique(folds)
    if len(unique)<2: raise ValueError('At least two development folds required')
    weights=np.asarray(cfg['blend_weights'],float)
    if not len(weights) or not np.isfinite(weights).all() or np.any((weights<0)|(weights>1)):
        raise ValueError('Blend weights must be finite in [0,1]')
    crossfit=np.full_like(base,np.nan,dtype=float)
    full_predictions=np.empty_like(query_base,dtype=float)
    interval_metadata={};fold_metadata=[];models={}
    for j,target in enumerate(targets):
        y=oof_truth[target].to_numpy(float)
        low=oof_truth[target+'_conf_low'].to_numpy(float)
        high=oof_truth[target+'_conf_high'].to_numpy(float)
        observed=np.isfinite(y)
        if np.any(observed&(~np.isfinite(low)|~np.isfinite(high)|(low>high))): raise ValueError(f'Invalid observed confidence bounds: {target}')
        interval_metadata[target]=_diagnose_intervals(y[observed],low[observed],high[observed])
        for k,fold in enumerate(unique):
            fit=observed&(folds!=fold);val=folds==fold
            forest=_fit_forest(x[fit],low[fit],high[fit],cfg,int(cfg['seed'])+1000*j+k)
            crossfit[val,j]=forest.predict(x[val])
            fold_metadata.append({'target':target,'fold':str(fold),'n_fit_molecules':int(fit.sum()),'n_predict_molecules':int(val.sum())})
        forest=_fit_forest(x[observed],low[observed],high[observed],cfg,int(cfg['seed'])+1000*j+len(unique))
        full_predictions[:,j]=forest.predict(qx)
        models[target]=forest
    if not np.isfinite(crossfit).all() or not np.isfinite(full_predictions).all(): raise RuntimeError('Nonfinite interval-forest predictions')
    def frame(row_ids,values):
        result=pd.DataFrame(values,columns=targets);result.insert(0,'Molecule_Name',row_ids);return result
    development_scores=[]
    for weight in weights:
        pred=frame(ids,(1-weight)*base+weight*crossfit)
        scored=score(oof_truth,pred,targets=targets)
        if not scored['defined']: raise ValueError('Undefined development selection score')
        development_scores.append({'forest_weight':float(weight),'score':scored})
    # Deterministic tie handling favors the smaller learned correction.
    selected=min(development_scores,key=lambda r:(r['score']['macro_ST_RAE'],r['forest_weight']))
    weight=selected['forest_weight']
    result=frame(qids,(1-weight)*query_base+weight*full_predictions)
    metadata={'candidate':CANDIDATE_NAME,'config':cfg,'targets':targets,
        'selected_forest_weight':weight,'development_scores':development_scores,
        'selection_scope':'Fixed development OOF folds; no gate/test labels or query moments.',
        'development_score_caveat':'Internal method selection on cross-fitted meta predictions, not an unbiased final performance estimate.',
        'objective_identity':'|p-l|+|p-u|=(u-l)+2*distance(p,[l,u])',
        'paired_endpoints':'Identical feature rows, bootstrap=False; each tree leaf sees both interval endpoints for each retained molecule.',
        'model_note':'Mean of interval-L1-trained randomized trees; no claim of exact global conditional-loss optimum.',
        'uncertainty_note':'Experimental confidence bounds are supervision for point predictions; this does not produce calibrated predictive uncertainty.',
        'n_fit_molecules':len(ids),'n_query_molecules':len(qids),'n_features':len(feature_names),
        'feature_names':feature_names,'interval_diagnostics_training_only':interval_metadata,
        'folds':fold_metadata,'query_labels_used':False,'board_constants_used':False,
        'fit_ids_sha256':hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest(),
        'query_ids_sha256':hashlib.sha256(('\n'.join(qids)+'\n').encode()).hexdigest(),
        'source_provenance_requirement':'Caller must preserve base OOF generation and chemical-feature source manifests.'}
    if output_dir is not None:
        out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
        result.to_csv(out/'predictions.csv',index=False)
        frame(ids,crossfit).to_csv(out/'development_forest_crossfit.csv',index=False)
        frame(qids,full_predictions).to_csv(out/'query_forest_unblended.csv',index=False)
        (out/'metadata.json').write_text(json.dumps(metadata,indent=2))
        import joblib
        joblib.dump({'models':models,'feature_names':feature_names,'targets':targets,'forest_weight':weight},out/'forest.joblib',compress=3)
    return result,metadata
