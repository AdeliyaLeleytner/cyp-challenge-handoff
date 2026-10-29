import sys,json,hashlib
from pathlib import Path
import pandas as pd,numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
p=Path(__file__).parent;sys.path.insert(0,str(p/'worktree/night'));from p9_identity import validate
b=p.parent;rows=pd.read_csv(b/'p9a/assets/smoke-rows.csv');co=np.load(b/'p9a/results/coordinates.npz');n=0
for i,r in rows.iterrows():validate(r.SMILES,co[f'z_{i}'],co[f'pos_{i}']);n+=1
assert n==32
negative=[]
for i,r in rows.iterrows():
 m=Chem.AddHs(Chem.MolFromSmiles(r.SMILES));centers=[a for a in m.GetAtoms() if a.GetChiralTag()!=Chem.ChiralType.CHI_UNSPECIFIED]
 if centers:
  ids=[a.GetIdx() for a in centers[0].GetNeighbors()];pos=co[f'pos_{i}'].copy();pos[[ids[0],ids[1]]]=pos[[ids[1],ids[0]]]
  try:validate(r.SMILES,co[f'z_{i}'],pos)
  except AssertionError:negative.append('intentional_coordinate_stereo_inversion_rejected')
  else:raise AssertionError('inversionaccepted')
  break
z=co['z_0'].copy();z[0]+=1
try:validate(rows.SMILES.iloc[0],z,co['pos_0'])
except AssertionError:negative.append('atomidentity_change_rejected')
else:raise AssertionError('atomchangeaccepted')
s='O=C(NC1CCC(F)(F)CC1)N1C[C@@H]2C[C@H](C1)C1=CC=CC(=O)N1C2';runs=[]
for rep in range(2):
 m=Chem.AddHs(Chem.MolFromSmiles(s));params=AllChem.ETKDGv3();params.randomSeed=42;params.pruneRmsThresh=-1.;params.enforceChirality=True;assert len(AllChem.EmbedMultipleConfs(m,numConfs=1,params=params))==1;opt=AllChem.MMFFOptimizeMoleculeConfs(m,numThreads=1,maxIters=500,mmffVariant='MMFF94');z=np.array([a.GetAtomicNum() for a in m.GetAtoms()],dtype=np.int64);pos=m.GetConformer().GetPositions().astype(np.float32);rec=validate(s,z,pos);runs.append((z,pos,opt,rec))
assert np.array_equal(runs[0][1],runs[1][1]);np.savez_compressed(p/'failed-row-fixed-protocol-coordinates.npz',z=runs[0][0],pos=runs[0][1]);receipt={'status':'pass','smoke_positive_rows':32,'negative_controls':negative,'failed_row':'OCNT-2315767','failed_row_same_seed_geometry_repeat_exact':True,'failed_row_MMFF':runs[0][2],'failed_row_modern_validation':runs[0][3],'original_failed_coordinates_not_persisted':True,'regeneration_reason':'samefixedprotocol reexecution, noalternateconformer/seed andnoroundedSDFinput','validator_sha256':hashlib.sha256((p/'worktree/night/p9_identity.py').read_bytes()).hexdigest(),'no_model_inference':True};(p/'VALIDATOR_PREFLIGHT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
