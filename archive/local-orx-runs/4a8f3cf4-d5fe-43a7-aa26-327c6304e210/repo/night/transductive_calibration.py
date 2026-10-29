"""P0: structure-only covariate-shift weights for train-OOF interval calibration.

A balanced domain classifier distinguishes source training chemistry from query
chemistry. Source probabilities are predicted out of fold. Odds are an approximate
importance ratio because class weights impose equal domain priors; multiplying by
source/query sample counts again would be incorrect. Query activity and intervals
are never accessed. Only query feature geometry is used transductively.

The grid is fixed before evaluation. Development folds act as pseudoquery domains
for selection; final query geometry enters only after the grid choice is frozen.
"""
from collections.abc import Mapping
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from .evaluation import score
from .reference import CANONICAL

CANDIDATE_NAME='transductive_weighted_oof_interval_affine'
DEFAULT_CONFIG={'caps':[5.,20.],'strengths':[0.,.5,1.],
                'n_estimators':128,'min_samples_leaf':10,'max_depth':8,
                'max_features':'sqrt','n_jobs':1,'seed':42}

def _ids(df,name):
    if 'Molecule_Name' not in df or df.Molecule_Name.isna().any() or df.Molecule_Name.duplicated().any():
        raise ValueError(f'{name} requires unique non-null Molecule_Name')
    return df.Molecule_Name.astype(str).tolist()

def _aligned(df,ids,cols,name):
    actual=_ids(df,name)
    if set(actual)!=set(ids): raise ValueError(f'{name}: mismatched ID set')
    x=df.assign(Molecule_Name=actual).set_index('Molecule_Name').loc[ids,cols].to_numpy(float)
    if not np.isfinite(x).all(): raise ValueError(f'{name}: nonfinite numeric values')
    return x

def _quantiles(x):
    return dict(zip(['min','q10','median','q90','max'],np.quantile(x,[0,.1,.5,.9,1]).tolist()))

def _domain_crossfit(source_features,query_features,source_folds,cfg,seed):
    """Each source probability comes from trees that excluded its source fold."""
    from sklearn.ensemble import ExtraTreesClassifier
    unique=pd.unique(source_folds)
    if len(unique)<2: raise ValueError('At least two source folds required for domain crossfit')
    if not len(query_features): raise ValueError('Domain query must not be empty')
    probabilities=np.full(len(source_features),np.nan)
    diagnostics=[];models=[]
    for k,fold in enumerate(unique):
        held=source_folds==fold;fit=~held
        if not fit.any() or not held.any(): raise ValueError('Empty source domain fit/prediction fold')
        x=np.vstack([source_features[fit],query_features])
        domain=np.r_[np.zeros(int(fit.sum()),int),np.ones(len(query_features),int)]
        model=ExtraTreesClassifier(n_estimators=int(cfg['n_estimators']),
            min_samples_leaf=int(cfg['min_samples_leaf']),max_depth=cfg['max_depth'],
            max_features=cfg['max_features'],class_weight='balanced',bootstrap=False,
            random_state=seed+k,n_jobs=int(cfg['n_jobs']))
        model.fit(x,domain)
        query_class=int(np.flatnonzero(model.classes_==1)[0])
        probabilities[held]=model.predict_proba(source_features[held])[:,query_class]
        diagnostics.append({'source_fold':str(fold),'source_fit_rows':int(fit.sum()),
            'source_predicted_rows':int(held.sum()),'query_geometry_rows':len(query_features),
            'probability_quantiles':_quantiles(probabilities[held])})
        models.append(model)
    if not np.isfinite(probabilities).all(): raise RuntimeError('Incomplete domain source OOF probabilities')
    return probabilities,diagnostics,models

def importance_weights(probability,cap,strength):
    """Mean-one positive weights with an actual final bound [1/cap, cap].

    Project a scaled odds**strength vector into the box, solving its scale so the
    final mean is one. Thus normalization cannot accidentally undo the cap.
    """
    p=np.asarray(probability,float)
    if not len(p) or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError('Invalid domain probabilities')
    if cap<1 or not 0<=strength<=1: raise ValueError('Invalid cap/strength')
    if strength==0 or cap==1: return np.ones(len(p))
    # Numerical protection for classifier leaves with exact probabilities 0 or 1.
    safe=np.clip(p,1e-6,1-1e-6)
    powered=(safe/(1-safe))**strength
    lower,upper=1./cap,cap
    def project(scale): return np.clip(scale*powered,lower,upper)
    left,right=0.,1.
    while project(right).mean()<1.: right*=2.
    for _ in range(80):
        middle=(left+right)/2
        if project(middle).mean()<1.: left=middle
        else: right=middle
    weights=project((left+right)/2)
    if not np.isclose(weights.mean(),1.,atol=1e-10): raise RuntimeError('Weight projection did not normalize')
    return weights

