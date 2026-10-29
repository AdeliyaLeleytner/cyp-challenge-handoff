"""Frozen outer cohorts and grouped inner validation, without score-based selection."""
import json, hashlib
from pathlib import Path
import pandas as pd
import numpy as np
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from .public_data import normalize_parent_key

def make_cohorts(data_dir, reference_dir, output, seed=42):
    data_dir, reference_dir = Path(data_dir), Path(reference_dir)
    df = pd.read_csv(data_dir/'official-train.csv')
    test = pd.read_csv(data_dir/'official-test.csv')
    parents = dict(zip(df.Molecule_Name,df.SMILES.map(normalize_parent_key)))
    if any(v is None for v in parents.values()): raise ValueError('Invalid official parent')
    excluded = sorted(set(parents.values()) | set(test.SMILES.map(normalize_parent_key)))
    holdouts = {'own750': pd.read_csv(data_dir/'holdout.csv').Molecule_Name.tolist(),
                'briford529':pd.read_csv(reference_dir/'holdout_ids.csv').iloc[:,0].tolist()}
    result = {'seed':seed,'excluded_parent_keys':excluded,'cohorts':{}}
    for name, held in holdouts.items():
        heldset = set(held)
        heldparents = {parents[i] for i in held}
        dev = df[~df.Molecule_Name.isin(heldset) & ~df.Molecule_Name.map(parents).isin(heldparents)].copy()
        groups=[]; mapping={}
        for smi in dev.SMILES:
            scaff=Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(Chem.MolFromSmiles(smi)))
            if scaff not in mapping: mapping[scaff]=len(mapping)
            groups.append(mapping[scaff])
        groups=np.array(groups)
        unique,counts=np.unique(groups,return_counts=True)
        loads=np.zeros(5,dtype=int); assignment={}
        for ix in np.random.default_rng(seed).permutation(len(unique)):
            f=int(np.argmin(loads));assignment[int(unique[ix])]=f;loads[f]+=int(counts[ix])
        fold=np.array([assignment[int(g)] for g in groups])
        folds=[]
        for f in range(5):
            val=dev.loc[fold==f,'Molecule_Name'].tolist()
            vp={parents[i] for i in val}
            train=dev.loc[(fold!=f)&~dev.Molecule_Name.map(parents).isin(vp),'Molecule_Name'].tolist()
            folds.append({'train_ids':train,'val_ids':val,
                          'parent_purged':int((fold!=f).sum())-len(train)})
        purge=df.loc[~df.Molecule_Name.isin(heldset)&df.Molecule_Name.map(parents).isin(heldparents),'Molecule_Name'].tolist()
        result['cohorts'][name]={'train_ids':dev.Molecule_Name.tolist(),'test_ids':held,'inner_folds':folds,
            'outer_parent_purged_ids':purge,'test_id_sha256':hashlib.sha256('\n'.join(held).encode()).hexdigest(),
            'scaffolds':len(unique),'deviation':'Published scaffold groups plus train-side normalized-parent purge.'}
        assert not (set(dev.Molecule_Name)&heldset)
        assert sorted(sum([f['val_ids'] for f in folds],[]))==sorted(dev.Molecule_Name.tolist())
    Path(output).write_text(json.dumps(result,indent=2))
    return result
