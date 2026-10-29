"""Original-graph coordinate audit, consistent modernCIP; no chemical normalization."""
import numpy as np
from rdkit import Chem
from rdkit.Chem import rdCIPLabeler

def group_signature(m):return [(str(g.GetGroupType()),tuple(a.GetIdx() for a in g.GetAtoms())) for g in m.GetStereoGroups()]
def clear_and_label(m):
 for a in m.GetAtoms():
  for key in ['_CIPCode','_CIPRank']:
   if a.HasProp(key):a.ClearProp(key)
 for b in m.GetBonds():
  for key in ['_CIPCode','_CIPRank']:
   if b.HasProp(key):b.ClearProp(key)
 rdCIPLabeler.AssignCIPLabels(m)
def validate(smiles,z,positions):
 original=Chem.MolFromSmiles(smiles);assert original is not None;reference=Chem.AddHs(original);assert np.array_equal(z,[a.GetAtomicNum() for a in reference.GetAtoms()]);assert positions.shape==(reference.GetNumAtoms(),3) and np.isfinite(positions).all();assert group_signature(reference)==group_signature(original)
 assert Chem.MolToCXSmiles(Chem.RemoveHs(reference))==Chem.MolToCXSmiles(original)
 geometry=Chem.Mol(reference);conf=Chem.Conformer(len(z))
 for i,xyz in enumerate(positions):conf.SetAtomPosition(i,[float(v) for v in xyz])
 geometry.RemoveAllConformers();geometry.AddConformer(conf,assignId=True);Chem.AssignStereochemistryFrom3D(geometry,confId=0,replaceExistingTags=True);Chem.AssignStereochemistry(geometry,cleanIt=True,force=True);clear_and_label(reference);clear_and_label(geometry);atoms=0;bonds=0
 for a in reference.GetAtoms():
  if a.GetChiralTag()!=Chem.ChiralType.CHI_UNSPECIFIED:
   other=geometry.GetAtomWithIdx(a.GetIdx());assert [n.GetIdx() for n in a.GetNeighbors()]==[n.GetIdx() for n in other.GetNeighbors()];assert a.GetChiralTag()==other.GetChiralTag(),f'atomorientation{a.GetIdx()}';atoms+=1
   if a.HasProp('_CIPCode'):assert other.HasProp('_CIPCode') and a.GetProp('_CIPCode')==other.GetProp('_CIPCode'),f'modernCIP{a.GetIdx()}'
 for b in reference.GetBonds():
  if b.GetStereo() not in [Chem.BondStereo.STEREONONE,Chem.BondStereo.STEREOANY]:assert geometry.GetBondWithIdx(b.GetIdx()).GetStereo()==b.GetStereo(),f'bondstereo{b.GetIdx()}';bonds+=1
 assert group_signature(geometry)==group_signature(reference)
 return {'specified_atom_checks':atoms,'specified_bond_checks':bonds,'enhanced_groups':len(group_signature(reference)),'modern_CIP_consistent':True,'original_graph_coordinate_reconstruction':True}
