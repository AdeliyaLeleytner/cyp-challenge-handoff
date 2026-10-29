"""Official ST-RAE, development-OOF-only placement, and paired comparisons.

No public-board constants, query-distribution matching, or gate-label calibration.
Calibration inputs must be genuine training OOF predictions supplied by the runner.
"""
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd
from official_scoring_functions import rae_soft_threshold_absolute_error as _official
from .reference import CANONICAL

PLACEMENT_SOURCE = 'https://github.com/SuperCowPowers/workbench/blob/8c72c7559471febaf0962fd551b4eaab8db3a136/ml_pipelines/OpenADMET/cyp/scripts/cyp_recalibrate.py'
PLACEMENT_AUDIT = {
    'source': PLACEMENT_SOURCE,
    'oof_pearson_board_dependency': 'Lines 197-198 multiply measured OOF Pearson by OOF_TO_BLIND, itself derived from board measurements.',
    'place_board_dependency': 'Lines 217-227 use BLIND_MOMENTS; lines 220-222 optionally substitute board-tuned STRAE_MOMENTS.',
    'excluded_constants': ['BLIND_MOMENTS','SOLVED_PEARSON','STRAE_MOMENTS','OOF_TO_BLIND'],
    'local_adaptation': 'Fit an affine map using development training OOF only; do not use query moments, target labels, or the source floor.',
    'claim': 'Reconstructed recipe with independent local calibration, not reproduction of historical leaderboard 0.4378.',
}

@lru_cache(maxsize=1)
def _scorer_provenance():
    p = Path(__file__).resolve().parents[1]/'official_scoring_functions.py'
    return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
            'function':'rae_soft_threshold_absolute_error',
            'denominator':'Sum of interval distances from mean observed truth, recomputed on each evaluated sample.'}

def _ids(frame,name):
    if 'Molecule_Name' not in frame or frame.Molecule_Name.isna().any() or frame.Molecule_Name.duplicated().any():
        raise ValueError(f'{name} requires unique non-null Molecule_Name')
    return frame.Molecule_Name.astype(str).tolist()

def _align(truth,pred,targets):
    ids = _ids(truth,'truth')
    pids = _ids(pred,'predictions')
    if set(ids)!=set(pids): raise ValueError('Truth/prediction ID sets differ; subset explicitly before scoring')
    aligned = pred.assign(Molecule_Name=pids).set_index('Molecule_Name').loc[ids]
    if not set(targets)<=set(aligned): raise ValueError('Missing requested prediction columns')
    values = aligned[targets].to_numpy(float)
    if not np.isfinite(values).all(): raise ValueError('Predictions must be finite, including rows without labels')
    return values

def _truth_arrays(truth,targets):
    y = truth[targets].to_numpy(float)
    lo,hi = [],[]
    for col in targets:
        lc,hc = col+'_conf_low',col+'_conf_high'
        if lc not in truth or hc not in truth:
            raise ValueError(f'Missing official confidence bounds for {col}')
        lo.append(truth[lc].to_numpy(float));hi.append(truth[hc].to_numpy(float))
    lo,hi = np.column_stack(lo),np.column_stack(hi)
    observed = np.isfinite(y)
    if np.isinf(y).any(): raise ValueError('Infinite experimental labels')
    if np.any(observed & (~np.isfinite(lo)|~np.isfinite(hi)|(lo>hi))):
        raise ValueError('Observed labels have missing or reversed confidence bounds')
    return y,lo,hi,observed

def _distance(p,lo,hi):
    return np.maximum(lo-p,0.)+np.maximum(p-hi,0.)

def _score_arrays(y,lo,hi,p,targets):
    endpoints = {}
    for j,col in enumerate(targets):
        m = np.isfinite(y[:,j]); yy,ll,hh,pp = y[m,j],lo[m,j],hi[m,j],p[m,j]
        if len(yy)<2:
            value = float('nan');denom = float('nan')
        else:
            denom = float(_distance(float(yy.mean()),ll,hh).sum())
            with np.errstate(divide='ignore',invalid='ignore'):
                value = float(_official(yy,pp,y_true_upper=hh,y_true_lower=ll))
        endpoints[col] = {'ST_RAE':value,'n':int(m.sum()),'baseline_error_sum':denom,
            'interval_error_sum':float(_distance(pp,ll,hh).sum()),
            'MAE':float(np.mean(np.abs(pp-yy))) if len(yy) else float('nan'),
            'truth_mean':float(yy.mean()) if len(yy) else float('nan')}
    vals = [v['ST_RAE'] for v in endpoints.values()]
    # Undefined targets make the macro undefined; never silently change the target set.
    return {'macro_ST_RAE':float(np.mean(vals)), 'endpoints':endpoints,
            'defined':bool(np.isfinite(vals).all())}

