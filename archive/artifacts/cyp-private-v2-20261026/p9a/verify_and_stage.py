"""Read-only smoke verification and structure-only next-stage inventory; no model calls."""
from pathlib import Path
import pandas as pd,numpy as np,json,hashlib
from rdkit import Chem
p=Path(__file__).parent;out=p/'results';stage=p/'next-stage';stage.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def groups(m):return [(str(g.GetGroupType()),tuple(a.GetIdx() for a in g.GetAtoms())) for g in m.GetStereoGroups()]
rows=pd.read_csv(p/'assets/smoke-rows.csv');emb=np.load(out/'embeddings.npy');got=pd.read_csv(out/'embedding-rows.csv');assert emb.shape==(32,256) and np.isfinite(emb).all();assert got.Molecule_Name.tolist()==rows.Molecule_Name.tolist() and got.SMILES.tolist()==rows.SMILES.tolist();c=json.load(open(out/'COMPLETE.json'));assert c['repeat_max_abs']==0 and c['reorder_max_abs']==0
coords=np.load(out/'coordinates.npz');enhanced=0;assigned_bonds=0
for i,r in rows.iterrows():
 m=Chem.MolFromSmiles(r.SMILES);mh=Chem.AddHs(m);mr=Chem.RemoveHs(mh);assert groups(m)==groups(mh)==groups(mr);enhanced+=bool(groups(m));assert np.array_equal(coords[f'z_{i}'],[a.GetAtomicNum() for a in mh.GetAtoms()]);assert coords[f'pos_{i}'].shape==(mh.GetNumAtoms(),3)
 for b in m.GetBonds():
  if b.GetStereo()!=Chem.BondStereo.STEREONONE:assert mh.GetBondBetweenAtoms(b.GetBeginAtomIdx(),b.GetEndAtomIdx()).GetStereo()==b.GetStereo();assigned_bonds+=1
full=[];sources=[]
for role,path in [('train',Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-admet500-pilot-20261025/stage/official-train.csv')),('blind',Path('/Users/adeliyaleleytner/.local/share/openresearch/projects/cyp-chemeleon-baseline-20261023/data/official-test.csv'))]:
 d=pd.read_csv(path,usecols=['Molecule_Name','SMILES']);assert d.Molecule_Name.is_unique;sources.append({'role':role,'path':str(path),'sha256':sha(path),'rows':len(d)})
 for i,r in d.iterrows():
  m=Chem.MolFromSmiles(r.SMILES);assert m
  full.append({'Molecule_Name':r.Molecule_Name,'role':role,'source_row':int(i),'SMILES':r.SMILES,'smiles_sha256':hashlib.sha256(r.SMILES.encode()).hexdigest(),'canonical_isomeric':Chem.MolToSmiles(m,isomericSmiles=True),'canonical_cxsmiles':Chem.MolToCXSmiles(m),'heavy_atoms':m.GetNumHeavyAtoms(),'explicit_h_atoms':Chem.AddHs(m).GetNumAtoms(),'fragments':len(Chem.GetMolFrags(m)),'stereo_groups':json.dumps(groups(m))})
d=pd.DataFrame(full);assert len(d)==5655 and d.Molecule_Name.is_unique;d.to_csv(stage/'official5655-structures.csv',index=False)
a=Path('/Users/adeliyaleleytner/.local/share/cyp-inhibition/reciprocal-comparison-20261023/full/prepared');ad=pd.read_csv(a/'challenge.csv',usecols=['Molecule_Name','SMILES']);bank=np.load(a/'adme_pretrain.npy');assert bank.shape==(4905,600) and np.isfinite(bank).all();train=d[d.role=='train'];assert ad.Molecule_Name.tolist()==train.Molecule_Name.tolist() and ad.SMILES.tolist()==train.SMILES.tolist();sm=rows[rows.role=='train'];assert ad.set_index('Molecule_Name').loc[sm.Molecule_Name,'SMILES'].tolist()==sm.SMILES.tolist()
receipt={'status':'pass','smoke_rows':32,'embedding_shape':list(emb.shape),'finite':True,'same_exactID_SMILES_order':True,'enhanced_stereo_group_rows_preserved':enhanced,'assigned_bond_stereo_preserved':assigned_bonds,'repeat_max_abs':c['repeat_max_abs'],'reorder_max_abs':c['reorder_max_abs'],'full_structure_only_inventory':{'path':str(stage/'official5655-structures.csv'),'sha256':sha(stage/'official5655-structures.csv'),'rows':5655,'train':4905,'blind':750,'no_labels':True,'sources':sources},'adme600_train_control':{'path':str(a/'adme_pretrain.npy'),'sha256':sha(a/'adme_pretrain.npy'),'mapping':str(a/'challenge.csv'),'mapping_sha256':sha(a/'challenge.csv'),'exact_official_training_order_and_smiles':True,'shape':[4905,600]},'blind_adme600_not_required_for_current_OOF_comparison':True,'no_fullbank_inference_or_TabICL_calls':True,'code_sha256':sha(__file__),'smoke_files':{x.name:sha(x) for x in out.iterdir() if x.is_file()}};(p/'VERIFICATION.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['smoke_files','full_structure_only_inventory','adme600_train_control']}));print('fullinventoryatomcounts',d.groupby('role').explicit_h_atoms.agg(['mean','max']).to_dict())
