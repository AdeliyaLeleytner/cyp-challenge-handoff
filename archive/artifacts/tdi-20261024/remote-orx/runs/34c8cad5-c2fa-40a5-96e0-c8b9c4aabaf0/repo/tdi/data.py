"""Immutable TDI preparation; no training and no network access.

prepare(cfg) accepts assets as a directory containing official-tdi.csv,
official-train.csv, official-test.csv, cohorts.json, or an explicit path mapping
(tdi_train, direct_train, test, cohorts). Results go to output_dir/prepared.
All numerical arrays have accompanying immutable molecule-order tables.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, rdBase
from rdkit.Chem import Descriptors, rdFingerprintGenerator
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.ML.Cluster import Butina

TARGETS = ('CYP2D6_is_TDI', 'CYP3A4_is_TDI')
FP = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


@lru_cache(maxsize=100000)
def structure_keys(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f'Invalid input SMILES: {smiles}')
    connectivity = Chem.MolToInchiKey(mol).split('-')[0]
    parent = rdMolStandardize.Uncharger().uncharge(rdMolStandardize.FragmentParent(mol))
    Chem.RemoveStereochemistry(parent)
    return connectivity, Chem.MolToSmiles(parent, isomericSmiles=False)


def annotate(frame):
    frame = frame.copy().reset_index(drop=True)
    assert frame.Molecule_Name.notna().all() and not frame.Molecule_Name.duplicated().any()
    assert frame.SMILES.notna().all()
    keys = [structure_keys(s) for s in frame.SMILES]
    frame['parent_key'] = [k[0] for k in keys]
    frame['canonical_parent'] = [k[1] for k in keys]
    return frame


def encode_labels(frame):
    """Parse explicitly: bool('False') is True, so never use astype(bool) on strings."""
    y = np.full((len(frame), len(TARGETS)), np.nan, dtype=np.float64)
    accepted = {'true': 1., '1': 1., '1.0': 1., 'false': 0., '0': 0., '0.0': 0.}
    for j, col in enumerate(TARGETS):
        for i, value in enumerate(frame[col]):
            if pd.isna(value):
                continue
            key = str(value).strip().lower()
            if key not in accepted:
                raise ValueError(f'Invalid boolean label {col}, row {i}: {value!r}')
            y[i, j] = accepted[key]
    return y


def featurize(smiles):
    """Jeremy features in exact order, retaining float64 descriptor precision."""
    fps = np.zeros((len(smiles), 2048), dtype=np.uint8)
    descriptors = []
    for i, s in enumerate(smiles):
        mol = Chem.MolFromSmiles(s)
        if mol is None:
            raise ValueError('Invalid molecule during featurization')
        DataStructs.ConvertToNumpyArray(FP.GetFingerprint(mol), fps[i])
        descriptors.append(Descriptors.CalcMolDescriptors(mol))
    desc = pd.DataFrame(descriptors)
    features = pd.concat([pd.DataFrame(fps, columns=[f'ecfp4_{i}' for i in range(2048)]), desc], axis=1)
    return features.to_numpy(dtype=np.float64), list(features.columns)


HAUSER_DESCRIPTOR_COLUMNS = [
    "mw", "logp", "tpsa", "hbd", "hba", "rotb", "arom_rings", "heavy", "fsp3", "charge",
    "basic_amine", "acid_center", "aromatic_heterocycle", "halogen_count", "lipophilic_density", "surface_roughness",
]
HAUSER_FINGERPRINT_COLUMNS = ([f"maccs_{i}" for i in range(167)] + [f"tt_{i}" for i in range(1024)]
                              + [f"ap_{i}" for i in range(1024)] + [f"avalon_{i}" for i in range(1024)]
                              + [f"pat_{i}" for i in range(1024)])


def hauser_features(smiles):
    """Exact feature operations from HauserGroup commit06e1e1f training/tdi_features.py.

    Canonicalization before fingerprinting, float32 descriptor rounding before
    concatenation, and all16 physicochemical definitions match original source.
    """
    from rdkit.Avalon import pyAvalonTools
    from rdkit.Chem import MACCSkeys, rdMolDescriptors as D
    tt = rdFingerprintGenerator.GetTopologicalTorsionGenerator(fpSize=1024)
    ap = rdFingerprintGenerator.GetAtomPairGenerator(fpSize=1024)
    basic = Chem.MolFromSmarts("[#7;X3;!$(N-C=[O,S]);!$(N-S(=O)=O);!$(N=O)]")
    acid = Chem.MolFromSmarts("[CX3](=O)[OX2H1,OX1-]")
    hetero = Chem.MolFromSmarts("[a;!c]")
    halogen = Chem.MolFromSmarts("[F,Cl,Br,I]")
    rows, desc = [], []
    for value in smiles:
        mol = Chem.MolFromSmiles(value)
        if mol is None:
            raise ValueError(f'Invalid SMILES for Hauser features: {value!r}')
        mol = Chem.MolFromSmiles(Chem.MolToSmiles(mol, isomericSmiles=True))
        rows.append(np.concatenate([np.asarray(MACCSkeys.GenMACCSKeys(mol)), tt.GetFingerprintAsNumPy(mol),
                                    ap.GetFingerprintAsNumPy(mol), np.asarray(pyAvalonTools.GetAvalonFP(mol, 1024)),
                                    np.asarray(Chem.PatternFingerprint(mol, 1024))]))
        mw, logp, tpsa = float(D.CalcExactMolWt(mol)), float(D.CalcCrippenDescriptors(mol)[0]), float(D.CalcTPSA(mol))
        heavy = float(mol.GetNumHeavyAtoms())
        desc.append([mw, logp, tpsa, float(D.CalcNumHBD(mol)), float(D.CalcNumHBA(mol)),
                     float(D.CalcNumRotatableBonds(mol)), float(D.CalcNumAromaticRings(mol)), heavy,
                     float(D.CalcFractionCSP3(mol)), float(Chem.GetFormalCharge(mol)),
                     1.0 if mol.HasSubstructMatch(basic) else 0.0, 1.0 if mol.HasSubstructMatch(acid) else 0.0,
                     float(len(mol.GetSubstructMatches(hetero))), float(len(mol.GetSubstructMatches(halogen))),
                     logp / (mw / 100.0) if mw > 0 else 0.0, tpsa / (heavy + 1e-3)])
    descriptors = np.asarray(desc, dtype=np.float32)
    structure = np.column_stack([np.asarray(rows, dtype=np.float32), descriptors]).astype(np.float32)
    assert np.isfinite(structure).all() and structure.shape[1] == 4279 and descriptors.shape[1] == 16
    return structure, descriptors


def butina_clusters(smiles, cutoff=.6):
    """Exact Jeremy algorithm: original molecule order, Morgan R2/2048, no reorder."""
    fps = [FP.GetFingerprint(Chem.MolFromSmiles(s)) for s in smiles]
    dists = []
    for i in range(1, len(fps)):
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
        dists.extend(1 - s for s in sims)
    clusters = Butina.ClusterData(dists, len(fps), 1 - cutoff, isDistData=True)
    labels = np.empty(len(fps), dtype=int)
    for cid, members in enumerate(clusters):
        for member in members:
            labels[member] = cid
    return labels


def merge_identity_clusters(clusters, frame):
    """Union whole Butina clusters when chemical identity links two clusters."""
    parent = list(range(int(clusters.max()) + 1))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for col in ['parent_key', 'canonical_parent']:
        for indices in frame.groupby(col, sort=False).indices.values():
            roots = [find(int(clusters[i])) for i in indices]
            for root in roots[1:]:
                parent[find(root)] = find(roots[0])
    merged = np.array([find(int(c)) for c in clusters], dtype=int)
    # Preserve labels when unchanged, preserving native tie/order behavior.
    return merged


def assign_folds(clusters, seed=42, n_folds=5):
    rng = np.random.default_rng(seed)
    unique, counts = np.unique(clusters, return_counts=True)
    order = np.argsort(-counts)
    sizes = np.zeros(n_folds, dtype=int)
    mapping = {}
    for cid, count in zip(unique[order], counts[order]):
        fold = rng.choice(np.flatnonzero(sizes == sizes.min()))
        mapping[cid] = fold
        sizes[fold] += count
    return np.array([mapping[c] for c in clusters], dtype=int)


def label_counts(y):
    return {target: {'positive': int((y[:, j] == 1).sum()), 'negative': int((y[:, j] == 0).sum()),
                     'missing': int(np.isnan(y[:, j]).sum())} for j, target in enumerate(TARGETS)}


def _inputs(cfg):
    assets = cfg['assets']
    if isinstance(assets, dict):
        return {k: Path(v) for k, v in assets.items() if k not in ['source_files', 'aux_sources']}, assets
    assets = Path(assets)
    return {k: assets / v for k, v in {'tdi_train': 'official-tdi.csv', 'direct_train': 'official-train.csv',
                                      'test': 'official-test.csv', 'cohorts': 'cohorts.json'}.items()}, {}


def prepare(cfg):
    paths, extras = _inputs(cfg)
    out = Path(cfg['output_dir']) / 'prepared'
    out.mkdir(parents=True, exist_ok=True)
    originals = out / 'originals'
    originals.mkdir(exist_ok=True)
    provenance = {}
    for name in ['tdi_train', 'direct_train', 'test', 'cohorts']:
        path = paths[name]
        target = originals / f'{name}{path.suffix}'
        if target.exists() and sha(target) != sha(path):
            raise ValueError(f'Frozen input changed: {name}')
        if not target.exists():
            shutil.copyfile(path, target)
        provenance[name] = {'source': str(path.resolve()), 'sha256': sha(path), 'bytes': path.stat().st_size,
                            'copy': str(target.relative_to(out))}
    for name, path in extras.get('source_files', {}).items():
        path = Path(path)
        target = originals / ('source_' + name + path.suffix)
        if target.exists() and sha(target) != sha(path):
            raise ValueError(f'Frozen source changed: {name}')
        if not target.exists():
            shutil.copyfile(path, target)
        provenance['source_' + name] = {'source': str(path.resolve()), 'sha256': sha(path),
                                        'copy': str(target.relative_to(out))}
    for name, path in extras.get('aux_sources', {}).items():
        path = Path(path)
        target = originals / ('aux_' + name + path.suffix)
        if target.exists() and sha(target) != sha(path):
            raise ValueError(f'Frozen auxiliary input changed: {name}')
        if not target.exists():
            shutil.copyfile(path, target)
        provenance['aux_' + name] = {'source': str(path.resolve()), 'sha256': sha(path),
                                     'copy': str(target.relative_to(out))}
    train = annotate(pd.read_csv(paths['tdi_train']))
    direct = annotate(pd.read_csv(paths['direct_train']))
    test = annotate(pd.read_csv(paths['test']))
    assert len(train) == 6145 and len(test) == 750
    for key in ['parent_key', 'canonical_parent']:
        assert not set(train[key]) & set(test[key]), f'Train-test identity overlap: {key}'
    overlap_ids = set(train.Molecule_Name) & set(direct.Molecule_Name)
    train_keys = train.set_index('Molecule_Name').loc[sorted(overlap_ids), 'parent_key']
    direct_keys = direct.set_index('Molecule_Name').loc[sorted(overlap_ids), 'parent_key']
    assert train_keys.equals(direct_keys), 'A molecule ID changes structure between official tables'
    y = encode_labels(train)
    train.to_csv(out / 'train.csv', index=False)
    direct.to_csv(out / 'direct_train.csv', index=False)
    test.to_csv(out / 'test.csv', index=False)
    train[['Molecule_Name', 'SMILES', 'parent_key', 'canonical_parent']].to_csv(out / 'train_ids.csv', index=False)
    test[['Molecule_Name', 'SMILES', 'parent_key', 'canonical_parent']].to_csv(out / 'test_ids.csv', index=False)
    np.save(out / 'y_train.npy', y)
    np.save(out / 'label_mask.npy', ~np.isnan(y))
    X, columns = featurize(train.SMILES.tolist())
    Xt, test_columns = featurize(test.SMILES.tolist())
    assert columns == test_columns and X.shape[0] == len(train) and Xt.shape[0] == len(test)
    np.save(out / 'X_train.npy', X)
    np.save(out / 'X_test.npy', Xt)
    # Explicit data/ID alignment read-back checks, including selected recomputations.
    assert pd.read_csv(out / 'test_ids.csv').Molecule_Name.tolist() == test.Molecule_Name.tolist()
    for index in [0, len(test) // 2, len(test) - 1]:
        check, cols = featurize([test.SMILES.iloc[index]])
        assert columns == cols and np.array_equal(check[0], Xt[index], equal_nan=True)
    write_json(out / 'feature_columns.json', columns)
    for name, frame in [('train', train), ('test', test)]:
        structure, descriptors = hauser_features(frame.SMILES.tolist())
        assert len(structure) == len(frame)
        np.save(out / f'X_hauser_{name}.npy', structure)
        np.save(out / f'X_desc16_{name}.npy', descriptors)
        for index in [0, len(frame) - 1]:
            check, dcheck = hauser_features([frame.SMILES.iloc[index]])
            assert np.array_equal(check[0], structure[index]) and np.array_equal(dcheck[0], descriptors[index])
    write_json(out / 'hauser_feature_columns.json', {'fingerprints': HAUSER_FINGERPRINT_COLUMNS,
                                                   'descriptors': HAUSER_DESCRIPTOR_COLUMNS})
    full_clusters = butina_clusters(train.SMILES.tolist())
    native_folds = assign_folds(full_clusters)
    np.save(out / 'clusters_native.npy', full_clusters)
    np.save(out / 'folds_native.npy', native_folds)
    for seed in cfg.get('seeds', [42, 142]):
        np.save(out / f'folds_native_seed{seed}.npy', assign_folds(full_clusters, int(seed)))
    full_dir = out / 'cohorts' / 'full'
    full_dir.mkdir(parents=True, exist_ok=True)
    np.save(full_dir / 'train_indices.npy', np.arange(len(train), dtype=int))
    np.save(full_dir / 'query_indices.npy', np.arange(len(test), dtype=int))
    train[['Molecule_Name', 'SMILES']].to_csv(full_dir / 'train_ids.csv', index=False)
    test[['Molecule_Name', 'SMILES']].to_csv(full_dir / 'query_ids.csv', index=False)
    strict_full_clusters = merge_identity_clusters(full_clusters, train)
    np.save(full_dir / 'clusters.npy', strict_full_clusters)
    for seed in cfg.get('seeds', [42, 142]):
        np.save(full_dir / f'folds_seed{seed}.npy', assign_folds(strict_full_clusters, int(seed)))
    write_json(full_dir / 'metadata.json', {'train_rows': len(train), 'query_rows': len(test),
                                           'query_table': '../../test.csv', 'query_matrix': '../../X_test.npy',
                                           'labels': label_counts(y)})
    # Optional independent comparison to the frozen vendored algorithm.
    if paths.get('jeremy_splits'):
        spec = importlib.util.spec_from_file_location('frozen_jeremy_splits', paths['jeremy_splits'])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert np.array_equal(module.butina_kfold(train.SMILES.tolist()), native_folds)
    cohort_info = {}
    frozen = json.loads(paths['cohorts'].read_text())['cohorts']
    id_to_row = {name: i for i, name in enumerate(train.Molecule_Name)}
    direct_ids = set(direct.Molecule_Name)
    for name in ['own750', 'briford529']:
        cohort = frozen[name]
        ids = cohort['test_ids']
        actual_holdout_sha = hashlib.sha256('\n'.join(ids).encode()).hexdigest()
        expected_holdout_sha = {
            'own750': 'befcfc0f85f8a4920afae21a01a0ce0242d5e7e3c5d96a98aca5114d74517504',
            'briford529': 'f5b99359b0752a485b2123a87777fb09b7b3b8b8db60052e63d5468439de2a08',
        }[name]
        assert actual_holdout_sha == cohort['test_id_sha256'] == expected_holdout_sha, 'Frozen holdout ID order changed'
        assert len(ids) == (750 if name == 'own750' else 529)
        held_indices = np.array([id_to_row[x] for x in ids], dtype=int)
        held = train.iloc[held_indices]
        excluded_ids = set(ids) | set(cohort.get('outer_parent_purged_ids', []))
        exclusion = train[train.Molecule_Name.isin(excluded_ids)]
        keep = ~train.Molecule_Name.isin(excluded_ids).to_numpy()
        for key in ['parent_key', 'canonical_parent']:
            keep &= ~train[key].isin(set(exclusion[key])).to_numpy()
        # Original regression development identities stay frozen; TDI-only rows can join.
        keep &= (~train.Molecule_Name.isin(direct_ids - set(cohort['train_ids']))).to_numpy()
        dev_indices = np.flatnonzero(keep)
        dev = train.iloc[dev_indices].reset_index(drop=True)
        for key in ['parent_key', 'canonical_parent']:
            assert not set(dev[key]) & set(held[key]), f'{name}: heldout identity leakage'
        dest = out / 'cohorts' / name
        dest.mkdir(parents=True, exist_ok=True)
        np.save(dest / 'train_indices.npy', dev_indices)
        np.save(dest / 'holdout_indices.npy', held_indices)
        dev[['Molecule_Name', 'SMILES']].to_csv(dest / 'train_ids.csv', index=False)
        held[['Molecule_Name', 'SMILES']].to_csv(dest / 'holdout_ids.csv', index=False)
        clusters = merge_identity_clusters(butina_clusters(dev.SMILES.tolist()), dev)
        np.save(dest / 'clusters.npy', clusters)
        fold_info = {}
        for seed in cfg.get('seeds', [42, 142]):
            folds = assign_folds(clusters, int(seed))
            for key in ['parent_key', 'canonical_parent']:
                grouped = pd.DataFrame({'key': dev[key], 'fold': folds}).groupby('key')['fold'].nunique()
                assert grouped.max() == 1, f'{name}: duplicate identity crosses folds'
            np.save(dest / f'folds_seed{seed}.npy', folds)
            fold_info[str(seed)] = {str(f): label_counts(y[dev_indices[folds == f]]) for f in range(5)}
        # Auxiliary tables are purged before exporting, never use query assay measurements.
        auxiliary = {'direct_train': direct}
        for aux_name, aux_path in extras.get('aux_sources', {}).items():
            auxiliary[aux_name] = annotate(pd.read_csv(aux_path))
        aux_info = {}
        for aux_name, frame in auxiliary.items():
            valid = ~frame.Molecule_Name.isin(excluded_ids)
            for key in ['parent_key', 'canonical_parent']:
                valid &= ~frame[key].isin(set(exclusion[key]))
                valid &= ~frame[key].isin(set(test[key]))
            purged = frame.loc[valid].reset_index(drop=True)
            for key in ['parent_key', 'canonical_parent']:
                assert not set(purged[key]) & set(held[key])
            purged.to_csv(dest / f'aux_{aux_name}.csv', index=False)
            aux_info[aux_name] = {'retained': len(purged), 'removed': len(frame) - len(purged)}
        cohort_info[name] = {'train_rows': len(dev), 'holdout_rows': len(held),
                              'heldout_ids_original_order': ids, 'original_test_id_sha256': cohort['test_id_sha256'],
                              'train_labels': label_counts(y[dev_indices]), 'holdout_labels': label_counts(y[held_indices]),
                              'folds': fold_info, 'auxiliary': aux_info, 'identity_overlap': 0}
        write_json(dest / 'metadata.json', cohort_info[name])
    metadata = {'inputs': provenance, 'targets': list(TARGETS), 'train_rows': len(train), 'test_rows': len(test),
                'label_counts': label_counts(y), 'rdkit_version': rdBase.rdkitVersion,
                'numpy_version': np.__version__, 'pandas_version': pd.__version__,
                'feature_shape': list(X.shape), 'test_feature_shape': list(Xt.shape),
                'feature_columns': columns, 'descriptor_columns': columns[2048:],
                'hauser_feature_columns': HAUSER_FINGERPRINT_COLUMNS + HAUSER_DESCRIPTOR_COLUMNS,
                'hauser_descriptor_columns': HAUSER_DESCRIPTOR_COLUMNS,
                'train_nan_features': int(np.isnan(X).sum()), 'train_inf_features': int(np.isinf(X).sum()),
                'feature_policy': 'Raw Jeremy ECFP4+RDKit2D float64; do not globally impute strict variants',
                'cohorts': cohort_info, 'test_alignment_verified': True, 'train_test_parent_overlap': 0,
                'output_files': {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
                                 if p.is_file() and p != out / 'metadata.json'}}
    write_json(out / 'metadata.json', metadata)
    print(json.dumps({'stage': 'prepared', 'path': str(out), 'train_rows': len(train), 'test_rows': len(test),
                      'labels': label_counts(y), 'cohorts': {k: v['train_rows'] for k, v in cohort_info.items()}}, allow_nan=False), flush=True)
    return metadata
