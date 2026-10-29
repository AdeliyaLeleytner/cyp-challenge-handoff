"""Pinned Hauser FinalTDI reproduction with explicit outer-cohort boundaries.

Only the adapter assembles/alines inputs. Original feature, fold, fitting,
probability averaging and threshold functions execute unchanged. Full registry
is canonical-identity union of direct, TDI and raw screening training tables.
"""
from __future__ import annotations
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
import time
import types
import numpy as np
import pandas as pd
from rdkit import Chem
from .data import structure_keys, sha, write_json
from .evaluation import TARGETS, score

REVISION = '06e1e1fcf7341333e4623ce353c65c6b4b6e71f3'
SOURCE_FILES = {
    'final_tdi.py': ('hauser-models_final_tdi.py', 'fce6313d3ad3d1850a9f6d4a2bdbc2e5102e4dca06a239bdc08449c64cd0442c'),
    'features.py': ('hauser-training_features.py', 'd95af6301de8a17d5a407d38d257b70495b4afdfe37e4ee983dc58e19d5242bb'),
    'tdi_features.py': ('hauser-training_tdi_features.py', '65b82d3704c97a568e9a28adad9bcdb9bb5183d53cec2cf96eafd9e8af55695b'),
}


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sources(source_dir=None):
    root = Path(source_dir) if source_dir is not None else Path(__file__).resolve().parents[1] / 'vendor' / 'hauser'
    paths = {}
    for filename, (download_name, expected) in SOURCE_FILES.items():
        path = root / filename
        if not path.exists():
            path = root / download_name
        if not path.is_file() or sha(path) != expected:
            raise ValueError(f'Missing or altered pinned Hauser source: {path}')
        paths[filename] = path
    original_features = _module('tdi._hauser_original_features', paths['features.py'])
    # Original tdi_features imports training.features; bind just during import.
    previous = {name: sys.modules.get(name) for name in ('training', 'training.features')}
    sys.modules['training'] = types.ModuleType('training')
    sys.modules['training.features'] = original_features
    try:
        features = _module('tdi._hauser_original_tdi_features', paths['tdi_features.py'])
    finally:
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
    model = _module('tdi._hauser_original_final_tdi', paths['final_tdi.py'])
    return model, features, {name: {'path': str(p), 'sha256': sha(p)} for name, p in paths.items()}


def _canonical(s):
    mol = Chem.MolFromSmiles(s)
    if mol is None:
        raise ValueError('Invalid molecular structure')
    return Chem.MolToSmiles(mol, isomericSmiles=True)


def _identities(frame):
    frame = frame.copy()
    frame['canonical_smiles'] = frame.SMILES.map(_canonical)
    return frame


def _raw_screen(prepared, explicit=None):
    paths = [Path(explicit)] if explicit is not None else []
    paths += [prepared / 'originals' / 'aux_single_raw.csv',
              prepared / 'originals' / 'source_single_concentration.csv',
              prepared / 'originals' / 'single_concentration.csv',
              prepared / 'originals' / 'aux_single_concentration.csv',
              prepared.parent / 'single_concentration.csv',
              prepared.parent.parent / 'stage' / 'single_concentration.csv']
    for path in paths:
        if not path.is_file():
            continue
        head = pd.read_csv(path, nrows=0)
        if {'enzyme', 'log2fc_estimate'}.issubset(head.columns):
            raw = pd.read_csv(path)
            raw = raw.rename(columns={'molecule_name': 'Molecule_Name', 'smiles': 'SMILES'})
            if not {'Molecule_Name', 'SMILES', 'enzyme', 'log2fc_estimate'}.issubset(raw.columns):
                raise ValueError('Raw screen lacks molecular identity/response columns')
            return _identities(raw), path
    raise FileNotFoundError('Native Hauser requires RAW single-concentration rows; supply raw_screen_path')


