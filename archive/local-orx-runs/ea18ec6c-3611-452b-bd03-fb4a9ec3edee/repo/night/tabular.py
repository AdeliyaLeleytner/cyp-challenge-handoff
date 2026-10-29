"""Trial-local tabular learners with train-only transforms and pinned TFM assets.

The orchestrator owns folds, evaluation and model selection. This module never
uses query labels, downloads weights, changes cohorts, or tunes against holdout.
"""
from __future__ import annotations

import gc
import importlib.metadata
import json
from pathlib import Path
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.kernel_ridge import KernelRidge
from sklearn.metrics.pairwise import rbf_kernel
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import build_features, molecule_ids, pairwise_tanimoto, verified_file

PRIMARY = [f'{c}_pIC50_direct_inhibition' for c in ('CYP1A2','CYP2C9','CYP2D6','CYP3A4')]
_MODEL_ALIASES = {'extra_trees': 'extratrees', 'extra_trees_regressor': 'extratrees',
                  'random_forest': 'rf', 'randomforest': 'rf', 'catboostregressor': 'catboost',
                  'tanimoto_krr': 'krr', 'kernel_ridge': 'krr', 'tabiclv2': 'tabicl'}


def _json(value):
    if isinstance(value, Path): return str(value)
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, np.generic): return value.item()
    raise TypeError(f'Non-serializable trial configuration: {type(value).__name__}')


def _write_json(path: Path, value: Any):
    path.write_text(json.dumps(value, indent=2, default=_json, allow_nan=False)+'\n')


def _targets(config: dict) -> list[str]:
    targets = config.get('targets', PRIMARY)
    if isinstance(targets, str): targets = [targets]
    targets = [v if v in PRIMARY else v+'_pIC50_direct_inhibition' for v in targets]
    if not targets or len(set(targets)) != len(targets) or any(t not in PRIMARY for t in targets):
        raise ValueError('targets must be a nonempty unique subset of the four canonical CYP endpoints')
    return targets


def _feature_specs(config: dict) -> list[dict]:
    specs = config.get('features')
    if specs is None:
        specs = [{'family': config.get('feature_family', 'morgan_bits'), **config.get('feature_params', {})}]
    if isinstance(specs, (str, dict)): specs = [specs]
    return [{'family': v} if isinstance(v, str) else dict(v) for v in specs]


def _feature_matrix(frame: pd.DataFrame, config: dict, asset_root: Path):
    arrays, names, metadata = [], [], []
    for i, spec in enumerate(_feature_specs(config)):
        if 'family' not in spec: raise ValueError('Every feature specification requires family')
        arr, cols, meta = build_features(frame, spec['family'], asset_root, spec)
        if arr.shape != (len(frame), len(cols)): raise ValueError('Feature builder returned inconsistent shape')
        arrays.append(arr); names.extend(f'{i}:{c}' for c in cols); metadata.append(meta)
    if not arrays: raise ValueError('At least one feature family is required')
    X = np.concatenate(arrays, axis=1).astype(np.float32, copy=False)
    X = np.where(np.isfinite(X), X, np.nan).astype(np.float32, copy=False)
    return X, names, metadata


def _preprocess(config: dict, X: np.ndarray):
    options = dict(config.get('preprocessing', {}))
    imputer_args = {'strategy': options.get('impute_strategy', 'median'), 'keep_empty_features': True,
                    'add_indicator': bool(options.get('add_indicator', False))}
    if imputer_args['strategy'] == 'constant': imputer_args['fill_value'] = options.get('fill_value', 0.0)
    steps = [('imputer', SimpleImputer(**imputer_args))]
    requested = options.get('pca_components')
    scale = bool(options.get('scale', requested is not None))
    if scale: steps.append(('scale', StandardScaler()))
    # Determine effective dimensions after the actual train-fitted imputer.
    # Fit the complete pipeline below; this temporary transform is label-free and train-only.
    probe = steps[0][1].fit_transform(X)
    pca_effective = None
    if requested is not None:
        if int(requested) < 1: raise ValueError('pca_components must be a positive integer')
        pca_effective = min(int(requested), probe.shape[0], probe.shape[1])
        steps.append(('pca', PCA(n_components=pca_effective,
                                 svd_solver=options.get('pca_solver', 'randomized'),
                                 random_state=int(config.get('seed', 42)))))
    pipe = Pipeline(steps)
    Xt = pipe.fit_transform(X).astype(np.float32, copy=False)
    if not np.isfinite(Xt).all(): raise ValueError('Nonfinite training features after preprocessing')
    return pipe, Xt, {'fit_rows': len(X), 'fit_pool': 'all supplied training molecules; no query/validation rows',
                      'options': options, 'pca_requested': requested, 'pca_effective': pca_effective,
                      'output_features': Xt.shape[1]}