def _targets_from(pred,targets=None):
    selected = list(targets) if targets is not None else [t for t in CANONICAL if t in pred]
    if not selected: raise ValueError('No recognized prediction targets')
    return selected

def score(truth,pred,*,targets=None):
    targets = _targets_from(pred,targets)
    p = _align(truth,pred,targets)
    y,lo,hi,_ = _truth_arrays(truth,targets)
    result = _score_arrays(y,lo,hi,p,targets)
    result['scorer'] = _scorer_provenance()
    result['n_molecules'] = len(truth)
    return result

def score_variants(truth,raw_pred,placed_predictions,*,targets=None):
    """Report raw and named placements without selecting a method on these labels."""
    result = {'raw':score(truth,raw_pred,targets=targets)}
    if isinstance(placed_predictions,pd.DataFrame): placed_predictions={'placed':placed_predictions}
    for name,pred in placed_predictions.items():
        if name=='raw': raise ValueError('Placement name must not overwrite raw')
        result[name]=score(truth,pred,targets=targets)
    return result

def _fit_affine(p,y,lo,hi,method):
    if method=='raw': return {'slope':1.,'intercept':0.,'method':method}
    if len(p)<2: raise ValueError('At least two observed development OOF labels are required')
    pmean,pstd = float(np.mean(p)),float(np.std(p))
    if method=='oof_r2':
        variance = float(np.var(p))
        slope = max(0.,float(np.mean((p-pmean)*(y-y.mean()))/variance)) if variance>0 else 0.
        return {'slope':slope,'intercept':float(y.mean()-slope*pmean),'method':method,
                'negative_slope_constrained':bool(variance>0 and np.mean((p-pmean)*(y-y.mean()))<0)}
    if method!='oof_lp': raise ValueError(f'Unknown calibration method {method}')
    from scipy.optimize import linprog
    from scipy.sparse import csr_matrix, eye, hstack, vstack
    # One slack per molecule: e >= lower-(a*z+b), e >= (a*z+b)-upper.
    # a>=0 preserves order (a=0 may create ties). No arbitrary slope or offset caps.
    scale = pstd if pstd>0 else 1.
    z = (p-pmean)/scale
    n = len(p)
    x = csr_matrix(np.column_stack([z,np.ones(n)]))
    matrix = vstack([hstack([-x,-eye(n)]),hstack([x,-eye(n)])],format='csr')
    fit = linprog(np.r_[0.,0.,np.ones(n)],A_ub=matrix,b_ub=np.r_[-lo,hi],
        bounds=[(0.,None),(None,None)]+[(0.,None)]*n,method='highs')
    if not fit.success: raise RuntimeError(f'Affine interval-L1 solver failed: {fit.message}')
    slope = float(fit.x[0]/scale)
    intercept = float(fit.x[1]-slope*pmean)
    return {'slope':slope,'intercept':intercept,'method':method,
            'optimizer':'scipy.optimize.linprog/highs','status':int(fit.status),
            'interval_absolute_error_sum':float(fit.fun),'prediction_mean_fit':pmean,
            'prediction_std_fit':pstd,'rank_collapsed':bool(slope==0.)}

def _fit_params(truth,pred,targets,method):
    p = _align(truth,pred,targets)
    y,lo,hi,observed = _truth_arrays(truth,targets)
    params = {}
    for j,col in enumerate(targets):
        m = observed[:,j]
        params[col] = _fit_affine(p[m,j],y[m,j],lo[m,j],hi[m,j],method)
        params[col]['n_fit'] = int(m.sum())
        r2 = _fit_affine(p[m,j],y[m,j],lo[m,j],hi[m,j],'oof_r2')
        params[col]['oof_r2_standin'] = r2
    return params

def apply_calibration(pred,parameters,*,targets=None):
    targets = list(targets or parameters['targets'])
    _ids(pred,'query predictions')
    result = pred[['Molecule_Name']+targets].copy()
    if not np.isfinite(result[targets].to_numpy(float)).all(): raise ValueError('Nonfinite query predictions')
    for col in targets:
        par = parameters['per_target'][col]
        result[col] = par['slope']*result[col]+par['intercept']
    if not np.isfinite(result[targets].to_numpy(float)).all(): raise ValueError('Nonfinite calibrated predictions')
    return result

