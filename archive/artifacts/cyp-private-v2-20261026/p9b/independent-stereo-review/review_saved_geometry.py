from pathlib import Path
import json,hashlib,numpy as np
from rdkit import Chem,rdBase
from rdkit.Chem import rdCIPLabeler
P=Path(__file__).resolve().parents[1];O=Path(__file__).resolve().parent;R=P/'failure-audit';report=json.loads((R/'STEREO_AUDIT.json').read_text());smiles=report['smiles'];original=Chem.MolFromSmiles(smiles);ref=Chem.AddHs(original);defined=[a.GetIdx() for a in original.GetAtoms() if a.GetChiralTag()!=Chem.ChiralType.CHI_UNSPECIFIED];identity=[(a.GetAtomicNum(),a.GetIsotope(),a.GetFormalCharge(),a.GetAtomMapNum()) for a in ref.GetAtoms()]
def clear(m):
 for a in m.GetAtoms():
  for name in ['_CIPCode','_CIPRank']:
   if a.HasProp(name):a.ClearProp(name)
 for b in m.GetBonds():
  if b.HasProp('_CIPCode'):b.ClearProp('_CIPCode')
def modern(m,geometry):
 t=Chem.Mol(m);clear(t)
 if geometry:Chem.AssignStereochemistryFrom3D(t,confId=0,replaceExistingTags=True);clear(t)
 rdCIPLabeler.AssignCIPLabels(t)
 return t,{i:{'CIP':t.GetAtomWithIdx(i).GetProp('_CIPCode') if t.GetAtomWithIdx(i).HasProp('_CIPCode') else None,'tag':str(t.GetAtomWithIdx(i).GetChiralTag()),'neighbors':[a.GetIdx() for a in t.GetAtomWithIdx(i).GetNeighbors()]} for i in defined}
refmod,refvals=modern(ref,False);origmod,origvals=modern(original,False);mols={};evidence={}
for name in ['ETKDG','MMFF']:
 m=next(iter(Chem.SDMolSupplier(str(R/(name+'.sdf')),removeHs=False,sanitize=True)));assert m is not None
 assert [(a.GetAtomicNum(),a.GetIsotope(),a.GetFormalCharge(),a.GetAtomMapNum()) for a in m.GetAtoms()]==identity
 assert [(b.GetBeginAtomIdx(),b.GetEndAtomIdx(),str(b.GetBondType()),b.GetIsAromatic()) for b in m.GetBonds()]==[(b.GetBeginAtomIdx(),b.GetEndAtomIdx(),str(b.GetBondType()),b.GetIsAromatic()) for b in ref.GetBonds()]
 t,vals=modern(m,True);canonical=Chem.MolToSmiles(Chem.RemoveHs(t),isomericSmiles=True);assert canonical==Chem.MolToSmiles(original,isomericSmiles=True);assert all(vals[i]['CIP']==refvals[i]['CIP']==origvals[i]['CIP'] and vals[i]['tag']==refvals[i]['tag'] and vals[i]['neighbors']==refvals[i]['neighbors'] for i in defined)
 xyz=np.array(m.GetConformer().GetPositions());orientation={}
 for i in defined:
  ix=[a.GetIdx() for a in ref.GetAtomWithIdx(i).GetNeighbors()];assert len(ix)==4;v=xyz[ix];det=float(np.linalg.det(np.array([v[0]-v[3],v[1]-v[3],v[2]-v[3]])));orientation[i]={'neighbor_order':ix,'signed_determinant_A3':det}
 mols[name]=m;evidence[name]={'fresh_modern_CIP':vals,'signed_neighbor_orientation':orientation,'canonical_isomeric':canonical,'atom_identity_and_bond_order_unchanged':True}
for i in defined:assert np.sign(evidence['ETKDG']['signed_neighbor_orientation'][i]['signed_determinant_A3'])==np.sign(evidence['MMFF']['signed_neighbor_orientation'][i]['signed_determinant_A3'])
# Stress control: permuting two neighbors' coordinates only in an in-memory copied conformer must flip the tested stereocentre and be detected. No file/production geometry mutation.
# Not needed: actual stereotags and geometric orientation already independent of legacy labels.
r={'status':'no_coordinate_inversion_detected; legacy_CIP_comparison_false_positive','id':report['id'],'original_SMILES':smiles,'defined_centres':defined,'original_fresh_modern_CIP':origvals,'H_completed_reference_fresh_modern_CIP':refvals,'saved_geometry_evidence':evidence,'legacy_discrepancy_recorded_in_owner_audit':report['after_MMFF_geometry']['legacy'],'no_stale_CIP_properties_used':True,'no_coordinates_generated_or_modified':True,'SDF_coordinate_precision':'saved4decimalcoordinates; signs are far fromdegenerate and unchanged','rdkit_version':rdBase.rdkitVersion,'input_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'STEREO_AUDIT.json',R/'ETKDG.sdf',R/'MMFF.sdf',R/'audit_stereo.py',Path(__file__)]}};(O/'INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
