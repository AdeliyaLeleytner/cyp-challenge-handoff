"""Physicochemical descriptors and ECFP4 molecular fingerprints."""
from collections.abc import Sequence
import numpy as np
from rdkit import Chem
from rdkit.Chem import rdFingerprintGenerator, rdMolDescriptors

SMARTS_BASIC_AMINE = Chem.MolFromSmarts("[#7;X3;!$(N-C=[O,S]);!$(N-S(=O)=O);!$(N=O)]")

SMARTS_ACIDIC_CENTER = Chem.MolFromSmarts("[CX3](=O)[OX2H1,OX1-]")

SMARTS_AROM_HETEROCYCLE = Chem.MolFromSmarts("[a;!c]")

SMARTS_HALOGENS = Chem.MolFromSmarts("[F,Cl,Br,I]")

def extract_physicochemical_basis(smiles_list: Sequence[str]) -> np.ndarray:
    """Extract standard 16-parameter physical-organic property and pharmacophore descriptor basis.

    Parameters
    ----------
    smiles_list : Sequence[str]
        List of SMILES strings.

    Returns
    -------
    np.ndarray of shape (len(smiles_list), 16)
        Features: [mw, logp, tpsa, hbd, hba, rotb, arom_rings, heavy,
                   fsp3, charge, basic_amine, acid_center, aromatic_heterocycle,
                   halogen_count, lipophilic_density, surface_roughness]
    """
    feats = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi) if isinstance(smi, str) else None
        if mol is None:
            feats.append([0.0] * 16)
            continue
        mw = float(rdMolDescriptors.CalcExactMolWt(mol))
        logp = float(rdMolDescriptors.CalcCrippenDescriptors(mol)[0])
        tpsa = float(rdMolDescriptors.CalcTPSA(mol))
        hbd = float(rdMolDescriptors.CalcNumHBD(mol))
        hba = float(rdMolDescriptors.CalcNumHBA(mol))
        rotb = float(rdMolDescriptors.CalcNumRotatableBonds(mol))
        arom_rings = float(rdMolDescriptors.CalcNumAromaticRings(mol))
        heavy = float(mol.GetNumHeavyAtoms())
        fsp3 = float(rdMolDescriptors.CalcFractionCSP3(mol))
        charge = float(Chem.GetFormalCharge(mol))

        basic_amine = 1.0 if mol.HasSubstructMatch(SMARTS_BASIC_AMINE) else 0.0
        acid_center = 1.0 if mol.HasSubstructMatch(SMARTS_ACIDIC_CENTER) else 0.0
        aromatic_heterocycle = float(
            len(mol.GetSubstructMatches(SMARTS_AROM_HETEROCYCLE))
        )
        halogen_count = float(len(mol.GetSubstructMatches(SMARTS_HALOGENS)))
        lipophilic_density = logp / (mw / 100.0) if mw > 0 else 0.0
        surface_roughness = tpsa / (heavy + 1e-3)

        feats.append(
            [
                mw,
                logp,
                tpsa,
                hbd,
                hba,
                rotb,
                arom_rings,
                heavy,
                fsp3,
                charge,
                basic_amine,
                acid_center,
                aromatic_heterocycle,
                halogen_count,
                lipophilic_density,
                surface_roughness,
            ]
        )
    return np.asarray(feats, dtype=np.float32)

def extract_ecfp4(smiles_list: Sequence[str], n_bits: int = 1024) -> np.ndarray:
    """Extract binary ECFP4 (Morgan radius 2, no chirality) fingerprints.

    Parameters
    ----------
    smiles_list : Sequence[str]
        List of SMILES strings.
    n_bits : int, default=1024
        Fingerprint width.

    Returns
    -------
    np.ndarray of shape (len(smiles_list), n_bits)
    """
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=2, fpSize=n_bits, includeChirality=False
    )
    rows = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            raise ValueError(f"Invalid SMILES: {smi}")
        rows.append(generator.GetFingerprintAsNumPy(mol))
    return np.asarray(rows, dtype=np.float32)