def _assemble(prepared_dir, cohort='full', raw_screen_path=None):
    """Build source-native identity registry, with query responses/labels absent."""
    p = Path(prepared_dir)
    train = _identities(pd.read_csv(p / 'train.csv', usecols=['Molecule_Name', 'SMILES']))
    direct = _identities(pd.read_csv(p / 'direct_train.csv', usecols=['Molecule_Name', 'SMILES']))
    official_test = _identities(pd.read_csv(p / 'test.csv', usecols=['Molecule_Name', 'SMILES']))
    screen, screen_path = _raw_screen(p, raw_screen_path)
    cdir = p / 'cohorts' / cohort
    dev_idx = np.load(cdir / 'train_indices.npy', allow_pickle=False)
    if cohort == 'full':
        query = official_test
    elif cohort in ('own750', 'briford529'):
        query = train.iloc[np.load(cdir / 'holdout_indices.npy', allow_pickle=False)].copy()
    else:
        raise ValueError('Unknown cohort')
    dev = train.iloc[dev_idx].copy()
    # Only read values at allowed development rows; query truth is never selected.
    label_array = np.load(p / 'y_train.npy', mmap_mode='r', allow_pickle=False)
    ydev = np.asarray(label_array[dev_idx], dtype=np.float32)
    forbidden = train.drop(index=dev_idx) if cohort != 'full' else train.iloc[:0]
    forbidden = pd.concat([forbidden, official_test, query], ignore_index=True)
    banned_keys = [structure_keys(s) for s in forbidden.SMILES]
    connectivity = {k[0] for k in banned_keys}; parents = {k[1] for k in banned_keys}
    banned_ids = set(forbidden.Molecule_Name)
    def keep(frame):
        keys = [structure_keys(s) for s in frame.SMILES]
        return np.array([name not in banned_ids and a not in connectivity and b not in parents
                         for name, (a, b) in zip(frame.Molecule_Name, keys)])
    if not keep(dev).all():
        raise ValueError('Prepared development pool overlaps excluded query identity')
    direct_allowed = direct.loc[keep(direct)].copy()
    screen_allowed = screen.loc[keep(screen)].copy()
    # Native loader order: regression, classification, screen; drop exact canonical duplicates.
    registry = pd.concat([direct_allowed, dev, screen_allowed[['Molecule_Name', 'SMILES', 'canonical_smiles']]],
                         ignore_index=True).drop_duplicates('canonical_smiles').reset_index(drop=True)
    n_train = len(registry)
    query_registry = query.drop_duplicates('canonical_smiles').reset_index(drop=True)
    if set(registry.canonical_smiles) & set(query_registry.canonical_smiles):
        raise ValueError('Native train and query identities overlap')
    all_registry = pd.concat([registry, query_registry], ignore_index=True)
    lookup = {s: i for i, s in enumerate(all_registry.canonical_smiles)}
    y = np.full((n_train, 2), np.nan, dtype=np.float32)
    for row, values in zip(dev.itertuples(), ydev):
        index = lookup[row.canonical_smiles]
        for j, value in enumerate(values):
            if np.isfinite(value):
                if np.isfinite(y[index, j]) and y[index, j] != value:
                    raise ValueError('Conflicting binary labels for an identical canonical compound')
                y[index, j] = value
    responses = np.full((len(all_registry), 2), np.nan)
    grouped = screen_allowed.groupby(['canonical_smiles', 'enzyme']).log2fc_estimate.mean()
    for (identity, enzyme), value in grouped.items():
        if enzyme in ('CYP2D6', 'CYP3A4'):
            index = lookup[identity]
            assert index < n_train
            responses[index, ('CYP2D6', 'CYP3A4').index(enzyme)] = value
    assert np.isnan(responses[n_train:]).all()
    query_map = np.array([lookup[s] - n_train for s in query.canonical_smiles])
    dev_map = np.array([lookup[s] for s in dev.canonical_smiles])
    return dict(registry=all_registry, n_train=n_train, labels=y, responses=responses,
                query=query, dev=dev, dev_map=dev_map, query_map=query_map,
                screen_path=screen_path, screen_rows_used=len(screen_allowed),
                additional_native_registry_rows=n_train - len(dev),
                dev_indices=dev_idx)


