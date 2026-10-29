from pathlib import Path
import numpy as np,pandas as pd
from rdkit import Chem,DataStructs
from rdkit.Chem import Descriptors,rdMolDescriptors,rdFingerprintGenerator
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold
P=Path('/Users/adeliyaleleytner/.cache/cyp-inhibition/data')
tr=pd.read_csv(P/'cyp-challenge-TRAIN_inhibition.csv');te=pd.read_csv(P/'cyp-challenge-TEST-BLINDED.csv')
g=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048,includeChirality=False);fps=[];rows=[]
for r in pd.concat([tr[['Molecule_Name','SMILES']],te]).itertuples():
 m=rdMolStandardize.FragmentParent(rdMolStandardize.Cleanup(Chem.MolFromSmiles(r.SMILES)),skipStandardize=True)
 fps.append(g.GetFingerprint(m));rows.append({'Molecule_Name':r.Molecule_Name,'parent_isomeric':Chem.MolToSmiles(m,isomericSmiles=True),'parent_no_stereo':Chem.MolToSmiles(m,isomericSmiles=False),'murcko':MurckoScaffold.MurckoScaffoldSmiles(mol=m,includeChirality=False),'MW':Descriptors.MolWt(m),'cLogP':Descriptors.MolLogP(m),'TPSA':Descriptors.TPSA(m),'fraction_CSP3':rdMolDescriptors.CalcFractionCSP3(m)})
pd.DataFrame(rows).to_csv(P/'all_molecule_structures.csv',index=False)
t=fps[:len(tr)];q=fps[len(tr):]
tt=np.array([DataStructs.BulkTanimotoSimilarity(f,t) for f in t],dtype=np.float32)
qt=np.array([DataStructs.BulkTanimotoSimilarity(f,t) for f in q],dtype=np.float32)
np.savez(P/'similarity_matrices.npz',train_train=tt,test_train=qt)
print('CACHED',len(tr),len(te),'test median',np.median(qt.max(axis=1)),flush=True)
