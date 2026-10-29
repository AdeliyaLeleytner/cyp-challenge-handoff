"""Deterministic, ID-aligned molecular features for the preregistered night run.

No learned transform belongs here. Precomputed assets are verified before use;
missing IDs and invalid structures are never silently dropped. Optional encoders
must be staged by the orchestrator; this module never downloads model weights.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
import pandas as pd
from rdkit import Chem, rdBase
from rdkit.Chem import Descriptors, rdFingerprintGenerator

_HASH_CACHE: dict[tuple[str, int, int], str] = {}
_PRIMARY_COLUMNS = [f'{c}_pIC50_direct_inhibition' for c in ('CYP1A2','CYP2C9','CYP2D6','CYP3A4')]


def molecule_ids(frame: pd.DataFrame) -> list[str]:
    if 'Molecule_Name' not in frame:
        raise ValueError('Molecule_Name is required for feature alignment')
    if frame.Molecule_Name.isna().any():
        raise ValueError('Molecule_Name contains missing IDs')
    ids = frame.Molecule_Name.astype(str).tolist()
    if len(set(ids)) != len(ids):
        raise ValueError('Molecule_Name must be unique within one feature request')
    return ids


def _path(value: str | Path, asset_root: Path) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else Path(asset_root) / p


def verified_file(value: str | Path, expected_sha256: str, asset_root: Path) -> Path:
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ValueError(f'A pinned SHA-256 is required for asset {value}')
    p = _path(value, asset_root)
    if not p.is_file():
        raise FileNotFoundError(f'Staged asset missing: {p}; implicit downloads are disabled')
    stat = p.stat()
    key = (str(p.resolve()), stat.st_size, stat.st_mtime_ns)
    actual = _HASH_CACHE.get(key)
    if actual is None:
        h = hashlib.sha256()
        with p.open('rb') as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                h.update(chunk)
        actual = _HASH_CACHE[key] = h.hexdigest()
    if actual.lower() != expected_sha256.lower():
        raise ValueError(f'SHA-256 mismatch for {p}: expected {expected_sha256}, got {actual}')
    return p


def _asset_record(config: dict, asset_root: Path) -> dict:
    if isinstance(config.get('asset'), dict):
        return dict(config['asset'])
    if 'matrix_path' in config:
        return dict(config)
    key = config.get('asset_key')
    if not key:
        raise ValueError('Precomputed features require asset_key or an explicit asset record')
    manifest_path = _path(config.get('manifest_path', 'feature_manifest.json'), asset_root)
    manifest = json.loads(manifest_path.read_text())
    assets = manifest.get('features', manifest)
    if key not in assets:
        raise KeyError(f'Feature asset {key!r} is absent from {manifest_path}')
    return dict(assets[key])


def _precomputed(frame: pd.DataFrame, asset_root: Path, config: dict):
    ids = molecule_ids(frame)
    record = _asset_record(config, asset_root)
    matrix_path = verified_file(record['matrix_path'], record.get('sha256') or record.get('matrix_sha256'), asset_root)
    ids_path = verified_file(record['ids_path'], record['ids_sha256'], asset_root)
    if ids_path.suffix.lower() == '.json':
        source_ids = json.loads(ids_path.read_text())
        if isinstance(source_ids, dict):
            source_ids = source_ids[record.get('id_column', 'Molecule_Name')]
    elif ids_path.suffix.lower() == '.npy':
        source_ids = np.load(ids_path, allow_pickle=False).tolist()
    else:
        id_column = record.get('id_column', 'Molecule_Name')
        source_ids = pd.read_csv(ids_path, usecols=[id_column], dtype={id_column: str})[id_column].tolist()
    if any(pd.isna(v) for v in source_ids):
        raise ValueError(f'Missing source IDs in {ids_path}')
    source_ids = [str(v) for v in source_ids]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError(f'Duplicate source IDs in {ids_path}')
    matrix = np.load(matrix_path, mmap_mode='r', allow_pickle=False)
    if matrix.ndim != 2 or matrix.shape[0] != len(source_ids):
        raise ValueError(f'Feature/ID shape mismatch: {matrix.shape}, {len(source_ids)} IDs')
    lookup = {v: i for i, v in enumerate(source_ids)}
    missing = [v for v in ids if v not in lookup]
    if missing:
        raise ValueError(f'{len(missing)} requested IDs absent from feature asset; examples: {missing[:8]}')
    X = np.asarray(matrix[[lookup[v] for v in ids]], dtype=np.float32)
    names = record.get('columns') or [f"{config.get('asset_key', 'embedding')}_{i}" for i in range(X.shape[1])]
    if len(names) != X.shape[1] or len(set(names)) != len(names):
        raise ValueError('Precomputed feature columns must be unique and match matrix width')
    nonfinite = ~np.isfinite(X)
    if nonfinite.any() and config.get('nonfinite_policy', record.get('nonfinite_policy', 'raise')) == 'raise':
        bad = np.flatnonzero(nonfinite.any(axis=1))
        raise ValueError(f'Nonfinite precomputed features for IDs {[ids[i] for i in bad[:8]]}')
    X[nonfinite] = np.nan
    return X, list(names), {
        'family': 'precomputed', 'asset_key': config.get('asset_key'),
        'matrix_path': str(matrix_path), 'matrix_sha256': record.get('sha256') or record.get('matrix_sha256'),
        'ids_path': str(ids_path), 'ids_sha256': record['ids_sha256'],
        'source_shape': list(matrix.shape), 'requested_rows': len(ids),
        'nonfinite_cells': int(nonfinite.sum()), 'ids': ids,
    }


def _raw(frame: pd.DataFrame, family: str, config: dict):
    ids = molecule_ids(frame)
    if 'SMILES' not in frame:
        raise ValueError('Raw molecular features require SMILES')
    mols = [Chem.MolFromSmiles(s) if isinstance(s, str) else None for s in frame.SMILES]
    invalid = [ids[i] for i, m in enumerate(mols) if m is None]
    policy = config.get('invalid_policy', 'raise')
    if policy not in ('raise', 'nan'):
        raise ValueError('invalid_policy must be raise or nan')
    if invalid and policy == 'raise':
        raise ValueError(f'Invalid SMILES for {len(invalid)} molecules: {invalid[:8]}')
    n_bits = int(config.get('n_bits', config.get('fp_size', 2048)))
    if n_bits <= 0:
        raise ValueError('n_bits must be positive')
    counts = bool(config.get('counts', 'count' in family))
    chirality = bool(config.get('include_chirality', False))
    radius = int(config.get('radius', 2))
    if family in ('morgan', 'morgan_bits', 'morgan_count', 'morgan_counts', 'feature_morgan', 'feature_morgan_bits', 'feature_morgan_count', 'feature_morgan_counts', 'fcfp_bits', 'fcfp_counts'):
        is_feature = family.startswith(('feature_', 'fcfp')) or bool(config.get('feature_invariants', False))
        kw = dict(radius=radius, fpSize=n_bits, includeChirality=chirality,
                  countSimulation=bool(config.get('count_simulation', False)))
        if is_feature:
            kw['atomInvariantsGenerator'] = rdFingerprintGenerator.GetMorganFeatureAtomInvGen()
        gen = rdFingerprintGenerator.GetMorganGenerator(**kw)
    elif family in ('atom_pair', 'atom_pair_bits', 'atom_pair_counts', 'atompair'):
        gen = rdFingerprintGenerator.GetAtomPairGenerator(
            fpSize=n_bits, includeChirality=chirality,
            minDistance=int(config.get('min_distance', 1)), maxDistance=int(config.get('max_distance', 30)),
            countSimulation=bool(config.get('count_simulation', False)))
    elif family in ('torsion', 'torsion_bits', 'torsion_counts', 'topological_torsion'):
        gen = rdFingerprintGenerator.GetTopologicalTorsionGenerator(
            fpSize=n_bits, includeChirality=chirality,
            torsionAtomCount=int(config.get('torsion_atom_count', 4)),
            countSimulation=bool(config.get('count_simulation', False)))
    elif family in ('rdkit_path', 'rdkit_path_bits', 'rdkit_path_counts'):
        gen = rdFingerprintGenerator.GetRDKitFPGenerator(
            fpSize=n_bits, minPath=int(config.get('min_path', 1)), maxPath=int(config.get('max_path', 7)),
            countSimulation=bool(config.get('count_simulation', False)))
    elif family in ('rdkit2d', 'rdkit_descriptors', 'descriptors'):
        available = dict(Descriptors._descList)
        names = list(config.get('descriptor_names', available.keys()))
        if len(set(names)) != len(names) or any(n not in available for n in names):
            raise ValueError('Unknown or duplicate RDKit descriptor names')
        X = np.full((len(mols), len(names)), np.nan, dtype=np.float32)
        failed = []
        for i, mol in enumerate(mols):
            if mol is None:
                continue
            for j, name in enumerate(names):
                try:
                    X[i, j] = float(available[name](mol))
                except Exception as exc:
                    failed.append({'id': ids[i], 'descriptor': name, 'error': type(exc).__name__})
        bad = ~np.isfinite(X); X[bad] = np.nan
        return X, [f'rdkit_{n}' for n in names], {
            'family': family, 'rdkit_version': rdBase.rdkitVersion, 'ids': ids,
            'invalid_ids': invalid, 'invalid_policy': policy, 'nonfinite_cells': int(bad.sum()),
            'descriptor_failures': failed, 'descriptor_names': names,
        }
    else:
        raise ValueError(f'Unknown feature family {family!r}')
    X = np.full((len(mols), n_bits), np.nan, dtype=np.float32)
    for i, mol in enumerate(mols):
        if mol is not None:
            X[i] = gen.GetCountFingerprintAsNumPy(mol) if counts else gen.GetFingerprintAsNumPy(mol)
    names = [f'{family}_{i}' for i in range(n_bits)]
    return X, names, {
        'family': family, 'rdkit_version': rdBase.rdkitVersion, 'ids': ids,
        'invalid_ids': invalid, 'invalid_policy': policy, 'counts': counts,
        'radius': radius if 'morgan' in family or family.startswith('fcfp') else None,
        'n_bits': n_bits, 'include_chirality': chirality,
    }


def build_features(molecules: pd.DataFrame, family: str, asset_root: Path,
                   config: dict | None = None) -> tuple[np.ndarray, list[str], dict]:
    """Build raw features or gather verified frozen features in exact input-ID order.

    Cache is opt-in via ``cache=True``. It contains only label-free raw features,
    keyed by IDs, SMILES, full feature config and RDKit version. Learned
    imputation/scaling/PCA are deliberately absent.
    """
    config = dict(config or {}); asset_root = Path(asset_root)
    family = str(family).lower()
    if family in ('precomputed', 'embedding', 'frozen_embedding'):
        return _precomputed(molecules, asset_root, config)
    if family in ('monroe', 'molformer', 'unimol', 'unimol2'):
        raise NotImplementedError(
            f'{family} online adapter is not enabled in the core implementation. '
            'Stage pinned, ID-audited embeddings and use family=precomputed; no implicit download/fallback.')
    ids = molecule_ids(molecules)
    cache_path = None
    if config.get('cache', False):
        cfg = {k: v for k, v in config.items() if k not in ('cache', 'cache_dir')}
        payload = {'family': family, 'config': cfg, 'rdkit_version': rdBase.rdkitVersion,
                   'ids': ids, 'smiles': molecules.get('SMILES', pd.Series(dtype=str)).fillna('<MISSING>').astype(str).tolist()}
        key = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        cache_dir = _path(config.get('cache_dir', 'feature_cache'), asset_root)
        cache_dir.mkdir(parents=True, exist_ok=True); cache_path = cache_dir / f'{key}.npz'
        if cache_path.exists():
            with np.load(cache_path, allow_pickle=False) as cached:
                X = cached['X']; names = cached['names'].tolist(); meta = json.loads(str(cached['metadata'].item()))
            if meta['ids'] != ids or X.shape != (len(ids), len(names)):
                raise ValueError(f'Invalid feature cache alignment: {cache_path}')
            meta.update(cache_hit=True, cache_path=str(cache_path), cache_key=key)
            return X, names, meta
    X, names, meta = _raw(molecules, family, config)
    meta['cache_hit'] = False
    if cache_path is not None:
        meta.update(cache_path=str(cache_path), cache_key=cache_path.stem)
        fd, tmp = tempfile.mkstemp(prefix=cache_path.stem+'.', suffix='.npz', dir=cache_path.parent)
        os.close(fd)
        try:
            np.savez_compressed(tmp, X=X, names=np.asarray(names, dtype=str), metadata=np.array(json.dumps(meta)))
            os.replace(tmp, cache_path)
        finally:
            Path(tmp).unlink(missing_ok=True)
    return X, names, meta


def pairwise_tanimoto(X: np.ndarray, Y: np.ndarray, kind: str = 'tdp') -> np.ndarray:
    """Explicit Tanimoto variant; zero-vs-zero is 1 and zero-vs-nonzero is 0.

    tdp: dot / (squared_norm_x + squared_norm_y - dot).
    tmm: sum(min(x,y)) / sum(max(x,y)); requires nonnegative counts.
    The variants agree on binary fingerprints and differ on counts.
    """
    X = np.asarray(X, dtype=np.float64); Y = np.asarray(Y, dtype=np.float64)
    if X.ndim != 2 or Y.ndim != 2 or X.shape[1] != Y.shape[1]:
        raise ValueError('Tanimoto arrays must be 2D with matching feature width')
    if not np.isfinite(X).all() or not np.isfinite(Y).all() or (X < 0).any() or (Y < 0).any():
        raise ValueError('Tanimoto requires finite, nonnegative fingerprints; do not standardize/PCA them')
    if kind in ('tdp', 'tanimoto', 'dot'):
        numerator = X @ Y.T
        denominator = np.sum(X*X, axis=1)[:,None] + np.sum(Y*Y, axis=1)[None,:] - numerator
    elif kind in ('tmm', 'minmax'):
        from scipy.spatial.distance import cdist
        norms = X.sum(axis=1)[:,None] + Y.sum(axis=1)[None,:]
        distances = cdist(X, Y, metric='cityblock')
        numerator = norms - distances; denominator = norms + distances
    else:
        raise ValueError(f'Unknown Tanimoto kind {kind!r}')
    out = np.divide(numerator, denominator, out=np.ones_like(numerator), where=denominator > 0)
    return np.clip(out, 0.0, 1.0)