def _weighted_affine(p,low,high,weights):
    from scipy.optimize import linprog
    from scipy.sparse import csr_matrix,eye,hstack,vstack
    if len(p)<2: raise ValueError('Too few observed source labels for affine calibration')
    mean=float(np.mean(p));sd=float(np.std(p));scale=sd if sd>0 else 1.
    z=(p-mean)/scale;n=len(p)
    x=csr_matrix(np.column_stack([z,np.ones(n)]))
    matrix=vstack([hstack([-x,-eye(n)]),hstack([x,-eye(n)])],format='csr')
    # Normalize only the target's weights; this scalar leaves the optimum unchanged.
    weights=weights/weights.mean()
    fit=linprog(np.r_[0.,0.,weights],A_ub=matrix,b_ub=np.r_[-low,high],
        bounds=[(0.,None),(None,None)]+[(0.,None)]*n,method='highs')
    if not fit.success: raise RuntimeError(f'Weighted interval-affine LP failed: {fit.message}')
    slope=float(fit.x[0]/scale);intercept=float(fit.x[1]-slope*mean)
    return {'slope':slope,'intercept':intercept,'n_fit':n,
        'weighted_interval_error_sum':float(fit.fun),'rank_collapsed':bool(slope==0.),
        'effective_sample_size':float(weights.sum()**2/np.square(weights).sum()),
        'target_normalized_weight_quantiles':_quantiles(weights)}

def _fit_apply(source_truth,source_pred,query_pred,targets,weights):
    output=np.empty_like(query_pred,dtype=float);parameters={}
    for j,target in enumerate(targets):
        y=source_truth[target].to_numpy(float)
        low=source_truth[target+'_conf_low'].to_numpy(float)
        high=source_truth[target+'_conf_high'].to_numpy(float)
        observed=np.isfinite(y)
        if np.isinf(y).any() or np.any(observed&(~np.isfinite(low)|~np.isfinite(high)|(low>high))):
            raise ValueError(f'Invalid source truth/confidence bounds for {target}')
        par=_weighted_affine(source_pred[observed,j],low[observed],high[observed],weights[observed])
        output[:,j]=par['slope']*query_pred[:,j]+par['intercept'];parameters[target]=par
    if not np.isfinite(output).all(): raise RuntimeError('Nonfinite placed query predictions')
    return output,parameters