def calibrate(ooftruth,oofpred,querypred,*,method='oof_lp',targets=None,allowed_fit_ids=None,forbidden_fit_ids=None):
    """Fit only on train OOF, then apply the frozen affine map to disjoint query IDs.

    Caller should pass allowed_fit_ids from its frozen outer training cohort. OOF
    fit scores are diagnostic apparent calibration error, not unbiased validation.
    """
    targets = _targets_from(oofpred,targets)
    fit_ids = _ids(ooftruth,'development OOF truth')
    query_ids = _ids(querypred,'query predictions')
    if set(fit_ids)&set(query_ids): raise ValueError('Calibration OOF/query ID overlap; gate labels cannot fit placement')
    if allowed_fit_ids is not None and not set(fit_ids)<=set(map(str,allowed_fit_ids)):
        raise ValueError('Calibration contains IDs outside the frozen training cohort')
    if forbidden_fit_ids is not None and set(fit_ids)&set(map(str,forbidden_fit_ids)):
        raise ValueError('Calibration contains forbidden gate/test IDs')
    params = {'method':method,'targets':targets,'per_target':_fit_params(ooftruth,oofpred,targets,method),
        'fit_ids_sha256':hashlib.sha256(('\n'.join(fit_ids)+'\n').encode()).hexdigest(),
        'n_fit_molecules':len(fit_ids),'allowed_fit_ids_checked':allowed_fit_ids is not None,
        'forbidden_fit_ids_checked':forbidden_fit_ids is not None,
        'query_labels_used':False,'query_moments_used':False,'source_audit':PLACEMENT_AUDIT,
        'oof_provenance':'Runner must establish each prediction was made without its own molecule in fit.',
        'fit_score_warning':'These are apparent calibration fit scores; use development calibration folds for method selection.'}
    result = apply_calibration(querypred,params)
    params['oof_raw_score'] = score(ooftruth,oofpred,targets=targets)
    params['oof_calibration_fit_score'] = score(ooftruth,apply_calibration(oofpred,params),targets=targets)
    return result,params

def calibrate_variants(ooftruth,oofpred,querypred,development_folds,*,targets=None,allowed_fit_ids=None,forbidden_fit_ids=None):
    """Select raw/OOF-LP/OOF-R2 on cross-fitted DEVELOPMENT calibration predictions.

    development_folds maps every OOF Molecule_Name to a fixed fold. The gate query
    is used only after selection. The returned selected_name is frozen before any
    gate scoring; report all three variants but never reselect on gate outcomes.
    """
    targets = _targets_from(oofpred,targets)
    ids = _ids(ooftruth,'development OOF truth')
    mapping = dict(development_folds)
    if not set(ids)<=set(map(str,mapping)): raise ValueError('Missing development calibration fold IDs')
    mapping = {str(k):v for k,v in mapping.items()}
    folds = np.asarray([mapping[i] for i in ids])
    unique = pd.unique(folds)
    if len(unique)<2: raise ValueError('At least two development calibration folds required')
    p = oofpred.assign(Molecule_Name=oofpred.Molecule_Name.astype(str)).set_index('Molecule_Name').loc[ids].reset_index()
    predictions,parameters,cv_scores = {},{},{}
    for method in ['raw','oof_lp','oof_r2']:
        crossfit = p.copy()
        if method!='raw':
            for fold in unique:
                fit = folds!=fold; val = ~fit
                part = {'targets':targets,'per_target':_fit_params(ooftruth.loc[fit].reset_index(drop=True),p.loc[fit].reset_index(drop=True),targets,method)}
                placed = apply_calibration(p.loc[val].reset_index(drop=True),part)
                crossfit.loc[val,targets]=placed[targets].to_numpy()
        cv_scores[method]=score(ooftruth,crossfit,targets=targets)
        if not cv_scores[method]['defined']: raise ValueError('Undefined development calibration score')
        predictions[method],parameters[method]=calibrate(ooftruth,p,querypred,method=method,targets=targets,
            allowed_fit_ids=allowed_fit_ids,forbidden_fit_ids=forbidden_fit_ids)
    # Stable tie order favors raw, then LP, then R2; no gate values enter this choice.
    selected = min(cv_scores,key=lambda name:cv_scores[name]['macro_ST_RAE'])
    metadata = {'selected_name':selected,'selection_scope':'cross-fitted development training OOF only',
        'development_scores':cv_scores,'n_calibration_folds':len(unique),'parameters':parameters,
        'source_audit':PLACEMENT_AUDIT}
    return predictions,metadata

