"""Frozen encoders with explicit molecule ordering and checkpoint provenance.

No fitting: the two public ADME models use Jeremy's exact CPU fingerprint path.
The generic foundation encoder is BondMessagePassing + MeanAggregation only.
"""
from __future__ import annotations

from pathlib import Path
import gc
import hashlib
import json
import os

import numpy as np
import pandas as pd

MODELS = {
    'adme': 'chemprop_medium.pt',
    'chemeleon_adme': 'chemprop_chemeleon.pt',
    'foundation': 'chemeleon_foundation.pt',
}
JEREMY_SOURCE = Path(__file__).resolve().parents[1] / 'vendor' / 'jeremy' / 'chemprop_transfer.py'
JEREMY_SOURCE_SHA256 = '4daa3b30ffe8becd09e6533a331f7ac1d7f8984e7bed46de590698ecaf378c2c'


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def _json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    os.replace(temp, path)


def _jeremy_module():
    import importlib.util
    if _sha(JEREMY_SOURCE) != JEREMY_SOURCE_SHA256:
        raise ValueError('Pinned Jeremy embedding source changed')
    spec = importlib.util.spec_from_file_location('tdi_frozen_jeremy_transfer', JEREMY_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Chemprop2.2.1 supplies drop_last internally even when present in kwargs.
    # A module-local proxy preserves the original intended deterministic loader.
    from types import SimpleNamespace
    module.data = SimpleNamespace(**vars(module.data))
    module.data.build_dataloader = _inference_loader
    return module


def _inference_loader(dataset, *, num_workers=0, batch_size=256, shuffle=False, drop_last=False):
    from torch.utils.data import DataLoader
    from chemprop.data.collate import collate_batch
    if shuffle or drop_last or num_workers != 0:
        raise ValueError('Embedding loader must preserve every input row in order')
    return DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0,
                      collate_fn=collate_batch, drop_last=False)


def extract_embeddings(pretrained_path, smiles_list: list[str], batch_size: int = 256) -> np.ndarray:
    """Original embed_with_model, with explicit CPU checkpoint deserialization.

    Published checkpoints contain CUDA tensors; the author's load_from_file()
    omits map_location and cannot deserialize on CPU-only machines. This adapter
    changes only device placement, not tensors, graph featurization or pooling.
    """
    from chemprop.models.model import MPNN
    model = MPNN.load_from_file(str(pretrained_path), map_location='cpu')
    return _jeremy_module().embed_with_model(model, smiles_list, batch_size=batch_size)


def extract_foundation(pretrained_path, smiles_list, batch_size=128, device='cpu'):
    import torch
    from chemprop import data, featurizers, nn
    checkpoint = torch.load(pretrained_path, map_location='cpu', weights_only=False)
    if set(checkpoint) != {'hyper_parameters', 'state_dict'}:
        raise ValueError('Unexpected foundation checkpoint schema')
    message_passing = nn.BondMessagePassing(**checkpoint['hyper_parameters'])
    message_passing.load_state_dict(checkpoint['state_dict'], strict=True)
    message_passing = message_passing.to(device).eval()
    aggregate = nn.MeanAggregation().to(device).eval()
    featurizer = featurizers.SimpleMoleculeMolGraphFeaturizer()
    pts = [data.MoleculeDatapoint.from_smi(smi, [0.0]) for smi in smiles_list]
    dataset = data.MoleculeDataset(pts, featurizer)
    loader = _inference_loader(dataset, num_workers=0, batch_size=batch_size,
                               shuffle=False, drop_last=False)
    vectors = []
    with torch.inference_mode():
        for batch in loader:
            bmg, V_d, *_ = batch
            bmg.to(device)
            if V_d is not None:
                V_d = V_d.to(device)
            vectors.append(aggregate(message_passing(bmg, V_d), bmg.batch).cpu().numpy())
    result = np.concatenate(vectors)
    if result.shape != (len(smiles_list), message_passing.output_dim):
        raise ValueError('Foundation embedding shape mismatch')
    return result


def _validate_vectors(vectors, smiles, name):
    if vectors.ndim != 2 or vectors.shape[0] != len(smiles) or vectors.shape[1] < 1:
        raise ValueError(f'{name}: embedding rows/order mismatch')
    if not np.isfinite(vectors).all():
        raise ValueError(f'{name}: nonfinite embeddings')
    first, repeats, max_difference = {}, 0, 0.0
    for i, smi in enumerate(smiles):
        if smi not in first:
            first[smi] = i
            continue
        j = first[smi]
        repeats += 1
        difference = float(np.max(np.abs(vectors[i] - vectors[j])))
        max_difference = max(max_difference, difference)
        # Float32 matrix kernels may round differently in different-sized batches.
        if not np.allclose(vectors[i], vectors[j], rtol=1e-4, atol=2e-5):
            raise ValueError(f'{name}: identical SMILES have inconsistent embeddings at {j}/{i}')
    return {'shape': list(vectors.shape), 'dtype': str(vectors.dtype), 'duplicate_smiles_pairs': repeats,
            'duplicate_max_absolute_difference': max_difference,
            'duplicate_tolerance': {'rtol': 1e-4, 'atol': 2e-5}}


def _verify_files(root, outputs):
    for name, digest in outputs.items():
        path = root / name
        if not path.exists() or _sha(path) != digest:
            raise ValueError(f'Frozen embedding output is missing or modified: {path}')


