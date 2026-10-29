"""Independent coordinate/graph identity review of persisted bank shards, no inference."""
import json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from rdkit import Chem
p=Path(__file__).parent;rows=pd.read_csv(p.parent/'p9a/next-stage/official5655-structures.csv');records=[]
def groups(m):return [(str(g.GetGroupType()),tuple(a.GetIdx() for a in g.GetAtoms())) for g in m.GetStereoGroups()]
for file in sorted((p/'results').glob('coordinates-through-*.npz')):
 data=np.load(file)
 for key in data.files:
  if not key.startswith('z_'):continue
  i=int(key[2:]);r=rows.iloc[i];o=Chem.MolFromSmiles(r.SMILES);m=Chem.AddHs(o);pos=data[f'pos_{i}'];z=data[key];rec={'index':i,'id':r.Molecule_Name,'specified_atoms':0,'specified_bonds':0,'enhanced_groups':len(groups(o)),'errors':[]}
  if groups(o)!=groups(m):rec['errors'].append('enhanced_group_changed')
  if not np.array_equal(z,[a.GetAtomicNum() for a in m.GetAtoms()]):rec['errors'].append('atom_identity_order')
  if not np.isfinite(pos).all() or pos.shape!=(m.GetNumAtoms(),3):rec['errors'].append('coordinates_shape_or_finiteness')
  conf=Chem.Conformer(m.GetNumAtoms())
  for k,xyz in enumerate(pos):conf.SetAtomPosition(k,[float(v) for v in xyz])
  m.RemoveAllConformers();m.AddConformer(conf,assignId=True);Chem.AssignStereochemistryFrom3D(m,confId=0,replaceExistingTags=True);Chem.AssignStereochemistry(m,cleanIt=True,force=True)
  for a in o.GetAtoms():
   if a.HasProp('_CIPCode'):
    rec['specified_atoms']+=1;b=m.GetAtomWithIdx(a.GetIdx())
    if not b.HasProp('_CIPCode') or b.GetProp('_CIPCode')!=a.GetProp('_CIPCode'):rec['errors'].append(f'atom_stereo_{a.GetIdx()}')
  for b in o.GetBonds():
   if b.GetStereo() not in [Chem.BondStereo.STEREONONE,Chem.BondStereo.STEREOANY]:
    rec['specified_bonds']+=1;other=m.GetBondBetweenAtoms(b.GetBeginAtomIdx(),b.GetEndAtomIdx())
    if other.GetStereo()!=b.GetStereo():rec['errors'].append(f'bond_stereo_{b.GetIdx()}_{b.GetStereo()}_to_{other.GetStereo()}')
  records.append(rec)
assert len(records)==len({x['index'] for x in records});report={'status':'complete_pass' if len(records)==5655 and not any(x['errors'] for x in records) else 'partial_or_flagged','persisted_coordinate_rows':len(records),'expected_rows':5655,'specified_atom_checks':sum(x['specified_atoms'] for x in records),'specified_bond_checks':sum(x['specified_bonds'] for x in records),'enhanced_group_rows':sum(x['enhanced_groups']>0 for x in records),'flagged':[x for x in records if x['errors']],'coordinate_files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((p/'results').glob('coordinates-through-*.npz'))},'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'no_inference':True};(p/'COORDINATE_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='coordinate_files'}))