def run_candidate(ooftruth,oofpred,querypred,trainfeatures,queryfeatures,development_folds,
                  config=None,*,allowed_fit_ids=None,forbidden_fit_ids=None,output_dir=None):
    """Return (placed query DataFrame, JSON-safe metadata), without reading query labels.

    Feature frames: Molecule_Name plus identical numeric chemistry-feature columns.
    development_folds: ID->fold mapping, with >=3 folds to allow nested domain OOF.
    Allowed/forbidden ID lists should come from the runner's frozen cohort manifest.
    Raw base OOF provenance and molecular-feature provenance remain caller duties.
    """
    cfg=dict(DEFAULT_CONFIG);cfg.update(config or {})
    ids=_ids(ooftruth,'source OOF truth');qids=_ids(querypred,'query predictions')
    if set(ids)&set(qids): raise ValueError('Source training and query IDs overlap')
    if allowed_fit_ids is not None and not set(ids)<=set(map(str,allowed_fit_ids)):
        raise ValueError('Source IDs exceed frozen allowed training cohort')
    if forbidden_fit_ids is not None and set(ids)&set(map(str,forbidden_fit_ids)):
        raise ValueError('Forbidden gate/test ID present in source truth')
    targets=[t for t in CANONICAL if t in oofpred]
    if not targets: raise ValueError('No recognized base OOF targets')
    p=_aligned(oofpred,ids,targets,'OOF predictions')
    qp=_aligned(querypred,qids,targets,'query predictions')
    columns=[c for c in trainfeatures if c!='Molecule_Name']
    if not columns or set(columns)!=set(queryfeatures)-{'Molecule_Name'}:
        raise ValueError('Training/query chemistry-feature columns differ')
    suspicious=[c for c in columns if any(s in c.lower() for s in [
        'pic50','conf_low','conf_high','ci_lower','ci_upper','activity','interval',
        'log2fc','emax','is_tdi','prediction','base_oof','target'])]
    if suspicious: raise ValueError(f'Domain classifier requires structure-only features: {suspicious}')
    x=_aligned(trainfeatures,ids,columns,'training chemistry features')
    qx=_aligned(queryfeatures,qids,columns,'query chemistry features')
    if not isinstance(development_folds,Mapping): raise TypeError('development_folds must map ID to fold')
    mapping={str(k):v for k,v in development_folds.items()}
    if not set(ids)<=set(mapping): raise ValueError('Missing development fold IDs')
    folds=np.asarray([mapping[i] for i in ids]);unique=pd.unique(folds)
    if len(unique)<3: raise ValueError('Need >=3 development folds for nested domain crossfit')
    grid=[]
    for strength in cfg['strengths']:
        for cap in cfg['caps']:
            strength,cap=float(strength),float(cap)
            if not np.isfinite([strength,cap]).all() or cap<1 or not 0<=strength<=1:
                raise ValueError('Invalid preregistered cap/strength grid')
            if strength==0 and any(item['strength']==0 for item in grid): continue
            grid.append({'strength':strength,'cap':cap})
    if not grid: raise ValueError('Empty calibration grid')
    dev_predictions=[np.full_like(p,np.nan) for _ in grid]
    development_domains=[]
    # Actual outer query features are deliberately absent from development selection.
    for fold_index,fold in enumerate(unique):
        fit=folds!=fold;val=~fit
        prop,domain_meta,_=_domain_crossfit(x[fit],x[val],folds[fit],cfg,int(cfg['seed'])+1000*fold_index)
        development_domains.append({'pseudoquery_fold':str(fold),
            'source_rows':int(fit.sum()),'pseudoquery_geometry_rows':int(val.sum()),
            'source_probability_quantiles':_quantiles(prop),'crossfit':domain_meta})
        for index,item in enumerate(grid):
            weights=importance_weights(prop,item['cap'],item['strength'])
            output,_=_fit_apply(ooftruth.loc[fit].reset_index(drop=True),p[fit],p[val],targets,weights)
            dev_predictions[index][val]=output
    def frame(row_ids,array):
        d=pd.DataFrame(array,columns=targets);d.insert(0,'Molecule_Name',row_ids);return d
    development_scores=[]
    for item,values in zip(grid,dev_predictions):
        if not np.isfinite(values).all(): raise RuntimeError('Incomplete development predictions')
        result=score(ooftruth,frame(ids,values),targets=targets)
        if not result['defined']: raise ValueError('Undefined development score')
        development_scores.append({**item,'score':result})
    selected_index=min(range(len(grid)),key=lambda i:(development_scores[i]['score']['macro_ST_RAE'],grid[i]['strength'],grid[i]['cap']))
    selected=grid[selected_index]
    # Selection is now frozen; only here does actual outer-query geometry enter fitting.
    if selected['strength']==0:
        final_prop=np.full(len(ids),.5);final_weights=np.ones(len(ids));final_domains=[];domain_models=[]
    else:
        final_prop,final_domains,domain_models=_domain_crossfit(x,qx,folds,cfg,int(cfg['seed'])+100000)
        final_weights=importance_weights(final_prop,selected['cap'],selected['strength'])
    placed,parameters=_fit_apply(ooftruth,p,qp,targets,final_weights)
    output=frame(qids,placed)
    metadata={'candidate':CANDIDATE_NAME,'config':cfg,'targets':targets,
        'selected':selected,'development_scores':development_scores,
        'selection_scope':'Development pseudoquery folds only; selection completes before actual query geometry is used.',
        'development_domains':development_domains,'final_domain_crossfit':final_domains,
        'final_affine_parameters':parameters,'query_geometry_used':bool(selected['strength']>0),
        'query_activity_used':False,'query_intervals_used':False,'query_prediction_moments_used':False,
        'classifier_inputs':'Structure-only feature matrix; not predictions, experimental labels, or assay bounds.',
        'domain_prior':'class_weight=balanced; odds are used without a source/query sample-count factor.',
        'weight_rule':'Project c*(p/(1-p))**strength to [1/cap,cap], solving c so final source mean is1.',
        'final_weight_quantiles':_quantiles(final_weights),
        'effective_source_sample_size':float(final_weights.sum()**2/np.square(final_weights).sum()),
        'source_probability_quantiles':_quantiles(final_prop),'n_source':len(ids),'n_query':len(qids),
        'feature_columns':columns,'allowed_fit_ids_checked':allowed_fit_ids is not None,
        'forbidden_fit_ids_checked':forbidden_fit_ids is not None,
        'source_ids_sha256':hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest(),
        'query_ids_sha256':hashlib.sha256(('\n'.join(qids)+'\n').encode()).hexdigest(),
        'source_features_sha256':hashlib.sha256(np.ascontiguousarray(x,dtype='<f8').tobytes()).hexdigest(),
        'query_features_sha256':hashlib.sha256(np.ascontiguousarray(qx,dtype='<f8').tobytes()).hexdigest(),
        'limitations':[
            'Tree probabilities are uncalibrated density-ratio proxies; exact covariate-shift correction is not claimed.',
            'Importance weighting assumes overlapping chemistry and a sufficiently stable conditional assay relation; it does not fix concept shift.',
            'Transductive predictions depend on the query batch chemistry. The feature batch and its hash must be retained.',
            'Development method selection reuses base OOF predictions and is internal tuning; only untouched outer labels estimate final performance.',
            'No intervals are estimated for query molecules. Their confidence bounds, if present as columns, are ignored.',
            'Caller must establish raw base OOF and structure-feature provenance. Column-name guards cannot prove semantic purity.']}
    if output_dir is not None:
        out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
        output.to_csv(out/'predictions.csv',index=False)
        frame(ids,dev_predictions[selected_index]).to_csv(out/'development_selected_crossfit.csv',index=False)
        pd.DataFrame({'Molecule_Name':ids,'query_domain_probability_oof':final_prop,'importance_weight':final_weights}).to_csv(out/'training_domain_weights.csv',index=False)
        (out/'metadata.json').write_text(json.dumps(metadata,indent=2))
        import joblib
        joblib.dump({'domain_models':domain_models,'affine':parameters,'features':columns,'selected':selected},out/'transductive_calibration.joblib',compress=3)
    return output,metadata
