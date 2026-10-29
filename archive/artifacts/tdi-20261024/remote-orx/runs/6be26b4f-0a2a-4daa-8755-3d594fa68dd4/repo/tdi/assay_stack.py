"""Conditional E5: cached six predicted assay endpoints, CYP2D6 only.

No observed assay values are read into features. Native base OOF folds differ
from TDI folds: downstream inner CV is not a fully nested stacking evaluation.
Independent query predictions use matching outer-purged native regressors.
"""
from __future__ import annotations

from pathlib import Path
import gc
import hashlib
import json
import os
import time

import numpy as np
import pandas as pd

PRED_COLUMNS = [
    'cyp2d6_pic50_direct_inhibition_pred', 'cyp2d6_log2fc_pred',
    'cyp2d6_pic50_tdi_condition_pred', 'cyp2d6_emax_vs_pos_ctrl_direct_inhibition_pred',
    'cyp2d6_pic50_chembl_pred', 'cyp2d6_max_response_pred',
]
ALIASES = {
    'own750': ['OCNT-0494161', 'OCNT-1911794', 'OCNT-1965934', 'OCNT-2328651', 'OCNT-2328781', 'OCNT-2328911'],
    'briford529': ['OCNT-1965934', 'OCNT-2328651'],
    'full': ['OCNT-0494161', 'OCNT-1911794'],
}
PARAMS = dict(n_estimators=500, learning_rate=.05, num_leaves=31, subsample=.8,
              colsample_bytree=.8, class_weight='balanced', verbose=-1)
LIMITS = [
    'Native regression OOF folds differ from TDI folds; inner stacking CV is not strictly nested.',
    'Native regressors used validation-assay values for early stopping; OOF is not a completely untouched assay evaluation.',
    'Full isoform6 contains public Veith structure overlapping test OCNT-0496981; matching outer models have zero query overlap.',
    'CYP3A4 is copied exactly from native_seed42 baseline; only CYP2D6 changes.',
    'Unknown or excluded development labels never enter fitting/calibration; baseline probabilities only fill aligned output rows.',
]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    os.replace(temp, path)


def _binary_frame(path, ids):
    frame = pd.read_csv(path)
    if frame.Molecule_Name.tolist() != list(ids):
        raise ValueError(f'Baseline query ID order mismatch: {path}')
    cols = ['CYP2D6_is_TDI', 'CYP3A4_is_TDI']
    allowed = {'true': True, 'false': False, '1': True, '0': False, '1.0': True, '0.0': False}
    result = np.empty((len(frame), 2), dtype=bool)
    for j, name in enumerate(cols):
        values = frame[name].astype(str).str.lower().map(allowed)
        if values.isna().any():
            raise ValueError('Invalid baseline binary prediction')
        result[:, j] = values.to_numpy(dtype=bool)
    return result


def _baseline(base, cohort, dev_ids, query_ids):
    from tdi.evaluation import apply_policy
    folder = base / 'evaluation' / cohort
    policy_path = folder / 'native_seed42_policy.json'
    policy = json.loads(policy_path.read_text())
    if policy['selection_input']['ids'] != list(dev_ids):
        raise ValueError('Baseline policy training ID order differs from current development IDs')
    library, sources = {}, {str(policy_path): sha(policy_path)}
    for name in policy['models']:
        values = []
        for target in range(2):
            path = base / 'results' / cohort / 'seed42' / name / f'target{target}' / 'predictions.npz'
            with np.load(path) as data:
                if len(data['hard_oof']) != len(dev_ids):
                    raise ValueError('Baseline OOF shape mismatch')
                values.append(data['hard_oof'].copy())
            sources[str(path)] = sha(path)
        library[name] = np.column_stack(values)
    oof = apply_policy(library, policy, return_probabilities=True)
    query_path = folder / 'native_seed42_predictions.csv'
    query = _binary_frame(query_path, query_ids)
    sources[str(query_path)] = sha(query_path)
    return oof, query, sources


