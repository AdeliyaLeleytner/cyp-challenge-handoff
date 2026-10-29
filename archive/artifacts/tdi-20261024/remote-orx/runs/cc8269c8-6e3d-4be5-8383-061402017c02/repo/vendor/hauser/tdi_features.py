"""Exact structure-only inputs of the frozen TDI model; no fitted representation."""

import numpy as np
from rdkit import Chem
from rdkit.Avalon import pyAvalonTools
from rdkit.Chem import MACCSkeys, rdFingerprintGenerator

from training.features import extract_physicochemical_basis

FINGERPRINT_COLUMNS = (
    [f"maccs_{i}" for i in range(167)]
    + [f"tt_{i}" for i in range(1024)]
    + [f"ap_{i}" for i in range(1024)]
    + [f"avalon_{i}" for i in range(1024)]
    + [f"pat_{i}" for i in range(1024)]
)
DESCRIPTOR_COLUMNS = [
    "mw",
    "logp",
    "tpsa",
    "hbd",
    "hba",
    "rotb",
    "arom_rings",
    "heavy",
    "fsp3",
    "charge",
    "basic_amine",
    "acid_center",
    "aromatic_heterocycle",
    "halogen_count",
    "lipophilic_density",
    "surface_roughness",
]


def build_tdi_features(smiles, manifest):
    if manifest != {
        "fingerprints": FINGERPRINT_COLUMNS,
        "descriptors": DESCRIPTOR_COLUMNS,
    }:
        raise ValueError(
            "Feature identities or order differ from the frozen TDI specification"
        )
    tt = rdFingerprintGenerator.GetTopologicalTorsionGenerator(fpSize=1024)
    ap = rdFingerprintGenerator.GetAtomPairGenerator(fpSize=1024)
    canonical, rows = [], []
    for value in smiles:
        mol = Chem.MolFromSmiles(value) if isinstance(value, str) else None
        if mol is None:
            raise ValueError(f"Invalid SMILES: {value!r}")
        identity = Chem.MolToSmiles(mol, isomericSmiles=True)
        mol = Chem.MolFromSmiles(identity)
        canonical.append(identity)
        rows.append(
            np.concatenate(
                [
                    np.asarray(MACCSkeys.GenMACCSKeys(mol)),
                    tt.GetFingerprintAsNumPy(mol),
                    ap.GetFingerprintAsNumPy(mol),
                    np.asarray(pyAvalonTools.GetAvalonFP(mol, 1024)),
                    np.asarray(Chem.PatternFingerprint(mol, 1024)),
                ]
            )
        )
    if not rows:
        raise ValueError("At least one molecule is required")
    descriptors = extract_physicochemical_basis(canonical)
    structure = np.column_stack(
        [np.asarray(rows, dtype=np.float32), descriptors]
    ).astype(np.float32)
    if not np.isfinite(structure).all():
        raise ValueError("Nonfinite molecular features")
    return structure, descriptors