def run_native(prepared_dir, output_dir, cohort='full', *, source_dir=None, raw_screen_path=None):
    """Train original 3x5 Hauser procedure, export OOF/query arrays and frozen calls.

    Output oof/query arrays align to prepared cohort train/holdout order; native
    registry and full components retain screen-only rows. Native thresholds are
    fitted on training OOF only. Outer query labels are deliberately not read.
    """
    import joblib
    from threadpoolctl import threadpool_limits
    out = Path(output_dir)
    if out.exists():
        unexpected = {p.name for p in out.iterdir()} - {'job.json', 'worker.log'}
        if unexpected:
            raise FileExistsError(f'Native output contains existing result files: {sorted(unexpected)}')
    else:
        out.mkdir(parents=True)
    start = time.monotonic()
    native, features, sources = _sources(source_dir)
    a = _assemble(prepared_dir, cohort, raw_screen_path)
    feature_manifest = {'fingerprints': features.FINGERPRINT_COLUMNS,
                        'descriptors': features.DESCRIPTOR_COLUMNS}
    S, D = features.build_tdi_features(a['registry'].canonical_smiles.tolist(), feature_manifest)
    identities = a['registry'].canonical_smiles.to_numpy(str)
    a['registry'].to_csv(out / 'native_registry.csv', index=False)
    a['dev'][['Molecule_Name', 'SMILES']].to_csv(out / 'oof_ids.csv', index=False)
    a['query'][['Molecule_Name', 'SMILES']].to_csv(out / 'query_ids.csv', index=False)
    np.save(out / 'native_train_labels.npy', a['labels'])
    np.save(out / 'oof_registry_map.npy', a['dev_map'])
    np.save(out / 'query_registry_map.npy', a['query_map'])
    metadata = {'cohort': cohort, 'native_revision': REVISION, 'sources': sources,
        'prepared_manifest_sha256': sha(Path(prepared_dir) / 'metadata.json'),
        'oof_ids_sha256': sha(out / 'oof_ids.csv'), 'query_ids_sha256': sha(out / 'query_ids.csv'),
        'screen_source': {'path': str(a['screen_path']), 'sha256': sha(a['screen_path'])},
        'native_registry_train_rows': a['n_train'], 'cohort_train_rows': len(a['dev']),
        'extra_registry_rows_minus_collapsed_duplicates': a['additional_native_registry_rows'],
        'query_rows': len(a['query']), 'screen_rows_used': a['screen_rows_used'],
        'target_order': list(TARGETS), 'structure_weights': native.STRUCTURE_WEIGHTS.tolist(),
        'partition_seeds': [0, 1, 2], 'repeats': 3, 'folds_per_repeat': 5,
        'query_labels_used': False, 'threshold_policy': 'native exact midpoint; highest threshold on MCC ties',
        'oof_score_role': 'same-OOF threshold calibration, not unbiased validation',
        'registry_policy': 'canonical isomeric identity union: direct then TDI then raw screen; outer exclusions propagated',
        'fidelity_limit': 'Published cached registry ordering/software may differ; original model/feature functions unchanged',
        'packages': {name: importlib.metadata.version(name) for name in ('numpy', 'pandas', 'lightgbm', 'scikit-learn', 'rdkit')}}
    write_json(out / 'metadata.json', metadata)
    def progress(model, record):
        state = {'state': 'running', 'completed_folds': len(model.models_), 'total_folds': 15,
                 'repeat': record['repeat'], 'fold': record['fold'], 'elapsed_seconds': time.monotonic() - start}
        write_json(out / 'status.json', state)
        print(json.dumps({'event': 'hauser_native_progress', 'cohort': cohort, **state}), flush=True)
    try:
        with threadpool_limits(limits=1):
            model = native.FinalTDI().fit(S, D, a['labels'], a['responses'], identities,
                                         a['n_train'], out / 'models', progress=progress)
        joblib.dump(model, out / 'final_tdi.joblib')
        np.save(out / 'native_folds.npy', model.folds_)
        np.save(out / 'native_oof_components.npy', model.oof_components_)
        np.save(out / 'native_query_components.npy', model.test_components_)
        oof = model.oof_scores_[a['dev_map']]
        query = model.test_scores_[a['query_map']]
        calls = query >= model.thresholds_
        np.save(out / 'oof_proba.npy', oof)
        np.save(out / 'query_proba.npy', query)
        np.save(out / 'query_hard.npy', calls)
        np.save(out / 'thresholds.npy', model.thresholds_)
        write_json(out / 'nativepolicy.json', {'kind': 'native_hauser_structure_screen',
            'target_order': list(TARGETS), 'thresholds': dict(zip(TARGETS, model.thresholds_.tolist())),
            'structure_weights': dict(zip(TARGETS, native.STRUCTURE_WEIGHTS.tolist())),
            'comparison': '>=', 'threshold_fit_ids': a['registry'].iloc[:a['n_train']].canonical_smiles.tolist(),
            'query_labels_used': False, 'source_revision': REVISION})
        native_metrics = score(a['labels'], model.oof_scores_ >= model.thresholds_)
        summary = {'thresholds': dict(zip(TARGETS, model.thresholds_.tolist())),
                   'native_calibration_metrics': native_metrics,
                   'query_positive_calls': calls.sum(axis=0).tolist(),
                   'elapsed_seconds': time.monotonic() - start}
        for filename, frame, values in [('oof_proba.csv', a['dev'], oof),
                                        ('query_proba.csv', a['query'], query),
                                        ('submission.csv', a['query'], calls)]:
            result = frame[['Molecule_Name', 'SMILES']].copy()
            for j, target in enumerate(TARGETS): result[target] = values[:, j]
            result.to_csv(out / filename, index=False)
        write_json(out / 'summary.json', summary)
        write_json(out / 'status.json', {'state': 'complete', 'completed_folds': 15, 'summary': summary})
        write_json(out / 'complete.json', {'status': 'complete', 'cohort': cohort,
            'files': {str(f.relative_to(out)): sha(f) for f in out.rglob('*') if f.is_file() and f.suffix != '.log'}})
        print(json.dumps({'event': 'hauser_native_complete', 'cohort': cohort, **summary}), flush=True)
        return summary
    except Exception as exc:
        write_json(out / 'failure.json', {'type': type(exc).__name__, 'elapsed_seconds': time.monotonic() - start})
        raise