def _native_features(source, dev_frame, query_frame, cohort):
    """Required keys: oof, query, prepared_csv, prepared_spec; optional provenance_refs."""
    from tdi.data import structure_keys
    paths = {name: Path(source[name]) for name in ['oof', 'query', 'prepared_csv', 'prepared_spec']}
    # Deliberately load only prediction columns. Merged OOF also contains observed assays.
    oof = pd.read_csv(paths['oof'], usecols=['molecule_name'] + PRED_COLUMNS)
    query = pd.read_csv(paths['query'], usecols=['molecule_name'] + PRED_COLUMNS)
    native = pd.read_csv(paths['prepared_csv'], usecols=['molecule_name', 'smiles'])
    spec = json.loads(paths['prepared_spec'].read_text())
    if sha(paths['prepared_csv']) != spec['data_sha256']:
        raise ValueError('Native input pool differs from saved fold specification')
    if oof.molecule_name.duplicated().any() or set(oof.molecule_name) != set(native.molecule_name):
        raise ValueError('Native OOF must cover each original pool row exactly once')
    if query.molecule_name.duplicated().any() or set(query.molecule_name) != set(query_frame.Molecule_Name):
        raise ValueError('Native outer query predictions differ from frozen query IDs')
    keys = [structure_keys(s) for s in native.smiles]
    connectivity, parents = {k[0] for k in keys}, {k[1] for k in keys}
    overlap = query_frame[query_frame.parent_key.isin(connectivity) | query_frame.canonical_parent.isin(parents)]
    expected_overlap = {'OCNT-0496981'} if cohort == 'full' else set()
    if set(overlap.Molecule_Name) != expected_overlap:
        raise ValueError('Unexpected native base-model/query structural overlap')
    contaminated = set()
    dev_ids = set(dev_frame.Molecule_Name)
    val_members = []
    for split in spec['folds']:
        fit = [keys[i] for i in split['train']]
        cp, pa = {k[0] for k in fit}, {k[1] for k in fit}
        for i in split['validation']:
            val_members.append(native.molecule_name.iloc[i])
            if native.molecule_name.iloc[i] in dev_ids and (keys[i][0] in cp or keys[i][1] in pa):
                contaminated.add(native.molecule_name.iloc[i])
    if sorted(val_members) != sorted(native.molecule_name.tolist()):
        raise ValueError('Native fold validation assignments do not partition the source pool')
    affected = dev_frame[dev_frame.Molecule_Name.isin(contaminated)]
    excluded = dev_frame[dev_frame.parent_key.isin(affected.parent_key) |
                         dev_frame.canonical_parent.isin(affected.canonical_parent)]
    if set(excluded.Molecule_Name) != set(ALIASES[cohort]):
        raise ValueError('Identity-alias exclusions differ from predeclared audit')
    aligned = oof.set_index('molecule_name').reindex(dev_frame.Molecule_Name)[PRED_COLUMNS].to_numpy(dtype=float)
    Q = query.set_index('molecule_name').loc[query_frame.Molecule_Name, PRED_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(Q).all():
        raise ValueError('Native query predictions contain missing/nonfinite entries')
    # Missing OOF availability is not fed to a learner; only complete known rows are eligible.
    provenance = {name: {'path': str(path), 'sha256': sha(path)} for name, path in paths.items()}
    for i, path in enumerate(source.get('provenance_refs', [])):
        path = Path(path)
        provenance[f'upstream_ref_{i}'] = {'path': str(path), 'sha256': sha(path)}
    return aligned, Q, provenance, overlap.Molecule_Name.tolist()


def _folds(prepared, cohort, seed, n):
    path = prepared / f'folds_native_seed{seed}.npy' if cohort == 'full' else prepared / 'cohorts' / cohort / f'folds_seed{seed}.npy'
    values = np.load(path)
    if values.shape != (n,) or set(values.tolist()) != set(range(5)):
        raise ValueError('Five frozen folds must align with development rows')
    return values, path


def run_assay_stack(config):
    """Run only when activated through a committed ORX snapshot; never submits.

    config: prepared_dir, base_results, output_dir, seeds=[42,142],
    native_regression_sources={cohort: {oof,query,prepared_csv,prepared_spec,
                                      provenance_refs:[manifest/complete paths]}}.
    All paths should reference staged local/remote assets, not live services.
    """
    from lightgbm import LGBMClassifier
    from tdi.evaluation import optimize_threshold, score
    import joblib
    import importlib.metadata
    prepared, base, out = (Path(config[name]).resolve() for name in ['prepared_dir', 'base_results', 'output_dir'])
    seeds = config.get('seeds', [42, 142])
    if list(seeds) != [42, 142]:
        raise ValueError('E5 seed set is frozen to42/142')
    out.mkdir(parents=True, exist_ok=True)
    train, test = pd.read_csv(prepared / 'train.csv'), pd.read_csv(prepared / 'test.csv')
    labels = np.load(prepared / 'y_train.npy')
    structural = np.load(prepared / 'X_train.npy', mmap_mode='r')
    structural_test = np.load(prepared / 'X_test.npy', mmap_mode='r')
    summary = {}
    for cohort in ['own750', 'briford529', 'full']:
        folder = prepared / 'cohorts' / cohort
        dev = np.load(folder / 'train_indices.npy')
        qi = np.load(folder / ('query_indices.npy' if cohort == 'full' else 'holdout_indices.npy'))
        dev_frame = train.iloc[dev].reset_index(drop=True)
        query_frame = (test if cohort == 'full' else train).iloc[qi].reset_index(drop=True)
        for key in ['Molecule_Name', 'parent_key', 'canonical_parent']:
            if set(dev_frame[key]) & set(query_frame[key]):
                raise ValueError('Development/query identities overlap')
        baseline_oof, baseline_query, baseline_hashes = _baseline(base, cohort, dev_frame.Molecule_Name, query_frame.Molecule_Name)
        pred, query_pred, source_hashes, public_overlap = _native_features(config['native_regression_sources'][cohort], dev_frame, query_frame, cohort)
        known = np.isfinite(labels[dev, 0])
        if not np.isfinite(pred[known]).all():
            raise ValueError('A known CYP2D6 label has no complete native OOF prediction')
        retain = known & ~dev_frame.Molecule_Name.isin(ALIASES[cohort]).to_numpy()
        if np.any(~np.isfinite(pred[retain])):
            raise ValueError('Incomplete assay feature pairs cannot enter fitting')
        # No origin indicator, label availability, observed pIC50/CI or fold ID is a feature.
        X = np.column_stack([structural[dev], pred, pred[:, 2] - pred[:, 0]])
        query_structure = structural_test[qi] if cohort == 'full' else structural[qi]
        Q = np.column_stack([query_structure, query_pred, query_pred[:, 2] - query_pred[:, 0]])
        d = out / cohort
        d.mkdir(exist_ok=True)
        dev_frame[['Molecule_Name', 'SMILES']].to_csv(d / 'oof_ids.csv', index=False)
        query_frame[['Molecule_Name', 'SMILES']].to_csv(d / 'query_ids.csv', index=False)
        np.save(d / 'selection_mask.npy', retain)
        np.save(d / 'fallback_mask.npy', ~retain)
        write_json(d / 'frozen_design.json', {'params': PARAMS, 'seeds': seeds, 'feature_columns': PRED_COLUMNS + ['predicted_TDI_minus_direct'],
                                            'structural_columns': json.loads((prepared / 'feature_columns.json').read_text()),
                                            'candidate_methods': ['assay_logistic', 'struct_assay_lgbm'],
                                            'logistic_params': {'C': 1.0, 'class_weight': 'balanced', 'max_iter': 2000, 'preprocess': 'fold-only median+standard scaler'},
                                            'method_selection': 'highest pooled OOF MCC after fivefold crossfit thresholds; ties prefer logistic',
                                            'excluded_alias_ids': ALIASES[cohort], 'known_rows': int(known.sum()),
                                            'retained_rows': int(retain.sum()), 'baseline_hashes': baseline_hashes,
                                            'source_hashes': source_hashes, 'public_query_overlap': public_overlap,
                                            'limitations': LIMITS, 'prepared_metadata_sha256': sha(prepared / 'metadata.json'),
                                            'implementation_sha256': sha(__file__)})
        methods = {}
        assay_X = np.column_stack([pred, pred[:, 2] - pred[:, 0]])
        assay_Q = np.column_stack([query_pred, query_pred[:, 2] - query_pred[:, 0]])
        for method in ['assay_logistic', 'struct_assay_lgbm']:
            features, query_features = (assay_X, assay_Q) if method == 'assay_logistic' else (X, Q)
            seed_oof, seed_query = [], []
            for seed in seeds:
                folds, folds_path = _folds(prepared, cohort, seed, len(dev))
                sd = d / method / f'seed{seed}'
                sd.mkdir(parents=True, exist_ok=True)
                oof = baseline_oof[:, 0].copy()
                predictions = []
                def new_model():
                    if method == 'struct_assay_lgbm':
                        return LGBMClassifier(**PARAMS, random_state=int(seed), n_jobs=int(config.get('n_jobs', 4)))
                    from sklearn.pipeline import make_pipeline
                    from sklearn.impute import SimpleImputer
                    from sklearn.preprocessing import StandardScaler
                    from sklearn.linear_model import LogisticRegression
                    return make_pipeline(SimpleImputer(strategy='median'), StandardScaler(),
                                         LogisticRegression(C=1., class_weight='balanced', max_iter=2000,
                                                            random_state=int(seed)))
                for f in range(5):
                    fit_mask, valid_mask = retain & (folds != f), retain & (folds == f)
                    if len(np.unique(labels[dev[fit_mask], 0])) != 2 or not valid_mask.any():
                        raise ValueError('Invalid labeled fold for two-class fitting')
                    model = new_model()
                    model.fit(features[fit_mask], labels[dev[fit_mask], 0].astype(int))
                    positive_column = int(np.flatnonzero(model.classes_ == 1)[0])
                    oof[valid_mask] = model.predict_proba(features[valid_mask])[:, positive_column]
                    qp = model.predict_proba(query_features)[:, positive_column]
                    predictions.append(qp)
                    np.savez_compressed(sd / f'fold{f}.npz', valid_positions=np.flatnonzero(valid_mask),
                                        valid_proba=oof[valid_mask], query_proba=qp)
                    joblib.dump(model, sd / f'fold{f}.joblib', compress=3)
                    del model
                    gc.collect()
                # Archive full fit; deployment continues to use fivefold mean predictions.
                full = new_model()
                full.fit(features[retain], labels[dev[retain], 0].astype(int))
                joblib.dump(full, sd / 'full_model.joblib', compress=3)
                np.save(sd / 'full_query_diagnostic.npy', full.predict_proba(query_features)[:, int(np.flatnonzero(full.classes_ == 1)[0])])
                bag = np.mean(predictions, axis=0)
                np.savez_compressed(sd / 'predictions.npz', oof=oof, query_bag=bag, selection_mask=retain)
                write_json(sd / 'metadata.json', {'folds_sha256': sha(folds_path), 'seed': seed,
                                                 'method': method, 'full_refit_used_for_deployment': False})
                seed_oof.append(oof)
                seed_query.append(bag)
                del full
            methods[method] = {'oof': np.mean(seed_oof, axis=0), 'query': np.mean(seed_query, axis=0)}
        # Method selection uses training-side OOF only; threshold for each held fold
        # is fit on other folds. This does not repair the upstream nesting limit.
        from sklearn.metrics import matthews_corrcoef
        selection_folds, _ = _folds(prepared, cohort, 42, len(dev))
        diagnostics = {}
        selected, selected_score = None, -float('inf')
        for method, values in methods.items():
            crossfit = np.zeros(len(dev), dtype=bool)
            thresholds_by_fold = {}
            for f in range(5):
                fit_mask, valid_mask = retain & (selection_folds != f), retain & (selection_folds == f)
                chosen = optimize_threshold(labels[dev[fit_mask], 0], values['oof'][fit_mask], exact=False)
                thresholds_by_fold[str(f)] = chosen['threshold']
                crossfit[valid_mask] = values['oof'][valid_mask] >= chosen['threshold']
            mcc = float(matthews_corrcoef(labels[dev[retain], 0], crossfit[retain]))
            diagnostics[method] = {'crossfit_threshold_mcc': mcc, 'thresholds_by_fold': thresholds_by_fold,
                                   'retained_rows': int(retain.sum())}
            np.save(d / method / 'crossfit_classes.npy', crossfit)
            if mcc > selected_score:
                selected, selected_score = method, mcc
        oof_mean, query_mean = methods[selected]['oof'], methods[selected]['query']
        threshold = optimize_threshold(labels[dev[retain], 0], oof_mean[retain], exact=False)
        write_json(d / 'method-selection.json', {'selected': selected, 'diagnostics': diagnostics,
                                                'selection_label_scope': 'retained development only',
                                                'upstream_inner_cv_is_strictly_nested': False})
        # CYP3A4 is exactly the baseline binary class; .5 merely reproduces it.
        combined = np.column_stack([query_mean >= threshold['threshold'], baseline_query[:, 1]])
        assert np.array_equal(combined[:, 1], baseline_query[:, 1])
        probabilities = np.column_stack([query_mean, baseline_query[:, 1].astype(float)])
        frame = query_frame[['SMILES', 'Molecule_Name']].copy()
        frame['CYP2D6_is_TDI'], frame['CYP3A4_is_TDI'] = combined[:, 0], combined[:, 1]
        frame.to_csv(d / 'predictions.csv', index=False)
        np.save(d / 'probabilities.npy', probabilities)
        np.save(d / 'oof_probabilities.npy', np.column_stack([oof_mean, baseline_oof[:, 1]]))
        policy = {'CYP2D6_method': selected, 'training_method_selection': diagnostics, 'CYP2D6': threshold, 'CYP3A4_threshold': .5,
                  'CYP3A4_source': 'native_seed42 baseline hard classes, copied unchanged',
                  'selection_ids': dev_frame.Molecule_Name[retain].tolist(),
                  'fallback_ids_excluded_from_selection': dev_frame.Molecule_Name[~retain].tolist(),
                  'outer_labels_used_for_fitting_or_threshold': False}
        write_json(d / 'policy.json', policy)
        # Lock all candidate choices and query predictions before accessing outer labels.
        write_json(d / 'prediction-lock.json', {'policy_sha256': sha(d / 'policy.json'),
                                               'predictions_sha256': sha(d / 'predictions.csv'),
                                               'design_sha256': sha(d / 'frozen_design.json'),
                                               'method_selection_sha256': sha(d / 'method-selection.json'),
                                               'query_ids': query_frame.Molecule_Name.tolist()})
        result = {'selected_method': selected, 'development_method_selection': diagnostics,
                  'development_2d6_threshold_score': threshold, 'retained_training_rows': int(retain.sum()),
                  'same_label_mask_used_for_fitting_and_calibration': True, 'limitations': LIMITS}
        if cohort != 'full':
            candidate = score(labels[qi], combined, query_frame.Molecule_Name.tolist())
            references = {}
            for name in ['native_seed42', 'native_reference', 'hauser_native']:
                path = base / 'evaluation' / cohort / f'{name}_predictions.csv'
                if not path.exists():
                    raise ValueError(f'Missing required native comparator: {path}')
                prediction = _binary_frame(path, query_frame.Molecule_Name)
                references[name] = score(labels[qi], prediction, query_frame.Molecule_Name.tolist())
            best = max(references, key=lambda key: references[key]['macro_mcc'])
            result.update(holdout=candidate, native_baselines=references, strongest_native=best,
                          delta_vs_strongest_native=candidate['macro_mcc'] - references[best]['macro_mcc'])
        else:
            if len(frame) != 750 or frame.Molecule_Name.tolist() != test.Molecule_Name.tolist():
                raise ValueError('Final submission must preserve all750 official test rows')
            frame.to_csv(out / 'submission_tdi.csv', index=False)
        write_json(d / 'summary.json', result)
        summary[cohort] = result
    qualified = all(summary[c]['delta_vs_strongest_native'] > 0 for c in ['own750', 'briford529'])
    record = {'cohorts': summary, 'qualified_on_both_holdouts': qualified,
              'submission_sha256': sha(out / 'submission_tdi.csv'), 'sent': False,
              'packages': {name: importlib.metadata.version(name) for name in ['lightgbm', 'numpy', 'scikit-learn']}}
    write_json(out / 'summary.json', record)
    write_json(out / 'complete.json', {'status': 'complete', 'summary_sha256': sha(out / 'summary.json')})
    return record