def compare(truth,candidate,reference,*,n_bootstrap=2000,seed=42,confidence=.95,targets=None):
    """Candidate-minus-reference deltas with paired seed and molecule resampling.

    DataFrames represent one seed; mappings represent matched seed->DataFrame.
    The point estimate is mean per-seed score delta, not score of averaged vectors.
    Both intervals preserve the same sampled molecules across targets and methods.
    """
    if isinstance(candidate,pd.DataFrame): candidate={'single':candidate}
    if isinstance(reference,pd.DataFrame): reference={'single':reference}
    if not isinstance(candidate,Mapping) or not isinstance(reference,Mapping): raise TypeError('Predictions must be DataFrames or matched seed mappings')
    if set(candidate)!=set(reference) or not candidate: raise ValueError('Candidate/reference seed keys must match exactly')
    if n_bootstrap<1 or not 0<confidence<1: raise ValueError('Invalid bootstrap settings')
    seeds = list(candidate)
    targets = _targets_from(candidate[seeds[0]],targets)
    cp = np.stack([_align(truth,candidate[s],targets) for s in seeds])
    rp = np.stack([_align(truth,reference[s],targets) for s in seeds])
    y,lo,hi,_ = _truth_arrays(truth,targets)
    point=[];per_seed={}
    for i,s in enumerate(seeds):
        c=_score_arrays(y,lo,hi,cp[i],targets);r=_score_arrays(y,lo,hi,rp[i],targets)
        if not c['defined'] or not r['defined']: raise ValueError('Undefined point score')
        d=c['macro_ST_RAE']-r['macro_ST_RAE'];point.append(d)
        per_seed[str(s)]={'candidate':c,'reference':r,'delta':d}
    rng=np.random.default_rng(seed)
    molecule_deltas=[];hierarchical_deltas=[];target_deltas=[];undefined=0
    for _ in range(n_bootstrap):
        rows=rng.integers(0,len(truth),len(truth))
        sd=[];td=[]
        for i in range(len(seeds)):
            c=_score_arrays(y[rows],lo[rows],hi[rows],cp[i,rows],targets)
            r=_score_arrays(y[rows],lo[rows],hi[rows],rp[i,rows],targets)
            sd.append(c['macro_ST_RAE']-r['macro_ST_RAE'])
            td.append([c['endpoints'][t]['ST_RAE']-r['endpoints'][t]['ST_RAE'] for t in targets])
        if not np.isfinite(sd).all(): undefined+=1;continue
        molecule_deltas.append(float(np.mean(sd)));target_deltas.append(np.mean(td,axis=0))
        drawn_seeds=rng.integers(0,len(seeds),len(seeds))
        hierarchical_deltas.append(float(np.asarray(sd)[drawn_seeds].mean()))
    alpha=(1-confidence)/2
    def summary(values):
        if not values: return {'defined':False,'valid_replicates':0}
        return {'defined':True,'valid_replicates':len(values),'mean':float(np.mean(values)),
                'confidence':confidence,'ci':np.quantile(values,[alpha,1-alpha]).tolist()}
    per_target={}
    if target_deltas:
        arr=np.asarray(target_deltas)
        per_target={t:summary(arr[:,j].tolist()) for j,t in enumerate(targets)}
    return {'delta_candidate_minus_reference':float(np.mean(point)),'lower_is_better':True,
        'n_paired_seeds':len(seeds),'per_seed':per_seed,
        'seed_delta_sd':float(np.std(point,ddof=1)) if len(point)>1 else None,
        'paired_molecule_bootstrap':summary(molecule_deltas),
        'paired_seed_and_molecule_bootstrap':summary(hierarchical_deltas),
        'per_target_paired_molecule_bootstrap':per_target,'undefined_bootstrap_replicates':undefined,
        'requested_bootstrap_replicates':n_bootstrap,'bootstrap_seed':seed,
        'uncertainty_note':'Molecule bootstrap conditions on fitted models. Seed+molecule interval additionally resamples the observed matched seeds; one seed cannot estimate training-seed variability.',
        'scorer':_scorer_provenance()}
