import json,sys,time,hashlib,importlib.metadata
from pathlib import Path
import numpy as np,pandas as pd,torch
from rdkit import Chem
from rdkit.Chem import AllChem
from atom_jepa import AtomJEPA
c=json.loads(Path(sys.argv[1]).read_text());out=Path(c['output']);torch.set_num_threads(c['threads']);torch.manual_seed(c['seed']);np.random.seed(c['seed']);start=time.monotonic()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=pd.read_csv(c['files']['rows']['path']);assert len(rows)==32 and rows.Molecule_Name.is_unique
for role,key in [('train','official_train'),('blind','official_test')]:
 df=pd.read_csv(c['files'][key]['path'],usecols=['Molecule_Name','SMILES']).set_index('Molecule_Name');r=rows[rows.role==role];assert len(r)==16 and r.SMILES.tolist()==df.loc[r.Molecule_Name,'SMILES'].tolist()
model=AtomJEPA.from_pretrained(c['checkpoint'],device='cpu',precision='fp32',cuequivariance=False,compile=False);model.eval();load_time=time.monotonic()-start
print(json.dumps({'loaded_seconds':load_time,'execution':model.execution,'parameter_count':sum(p.numel() for p in model.parameters())}),flush=True)
records=[];samples=[];features=[];successful=[];coordinates={};outcomes=out/'row-outcomes.jsonl'
for i,row in rows.iterrows():
 t=time.monotonic();r={'row':int(i),'id':row.Molecule_Name,'role':row.role,'smiles':row.SMILES,'status':'failed'}
 try:
  m=Chem.MolFromSmiles(row.SMILES);assert m is not None;orig=Chem.MolToSmiles(m,isomericSmiles=True);assert orig==row.canonical_isomeric;mol=Chem.AddHs(m)
  assert Chem.MolToSmiles(Chem.RemoveHs(mol),isomericSmiles=True)==orig
  assert len(Chem.GetMolFrags(mol))==int(row.fragments);assert sum(abs(a.GetFormalCharge()) for a in m.GetAtoms())==int(row.abs_charge)
  params=AllChem.ETKDGv3();params.randomSeed=c['seed'];params.pruneRmsThresh=-1.;params.enforceChirality=True;ids=list(AllChem.EmbedMultipleConfs(mol,numConfs=1,params=params));assert len(ids)==1,'embedding failed';assert AllChem.MMFFHasAllMoleculeParams(mol),'missing MMFF parameters';optimization=AllChem.MMFFOptimizeMoleculeConfs(mol,numThreads=1,maxIters=c['max_iters'],mmffVariant='MMFF94');r['mmff_status']=int(optimization[0][0]);r['mmff_energy']=float(optimization[0][1]);assert r['mmff_status'] in [0,1]
  assert Chem.MolToSmiles(Chem.RemoveHs(mol),isomericSmiles=True)==orig
  stereo=Chem.Mol(mol);Chem.AssignStereochemistryFrom3D(stereo,confId=ids[0],replaceExistingTags=True);Chem.AssignStereochemistry(stereo,cleanIt=True,force=True)
  specified=0
  for a in m.GetAtoms():
   if a.HasProp('_CIPCode'):
    b=stereo.GetAtomWithIdx(a.GetIdx());assert b.HasProp('_CIPCode') and b.GetProp('_CIPCode')==a.GetProp('_CIPCode'),'coordinate stereo inversion';specified+=1
  z=np.array([a.GetAtomicNum() for a in mol.GetAtoms()],dtype=np.int64);pos=mol.GetConformer(ids[0]).GetPositions().astype(np.float32);assert np.isfinite(pos).all();coordinates[f'z_{i}']=z;coordinates[f'pos_{i}']=pos
  sample={'atomic_numbers':z,'node_coordinates':pos};geom_time=time.monotonic()-t;ti=time.monotonic();v=model.embed([sample],layers='last',degrees=0,per_atom=False,batch_size=1).numpy();assert v.shape==(1,256) and np.isfinite(v).all()
  features.append(v[0]);samples.append(sample);successful.append(int(i));r.update(status='success',geometry_seconds=geom_time,inference_seconds=time.monotonic()-ti,explicit_h_atoms=len(z),specified_stereo_verified=specified,graph_roundtrip_exact=True,coordinates_sha256=hashlib.sha256(pos.tobytes()).hexdigest());np.save(out/'embeddings-progress.npy',np.array(features));np.savez_compressed(out/'coordinates.npz',**coordinates)
 except Exception as e:r['error']=type(e).__name__+': '+str(e)
 r['total_seconds']=time.monotonic()-t;records.append(r)
 with outcomes.open('a') as f:f.write(json.dumps(r)+'\n')
 print(json.dumps(r),flush=True)
assert successful,'no successful rows';first=np.array(features);ti=time.monotonic();repeat=model.embed(samples,layers='last',degrees=0,per_atom=False,batch_size=1).numpy();repeat_seconds=time.monotonic()-ti;order=np.arange(len(samples))[::-1];ti=time.monotonic();reverse=model.embed([samples[i] for i in order],layers='last',degrees=0,per_atom=False,batch_size=1).numpy()[np.argsort(order)];reorder_seconds=time.monotonic()-ti
assert np.allclose(first,repeat,atol=c['atol'],rtol=c['rtol']);assert np.allclose(first,reverse,atol=c['atol'],rtol=c['rtol']);np.save(out/'embeddings.npy',first);rows.iloc[successful].to_csv(out/'embedding-rows.csv',index=False)
receipt={'status':'complete' if len(successful)==32 else 'partial_explicit_failures','requested':32,'successful':len(successful),'failed':32-len(successful),'dimensions':256,'model_loaded_seconds':load_time,'runtime_seconds':time.monotonic()-start,'repeat_seconds':repeat_seconds,'reorder_seconds':reorder_seconds,'repeat_max_abs':float(np.max(abs(first-repeat))),'reorder_max_abs':float(np.max(abs(first-reverse))),'representation':'last-after-finalnorm-degree0-atommean','geometry_seed':42,'coordinate_units':'angstrom','execution':model.execution,'packages':{p:importlib.metadata.version(p) for p in ['atom-jepa','torch','numpy','rdkit','e3nn','torch-geometric']},'outcomes':records,'source_sha256':sha(__file__),'config_sha256':sha(sys.argv[1]),'no_fits':True,'no_neutralization_or_fragment_removal':True,'input_labels_loaded':False};(out/'COMPLETE.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='outcomes'}),flush=True)
