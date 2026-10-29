"""Training-only primary task weights for the preregistered objective comparison.

For primary head j, let D_j = sum_i distance(mean_train(y_j), [l_ij,h_ij])
over observed training labels, and let sigma_j be its positive target scale.
Put r_j=sigma_j/D_j and M=mean_j(r_j). With normalized weight w_j=r_j/M,

    sum_j w_j sum_i distance(z_pred, [z_low,z_high])
      = (1/M) sum_j sum_i distance(pred, [low,high])/D_j
      = (K/M) * macro_ST_RAE.

Thus its primary gradient equals the raw macro-ST-RAE gradient times K/M.
A common loss-reduction denominator adds only a common factor for that pool.
This identity is for interval-L1, not point-MAE or MSE; it does not cover the
separate auxiliary terms, whose supplied weights are deliberately preserved.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

from .reference import DIRECT


def compute_primary_weights(train_frame, target_names, scaler_scale,
                            existing_weights, mode):
    """Return (weights, metadata), in exactly the supplied target_names order.

    Modes: inverse_count uses 1/n_observed; st_rae uses sigma/denominator.
    Only the four lower-case DIRECT heads are changed. Auxiliary targets retain
    their supplied weights. Bounds are mandatory for st_rae on observed rows;
    unknown labels are omitted even if their bound cells contain other values.
    Caller must supply only the fitting partition and its fitted scaler scales.
    """
    if mode not in ('inverse_count', 'st_rae'):
        raise ValueError('mode must be inverse_count or st_rae')
    names = list(target_names)
    if not names or len(names) != len(set(names)):
        raise ValueError('target_names must be nonempty and unique')
    if not isinstance(train_frame, pd.DataFrame):
        raise TypeError('train_frame must be a DataFrame containing only fitting rows')
    scales = np.asarray(scaler_scale, dtype=np.float64)
    old = np.asarray(existing_weights, dtype=np.float64)
    if scales.shape != (len(names),) or old.shape != (len(names),):
        raise ValueError('scaler_scale and existing_weights must align with target_names')
    if not np.isfinite(old).all() or (old < 0).any():
        raise ValueError('Existing task weights must be finite and nonnegative')
    primary = [j for j, name in enumerate(names) if name in DIRECT]
    if not primary:
        raise ValueError('No recognized lower-case DIRECT primary heads')
    raw = []; per_target = {}
    for j in primary:
        name = names[j]
        if name not in train_frame or list(train_frame.columns).count(name) != 1:
            raise ValueError(f'Exactly one training label column is required for {name}')
        y = train_frame[name].to_numpy(dtype=np.float64, na_value=np.nan)
        if np.isinf(y).any():
            raise ValueError(f'Infinite training labels for {name}')
        observed = np.isfinite(y)
        n = int(observed.sum())
        if n == 0:
            raise ValueError(f'No observed training labels for {name}')
        sigma = float(scales[j])
        if not np.isfinite(sigma) or sigma <= 0:
            raise ValueError(f'Primary scaler scale must be finite and positive for {name}')
        mean = float(y[observed].mean())
        denominator = None
        if mode == 'st_rae':
            lower, upper = name+'_ci_lower', name+'_ci_upper'
            if any(list(train_frame.columns).count(c) != 1 for c in (lower, upper)):
                raise ValueError(f'st_rae requires unique {lower} and {upper} columns')
            lo = train_frame[lower].to_numpy(dtype=np.float64, na_value=np.nan)[observed]
            hi = train_frame[upper].to_numpy(dtype=np.float64, na_value=np.nan)[observed]
            if not (np.isfinite(lo).all() and np.isfinite(hi).all()) or (lo > hi).any():
                raise ValueError(f'Missing, nonfinite or reversed bounds on observed training labels for {name}')
            denominator = float((np.maximum(lo-mean, 0.)+np.maximum(mean-hi, 0.)).sum())
            if not np.isfinite(denominator) or denominator <= 0:
                raise ValueError(f'Zero or nonfinite training ST-RAE denominator for {name}')
            weight = sigma/denominator
        else:
            weight = 1./n
        if not np.isfinite(weight) or weight <= 0:
            raise ValueError(f'Nonfinite or nonpositive primary weight for {name}')
        raw.append(weight)
        per_target[name] = {'n_observed':n, 'n_unknown':int(len(y)-n),
            'training_mean':mean, 'scaler_scale':sigma, 'training_ST_RAE_denominator':denominator,
            'unnormalized_weight':float(weight), 'previous_weight':float(old[j])}
    normalizer = float(np.mean(raw))
    if not np.isfinite(normalizer) or normalizer <= 0:
        raise ValueError('Invalid primary weight normalization factor')
    result = old.copy()
    for j, weight in zip(primary, raw):
        result[j] = weight/normalizer
        per_target[names[j]]['normalized_weight'] = float(result[j])
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite normalized task weights')
    auxiliary = [j for j in range(len(names)) if j not in primary]
    assert np.array_equal(result[auxiliary], old[auxiliary])
    metadata = {'mode':mode, 'fit_scope':'supplied training partition only; no validation/query inputs',
        'target_order':names, 'primary_targets':[names[j] for j in primary],
        'n_primary_targets':len(primary), 'training_rows':int(len(train_frame)),
        'primary_mean_weight':float(result[primary].mean()),
        'primary_normalization_divisor':normalizer, 'per_primary_target':per_target,
        'auxiliary_weights_unchanged':{names[j]:float(result[j]) for j in auxiliary},
        'weight_formula':'sigma_j / D_j' if mode=='st_rae' else '1 / n_j',
        'bounds_validated_on_observed_primary_rows':mode=='st_rae',
        'denominator_definition':'Sum of interval distances from the observed training-label mean; no division by n_j.',
        'algebra': {
            'applies_to':'summed primary interval-L1 on standardized targets' if mode=='st_rae' else 'count balancing only; no macro-ST-RAE identity',
            'weighted_scaled_sum_to_raw_macro_factor':normalizer/len(primary) if mode=='st_rae' else None,
            'raw_macro_to_weighted_scaled_sum_factor':len(primary)/normalizer if mode=='st_rae' else None,
            'common_reduction_note':'A common observed-label denominator rescales this identity; varying minibatch denominators change gradient magnitude across batches.',
            'auxiliary_note':'Auxiliary loss terms are outside the macro-ST-RAE identity.'}}
    return result.tolist(), metadata


def synthetic_algebra_check():
    """Small deterministic verification, including masks/bounds and official scorer."""
    from official_scoring_functions import rae_soft_threshold_absolute_error
    y = np.asarray([[4,3,np.nan,1],[6,np.nan,4,2],[8,4,9,3],
                    [np.nan,7,6,4],[5,np.nan,5,5],[7,9,np.nan,6]],dtype=float)
    frame = pd.DataFrame(y, columns=DIRECT)
    half_width = np.asarray([.2,.1,.25,.3])
    lo, hi = y-half_width, y+half_width
    for j, name in enumerate(DIRECT):
        frame[name+'_ci_lower'] = lo[:,j]
        frame[name+'_ci_upper'] = hi[:,j]
    auxiliary = 'cyp2d6_log2fc'
    frame[auxiliary] = np.arange(len(frame),dtype=float)
    scales = np.r_[np.nanstd(y,axis=0),np.std(frame[auxiliary])]
    old = [2.,.5,1.,1.5,.3]
    weights, metadata = compute_primary_weights(frame,DIRECT+[auxiliary],scales,old,'st_rae')
    offsets = np.asarray([[0.,.5,0.,-.8],[1.,0.,-.6,.1],[-.7,.2,.4,1.2],
                          [0.,-.5,.1,-.1],[.1,0.,-.9,.4],[.8,-.3,0.,-.6]])
    prediction = np.nan_to_num(y,nan=5.)+offsets
    observed = np.isfinite(y);means=np.nanmean(y,axis=0)
    zpred=(prediction-means)/scales[:4]
    zlo=(lo-means)/scales[:4];zhi=(hi-means)/scales[:4]
    scaled_distance=np.where(observed,np.maximum(zlo-zpred,0.)+np.maximum(zpred-zhi,0.),0.)
    weighted_scaled_sum=float((scaled_distance*np.asarray(weights[:4])).sum())
    official_scores=[];denominators=[]
    for j,name in enumerate(DIRECT):
        mask=observed[:,j]
        official_scores.append(float(rae_soft_threshold_absolute_error(y[mask,j],prediction[mask,j],
            y_true_lower=lo[mask,j],y_true_upper=hi[mask,j])))
        denominators.append(metadata['per_primary_target'][name]['training_ST_RAE_denominator'])
    macro=float(np.mean(official_scores))
    factor=metadata['algebra']['weighted_scaled_sum_to_raw_macro_factor']
    assert np.isclose(weighted_scaled_sum*factor,macro,atol=1e-12,rtol=1e-12)
    signs=np.where(observed,(prediction>hi).astype(float)-(prediction<lo).astype(float),0.)
    scaled_gradient=signs*(np.asarray(weights[:4])/scales[:4])
    raw_macro_gradient=signs/(4*np.asarray(denominators))
    assert np.allclose(scaled_gradient*factor,raw_macro_gradient,atol=1e-12,rtol=1e-12)
    assert weights[-1]==old[-1] and np.isclose(np.mean(weights[:4]),1.)
    inverse, _=compute_primary_weights(frame,DIRECT+[auxiliary],scales,old,'inverse_count')
    expected=1/observed.sum(axis=0);expected/=expected.mean()
    assert np.allclose(inverse[:4],expected) and inverse[-1]==old[-1]
    invalid=frame.copy();invalid.loc[0,DIRECT[0]+'_ci_lower']=np.nan
    try:compute_primary_weights(invalid,DIRECT+[auxiliary],scales,old,'st_rae')
    except ValueError:pass
    else:raise AssertionError('Missing observed-label bounds accepted')
    zero=frame.copy()
    for name in DIRECT:
        zero[name+'_ci_lower']=-100.;zero[name+'_ci_upper']=100.
    try:compute_primary_weights(zero,DIRECT+[auxiliary],scales,old,'st_rae')
    except ValueError:pass
    else:raise AssertionError('Zero ST-RAE denominator accepted')
    return {'status':'passed','primary_targets':DIRECT,'n_observed':observed.sum(axis=0).tolist(),
        'weights':weights,'weighted_scaled_interval_sum':weighted_scaled_sum,
        'raw_sum_of_target_interval_error_ratios':float(np.sum(official_scores)),
        'recovered_sum_of_target_interval_error_ratios':weighted_scaled_sum*metadata['primary_normalization_divisor'],
        'sum_to_macro_factor':factor,'raw_official_macro_ST_RAE':macro,
        'recovered_macro_ST_RAE':weighted_scaled_sum*factor,
        'gradient_max_absolute_error':float(np.max(np.abs(scaled_gradient*factor-raw_macro_gradient))),
        'auxiliary_weight_unchanged':True,'inverse_count_check':True,
        'missing_bounds_rejected':True,'zero_denominator_rejected':True,
        'scientific_model_training':False}


if __name__=='__main__':
    print(json.dumps(synthetic_algebra_check(),indent=2,allow_nan=False))