def _kernel_settings(config: dict):
    params = dict(config.get('model_params', {}))
    kernel = params.pop('kernel', config.get('kernel', 'tanimoto'))
    alpha = float(params.pop('alpha', 1.0)); gamma = params.pop('gamma', None)
    power = int(params.pop('kernel_power', 1))
    center = bool(params.pop('center_target', config.get('center_target', False)))
    if params: raise ValueError(f'Unsupported KernelRidge parameters: {sorted(params)}')
    if alpha <= 0 or power < 1: raise ValueError('KRR alpha and kernel_power must be positive')
    aliases = {'tanimoto': 'tdp', 'tanimoto_dot': 'tdp', 'tanimoto_minmax': 'tmm', 'minmax': 'tmm'}
    kernel = aliases.get(kernel, kernel)
    if kernel not in ('tdp', 'tmm', 'linear', 'rbf'): raise ValueError(f'Unsupported kernel {kernel}')
    return {'kernel': kernel, 'alpha': alpha, 'gamma': gamma, 'kernel_power': power, 'center_target': center}


def _kernel(X: np.ndarray, Y: np.ndarray, params: dict) -> np.ndarray:
    kind = params['kernel']
    if kind in ('tdp', 'tmm'): K = pairwise_tanimoto(X, Y, kind)
    elif kind == 'linear': K = np.asarray(X, dtype=np.float64) @ np.asarray(Y, dtype=np.float64).T
    else: K = rbf_kernel(X, Y, gamma=params['gamma'])
    return np.asarray(K, dtype=np.float64) ** params['kernel_power']


def _tfm(config: dict, kind: str, asset_root: Path):
    asset = config.get('model_asset')
    if not isinstance(asset, dict): raise ValueError('TFM requires explicit model_asset={path,sha256}; no implicit download')
    model_path = verified_file(asset['path'], asset['sha256'], asset_root)
    params = dict(config.get('model_params', {}))
    if 'model_path' in params or 'allow_auto_download' in params:
        raise ValueError('Use pinned model_asset; model_params cannot override model_path/download policy')
    params.setdefault('n_estimators', 8); params.setdefault('random_state', int(config.get('seed', 42)))
    params.setdefault('device', config.get('device', 'cuda'))
    if kind == 'tabpfn':
        from tabpfn import TabPFNRegressor
        model = TabPFNRegressor(model_path=str(model_path), **params)
    else:
        from tabicl import TabICLRegressor
        params.setdefault('n_jobs', int(config.get('num_threads', 4)))
        model = TabICLRegressor(model_path=str(model_path), allow_auto_download=False, **params)
    return model, {'path': str(model_path), 'sha256': asset['sha256'], 'parameters': params,
                   'package_version': importlib.metadata.version(kind)}


def _release_tfm():
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available(): torch.cuda.empty_cache()
    except ImportError:
        pass


