from pathlib import Path
import json,hashlib
from rdkit import Chem
from rdkit.Chem import AllChem,rdCIPLabeler
p=Path(__file__).parent;s='O=C(NC1CCC(F)(F)CC1)N1C[C@@H]2C[C@H](C1)C1=CC=CC(=O)N1C2';o=Chem.MolFromSmiles(s);m=Chem.AddHs(o)
def atomtable(x):return [{'idx':a.GetIdx(),'element':a.GetSymbol(),'tag':str(a.GetChiralTag()),'CIP':a.GetProp('_CIPCode') if a.HasProp('_CIPCode') else None,'neighbors':[b.GetIdx() for b in a.GetNeighbors()]} for a in x.GetAtoms() if a.GetChiralTag()!=Chem.ChiralType.CHI_UNSPECIFIED or a.HasProp('_CIPCode')]
def inspect(x,geometry=False):
 t=Chem.Mol(x)
 if geometry:Chem.AssignStereochemistryFrom3D(t,confId=0,replaceExistingTags=True);Chem.AssignStereochemistry(t,cleanIt=True,force=True)
 legacy=atomtable(t);rdCIPLabeler.AssignCIPLabels(t);return {'legacy':legacy,'modern':atomtable(t),'graph_smiles':Chem.MolToSmiles(Chem.RemoveHs(x),isomericSmiles=True)}
params=AllChem.ETKDGv3();params.randomSeed=42;params.pruneRmsThresh=-1.;params.enforceChirality=True;ids=list(AllChem.EmbedMultipleConfs(m,numConfs=1,params=params));assert len(ids)==1;pre=Chem.Mol(m);r={'id':'OCNT-2315767','smiles':s,'original':inspect(o),'after_ETKDG_geometry':inspect(pre,True)};opt=AllChem.MMFFOptimizeMoleculeConfs(m,numThreads=1,maxIters=500,mmffVariant='MMFF94');r['MMFF']=opt;r['after_MMFF_geometry']=inspect(m,True);r['source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();r['scope']='samefixedprotocol diagnostic only; no embeddings/no retryseed/no changedbank'
for name,mol in [('ETKDG',pre),('MMFF',m)]:
 w=Chem.SDWriter(str(p/(name+'.sdf')));w.write(mol);w.close()
(p/'STEREO_AUDIT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