def prepare_embeddings(prepared_dir, weights_dir, *, device='cpu', batch_size=128, num_threads=4):
    """Write X_{adme,chemeleon_adme,foundation}_{train,test}.npy, preserving CSV order.

    device applies ONLY to generic foundation. Jeremy encoders always use CPU.
    Complete runs verify source/config/output hashes before returning. Individual
    completed encoders can also resume safely after interrupted preparation.
    """
    import torch
    import importlib.metadata
    root, weights = Path(prepared_dir), Path(weights_dir)
    if int(batch_size) < 1 or int(num_threads) < 1:
        raise ValueError('Positive batch size and thread count required')
    torch.set_num_threads(int(num_threads))
    frames = {name: pd.read_csv(root / f'{name}.csv') for name in ['train', 'test']}
    for name, frame in frames.items():
        if frame.Molecule_Name.isna().any() or frame.Molecule_Name.duplicated().any() or frame.SMILES.isna().any():
            raise ValueError(f'Invalid molecule identifiers in {name}')
        ids_path = root / f'{name}_ids.csv'
        if ids_path.exists():
            expected = pd.read_csv(ids_path)[['Molecule_Name', 'SMILES']]
            if not expected.equals(frame[['Molecule_Name', 'SMILES']]):
                raise ValueError(f'{name} table diverges from frozen molecule-order file')
    combined = pd.concat([frames['train'], frames['test']], ignore_index=True)
    smiles = combined.SMILES.tolist()
    n_train = len(frames['train'])
    if set(frames['train'].Molecule_Name) & set(frames['test'].Molecule_Name):
        raise ValueError('Train/test molecule identifiers overlap')
    signature = {
        'csv_sha256': {name: _sha(root / f'{name}.csv') for name in frames},
        'checkpoints': {name: {'filename': filename, 'sha256': _sha(weights / filename)}
                        for name, filename in MODELS.items()},
        'batch_size': int(batch_size), 'torch_threads': int(num_threads),
        'foundation_device': str(device), 'adme_device': 'cpu',
        'implementation_sha256': _sha(Path(__file__)),
        'jeremy_source_sha256': _sha(JEREMY_SOURCE),
        'versions': {pkg: importlib.metadata.version(pkg) for pkg in ['torch', 'chemprop', 'rdkit', 'numpy']},
    }
    complete = root / 'embeddings_manifest.json'
    if complete.exists():
        manifest = json.loads(complete.read_text())
        if manifest['signature'] != signature:
            raise ValueError('Existing embedding cache has different source/config/version signature')
        _verify_files(root, manifest['output_sha256'])
        return manifest
    for name, frame in frames.items():
        frame[['Molecule_Name', 'SMILES']].to_csv(root / f'embedding_ids_{name}.csv', index=False)
    audits = {}
    for name, checkpoint_name in MODELS.items():
        marker = root / f'embeddings_{name}_complete.json'
        if marker.exists():
            previous = json.loads(marker.read_text())
            if previous['signature'] != signature:
                raise ValueError(f'Partial {name} extraction used a different source signature')
            _verify_files(root, previous['output_sha256'])
            audits[name] = previous['audit']
            continue
        print(json.dumps({'stage': 'embedding', 'encoder': name, 'rows': len(smiles),
                          'device': str(device) if name == 'foundation' else 'cpu'}), flush=True)
        checkpoint_path = weights / checkpoint_name
        if name == 'foundation':
            vectors = extract_foundation(checkpoint_path, smiles, int(batch_size), device=device)
        else:
            vectors = extract_embeddings(checkpoint_path, smiles, int(batch_size))
        audits[name] = _validate_vectors(vectors, smiles, name)
        expected_dim = {'adme': 600, 'chemeleon_adme': 2048, 'foundation': 2048}[name]
        if vectors.shape[1] != expected_dim:
            raise ValueError(f'{name}: unexpected encoder dimensionality {vectors.shape[1]}')
        for part, array in [('train', vectors[:n_train]), ('test', vectors[n_train:])]:
            assert len(array) == len(frames[part])
            path = root / f'X_{name}_{part}.npy'
            with path.with_suffix('.npy.tmp').open('wb') as stream:
                np.save(stream, array)
            os.replace(path.with_suffix('.npy.tmp'), path)
        outputs = {f'X_{name}_{part}.npy': _sha(root / f'X_{name}_{part}.npy') for part in frames}
        _json(marker, {'signature': signature, 'audit': audits[name], 'output_sha256': outputs})
        del vectors
        gc.collect()
        if str(device).startswith('cuda'):
            torch.cuda.empty_cache()
    outputs = {f'X_{name}_{part}.npy': _sha(root / f'X_{name}_{part}.npy')
               for name in MODELS for part in frames}
    outputs.update({f'embedding_ids_{part}.csv': _sha(root / f'embedding_ids_{part}.csv') for part in frames})
    manifest = {'signature': signature, 'audits': audits, 'output_sha256': outputs,
                'train_rows': n_train, 'test_rows': len(frames['test']),
                'operation': 'Frozen encoders only; no labels read by extraction; no parameter fitting',
                'reference_path': 'CPU map_location loader adapter -> unchanged Jeremy embed_with_model -> model.fingerprint',
                'reference_adaptation': ['CUDA-serialized checkpoint tensors relocated to CPU',
                                         'Module-local torch DataLoader plus Chemprop collate_batch preserves explicit drop_last=False intent'],
                'foundation_path': 'BondMessagePassing(strict checkpoint) -> MeanAggregation',
                'joint_order': 'train.csv rows followed by test.csv rows; split only after extraction'}
    _json(complete, manifest)
    return manifest