def run_trial(config: dict, train_df: pd.DataFrame, query_df: pd.DataFrame,
              asset_root: Path, output_dir: Path,
              validation_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Fit a declared tabular recipe and predict every query row without reading its labels.

    Imputer/scaler/PCA are fitted on all supplied training feature rows; each
    target learner is fitted only on its known training labels. validation_df is
    intentionally unused for these fixed configurations. Root owns CV/HPO.
    Persistence: sklearn joblib, CatBoost cbm, KRR dual coefficients, or TFM
    transformed training context + pinned foundation asset (no duplicated weights).
    """
    config = dict(config); asset_root = Path(asset_root); output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic(); kind = str(config.get('model', 'extratrees')).lower(); kind = _MODEL_ALIASES.get(kind, kind)
    if kind not in ('extratrees', 'rf', 'catboost', 'krr', 'tabpfn', 'tabicl'): raise ValueError(f'Unknown model {kind}')
    ids = molecule_ids(train_df); qids = molecule_ids(query_df)
    if set(ids) & set(qids): raise ValueError('Training and query Molecule_Name overlap')
    if not len(train_df) or not len(query_df): raise ValueError('Training and query frames must be nonempty')
    targets = _targets(config)
    for t in targets:
        if t not in train_df: raise ValueError(f'Training target absent: {t}')
    Y = train_df[targets].to_numpy(dtype=np.float64)
    if np.isinf(Y).any(): raise ValueError('Infinite training target; missing labels must be NaN')
    if any(np.isfinite(Y[:,k]).sum() == 0 for k in range(len(targets))): raise ValueError('A requested endpoint has no observed training labels')
    meta = {'status': 'running', 'config': config, 'model': kind, 'targets': targets,
            'train_ids': ids, 'query_ids': qids, 'validation_used': False,
            'validation_rows_supplied': 0 if validation_df is None else len(validation_df),
            'versions': {p: importlib.metadata.version(p) for p in ('numpy','pandas','scikit-learn','rdkit')},
            'targets_metadata': {}}
    _write_json(output_dir/'trial.json', meta)
    try:
        X, columns, train_features = _feature_matrix(train_df, config, asset_root)
        Q, qcolumns, query_features = _feature_matrix(query_df, config, asset_root)
        if columns != qcolumns: raise ValueError('Training/query feature column mismatch')
        kernel_params = _kernel_settings(config) if kind == 'krr' else None
        if kind == 'krr' and kernel_params['kernel'] in ('tdp','tmm'):
            pp = config.get('preprocessing', {})
            if pp.get('scale', False) or pp.get('pca_components') is not None or pp.get('add_indicator', False):
                raise ValueError('Tanimoto kernels cannot use standardization, PCA, or missingness-indicator augmentation')
            if not np.isfinite(X).all() or not np.isfinite(Q).all() or (X<0).any() or (Q<0).any():
                raise ValueError('Tanimoto features must be finite nonnegative fingerprints')
            transform = None; Xt = X; Qt = Q
            prep_meta = {'fit_pool': 'none; raw fingerprints', 'output_features': X.shape[1]}
        else:
            transform, Xt, prep_meta = _preprocess(config, X)
            Qt = transform.transform(Q).astype(np.float32, copy=False)
        if not np.isfinite(Qt).all(): raise ValueError('Nonfinite query features after train-only transformation')
        joblib.dump(transform, output_dir/'transform.joblib')
        np.savez_compressed(output_dir/'context.npz', X=Xt, Y=Y, ids=np.asarray(ids,dtype=str), targets=np.asarray(targets,dtype=str))
        meta.update(feature_columns=columns, train_features=train_features, query_features=query_features, preprocessing=prep_meta)
        prediction = np.empty((len(query_df), len(targets)), dtype=np.float64)
        for k, target in enumerate(targets):
            observed = np.isfinite(Y[:,k]); y = Y[observed,k]; fitX = Xt[observed]
            target_meta = {'n_labels': int(observed.sum()), 'labelled_train_ids': [ids[i] for i in np.flatnonzero(observed)]}
            params = dict(config.get('model_params', {})); seed = int(config.get('seed',42)); threads=int(config.get('num_threads',4))
            if kind in ('rf','extratrees'):
                params.setdefault('random_state',seed);params.setdefault('n_jobs',threads)
                cls = RandomForestRegressor if kind == 'rf' else ExtraTreesRegressor
                model = cls(**params);model.fit(fitX,y);p = model.predict(Qt)
                filename = target+'.joblib';joblib.dump(model,output_dir/filename);target_meta.update(storage='joblib',file=filename,parameters=params)
            elif kind == 'catboost':
                from catboost import CatBoostRegressor
                params.setdefault('loss_function',config.get('loss','RMSE'));params.setdefault('random_seed',seed)
                params.setdefault('thread_count',threads);params.setdefault('allow_writing_files',False);params.setdefault('verbose',False)
                model=CatBoostRegressor(**params);model.fit(fitX,y);p=model.predict(Qt)
                filename=target+'.cbm';model.save_model(str(output_dir/filename));target_meta.update(storage='catboost',file=filename,parameters=params)
            elif kind == 'krr':
                offset=float(y.mean()) if kernel_params['center_target'] else 0.0
                model=KernelRidge(alpha=kernel_params['alpha'],kernel='precomputed');model.fit(_kernel(fitX,fitX,kernel_params),y-offset)
                p=model.predict(_kernel(Qt,fitX,kernel_params))+offset
                filename=target+'.dual.npz';np.savez_compressed(output_dir/filename,dual_coef=model.dual_coef_,observed=observed,offset=offset)
                target_meta.update(storage='kernel_dual',file=filename,parameters=kernel_params)
            else:
                model,asset_meta=_tfm(config,kind,asset_root);model.fit(fitX,y);p=model.predict(Qt)
                target_meta.update(storage='in_context',foundation=asset_meta)
            p=np.asarray(p,dtype=np.float64).reshape(-1)
            if p.shape!=(len(query_df),) or not np.isfinite(p).all(): raise ValueError(f'{kind}/{target} did not produce one finite prediction per query')
            prediction[:,k]=p;meta['targets_metadata'][target]=target_meta
            del model
            if kind in ('tabpfn','tabicl'): _release_tfm()
        out=pd.DataFrame({'Molecule_Name':query_df.Molecule_Name.to_numpy(),**{t:prediction[:,k] for k,t in enumerate(targets)}})
        out.to_csv(output_dir/'predictions.csv',index=False)
        meta.update(status='complete',elapsed_seconds=time.monotonic()-start)
        _write_json(output_dir/'trial.json',meta)
        print('TABULAR_TRIAL_COMPLETE',json.dumps({'model':kind,'targets':targets,'query_rows':len(out),'seconds':meta['elapsed_seconds']}),flush=True)
        return out
    except Exception as exc:
        meta.update(status='failed',error_type=type(exc).__name__,error=str(exc),elapsed_seconds=time.monotonic()-start)
        _write_json(output_dir/'trial.json',meta)
        raise


def predict_saved_trial(trial_dir: Path, query_df: pd.DataFrame, asset_root: Path) -> pd.DataFrame:
    """Reload a complete trial for new molecules, without refitting feature transforms.

    TFM adapters reconstruct in-context state from the retained labelled training
    context and pinned pretrained model. No target from query_df is consulted.
    """
    trial_dir=Path(trial_dir);asset_root=Path(asset_root);meta=json.loads((trial_dir/'trial.json').read_text())
    if meta['status']!='complete': raise ValueError('Cannot restore an incomplete trial')
    molecule_ids(query_df);config=meta['config'];kind=meta['model'];targets=meta['targets']
    Q,cols,_=_feature_matrix(query_df,config,asset_root)
    if cols!=meta['feature_columns']:raise ValueError('Restored feature columns differ from fitted trial')
    transform=joblib.load(trial_dir/'transform.joblib');Qt=Q if transform is None else transform.transform(Q).astype(np.float32,copy=False)
    if not np.isfinite(Qt).all():raise ValueError('Nonfinite restored query representation')
    with np.load(trial_dir/'context.npz',allow_pickle=False) as context:X=context['X'];Y=context['Y']
    pred=np.empty((len(query_df),len(targets)))
    for k,target in enumerate(targets):
        tm=meta['targets_metadata'][target];observed=np.isfinite(Y[:,k])
        if tm['storage']=='joblib':model=joblib.load(trial_dir/tm['file']);p=model.predict(Qt)
        elif tm['storage']=='catboost':
            from catboost import CatBoostRegressor
            model=CatBoostRegressor();model.load_model(str(trial_dir/tm['file']));p=model.predict(Qt)
        elif tm['storage']=='kernel_dual':
            with np.load(trial_dir/tm['file'],allow_pickle=False) as stored:
                p=_kernel(Qt,X[stored['observed']],tm['parameters'])@stored['dual_coef']+float(stored['offset'])
            model=None
        elif tm['storage']=='in_context':
            model,_=_tfm(config,kind,asset_root);model.fit(X[observed],Y[observed,k]);p=model.predict(Qt)
        else:raise ValueError(f'Unknown stored model format {tm["storage"]}')
        p=np.asarray(p,dtype=float).reshape(-1)
        if len(p)!=len(query_df) or not np.isfinite(p).all():raise ValueError('Invalid restored predictions')
        pred[:,k]=p;del model
        if kind in ('tabpfn','tabicl'):_release_tfm()
    return pd.DataFrame({'Molecule_Name':query_df.Molecule_Name.to_numpy(),**{t:pred[:,k] for k,t in enumerate(targets)}})
