import json,sys,time,hashlib,shutil,importlib.metadata
from pathlib import Path
import numpy as np,pandas as pd,torch
from rdkit import Chem
from rdkit.Chem import AllChem
from atom_jepa import AtomJEPA
from p9_identity import validate
c=json.loads(Path(sys.argv[1]).read_text());out=Path(c['output']);start=time.monotonic();torch.set_num_threads(c['threads']);torch.manual_seed(c['seed']);np.random.seed(c['seed'])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def savej(x,p):Path(p).write_text(json.dumps(x,indent=2)+'\n')
previous=json.load(open(c['previous_snapshot']['path']))
for key,r in previous['files'].items():assert sha(r['path'])==r['sha256'],key
assert previous['terminal'] and previous['source_commit']=='8ab23c4d9513919e71dd50f6e25b0cbc75eb42df'
oldcfg=json.load(open(previous['files']['config']['path']))
for k in ['seed','max_iters','dimensions','atol','rtol','threads','batch_size','checkpoint','deps_target']:assert oldcfg[k]==c[k],k
for k in ['weight','model_config','rows','official_train','official_test','smoke_rows','smoke_embeddings']:assert oldcfg['files'][k]['sha256']==c['files'][k]['sha256'],k
rows=pd.read_csv(c['files']['rows']['path']);assert len(rows)==5655 and rows.Molecule_Name.is_unique;oldrecords=[json.loads(x) for x in Path(previous['files']['outcomes']['path']).read_text().splitlines()];oldmap={x['row']:x for x in oldrecords};assert len(oldmap)==len(oldrecords);idx=np.load(previous['files']['indices']['path']);vectors=np.load(previous['files']['features']['path']);assert len(idx)==len(set(idx.tolist())) and vectors.shape==(len(idx),256) and vectors.dtype==np.float32 and np.isfinite(vectors).all();coords={};audit=[]
for key,r in previous['files'].items():
 if not key.startswith('coords_'):continue
 source=Path(r['path']);co=np.load(source)
 for name in co.files:
  if not name.startswith('z_'):continue
  i=int(name[2:]);assert i not in coords;z=co[name];pos=co[f'pos_{i}'];checks=validate(rows.SMILES.iloc[i],z,pos);coords[i]=(z,pos);audit.append({'row':i,'id':rows.Molecule_Name.iloc[i],'checks':checks})
 shutil.copy2(source,out/('coordinates-prior-'+source.name.removeprefix('coordinates-')))
assert all(int(i) in coords for i in idx),'persistedvector lacks auditedcoordinate';bank=np.full((5655,256),np.nan,np.float32);bank[idx]=vectors;newrecords=[]
for i in idx:
 i=int(i);r=oldmap[i];assert r['status']=='success' and r['id']==rows.Molecule_Name.iloc[i] and r['smiles']==rows.SMILES.iloc[i];newrecords.append({**r,'execution_origin':'prior:'+previous['run_id'],'revalidated_with_modern_CIP':True})
shutil.copy2(previous['files']['outcomes']['path'],out/'original-attempt-ledger.jsonl');savej({'status':'pass','saved_coordinate_rows':len(audit),'reused_embedding_rows':len(idx),'all_saved_coords_revalidated':True,'validator_sha256':sha(Path(__file__).with_name('p9_identity.py')),'checks':audit},out/'REUSE_AUDIT.json')
print(json.dumps({'reused':len(idx),'missing':5655-len(idx),'all_saved_coordinate_checks':'pass'}),flush=True)
model=AtomJEPA.from_pretrained(c['checkpoint'],device='cpu',precision='fp32',cuequivariance=False,compile=False);model.eval();reused_set=set(idx.tolist());missing=[i for i in range(5655) if i not in reused_set];newcoords={};failures=[]
with (out/'row-outcomes.jsonl').open('w') as f:
 for r in newrecords:f.write(json.dumps(r)+'\n')
for step,i in enumerate(missing):
 row=rows.iloc[i];t=time.monotonic();r={'row':i,'id':row.Molecule_Name,'smiles':row.SMILES,'role':row.role,'status':'failed','execution_origin':'resume','prior_attempt':oldmap.get(i)}
 try:
  if row.Molecule_Name==c['fixed_failed_id']:
   co=np.load(c['files']['failed_row_coords']['path']);z=co['z'];pos=co['pos'];r.update(mmff_status=0,mmff_energy=-42.577177380436176,coordinate_provenance='samefixedprotocol fullprecisionregeneration verifiedrepeat;originalfailedcoordsnotpersisted;notroundedSDF')
  else:
   original=Chem.MolFromSmiles(row.SMILES);assert original;mol=Chem.AddHs(original);params=AllChem.ETKDGv3();params.randomSeed=c['seed'];params.pruneRmsThresh=-1.;params.enforceChirality=True;confids=list(AllChem.EmbedMultipleConfs(mol,numConfs=1,params=params));assert len(confids)==1 and AllChem.MMFFHasAllMoleculeParams(mol);opt=AllChem.MMFFOptimizeMoleculeConfs(mol,numThreads=1,maxIters=c['max_iters'],mmffVariant='MMFF94');assert opt[0][0] in [0,1];assert Chem.MolToSmiles(Chem.RemoveHs(mol),isomericSmiles=True)==row.canonical_isomeric;z=np.array([a.GetAtomicNum() for a in mol.GetAtoms()],np.int64);pos=mol.GetConformer(confids[0]).GetPositions().astype(np.float32);r.update(mmff_status=int(opt[0][0]),mmff_energy=float(opt[0][1]),coordinate_provenance='unchangedfixedprotocolforpreviouslymissingrow')
  checks=validate(row.SMILES,z,pos);v=model.embed([{'atomic_numbers':z,'node_coordinates':pos}],layers='last',degrees=0,per_atom=False,batch_size=1).numpy();assert v.shape==(1,256) and np.isfinite(v).all();bank[i]=v[0];newcoords[f'z_{i}']=z;newcoords[f'pos_{i}']=pos;r.update(status='success',checks=checks,coordinate_sha256=hashlib.sha256(pos.tobytes()).hexdigest())
 except Exception as e:r['error']=type(e).__name__+': '+str(e);failures.append(r)
 r['seconds']=time.monotonic()-t
 with (out/'row-outcomes.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
 if (step+1)%100==0 or step==len(missing)-1:
  np.save(out/'embeddings-progress.npy',bank);np.savez_compressed(out/f'coordinates-resume-through-{i:05d}.npz',**newcoords);newcoords={};print(json.dumps({'new_rows':step+1,'new_required':len(missing),'success_total':int(np.isfinite(bank).all(1).sum()),'failed_new':len(failures),'elapsed_seconds':time.monotonic()-start}),flush=True)
assert np.array_equal(bank[idx],vectors),'reusedvectorschanged';np.save(out/'embeddings.npy',bank);rows.to_csv(out/'embedding-rows.csv',index=False);smoke=pd.read_csv(c['files']['smoke_rows']['path']);lookup={x:i for i,x in enumerate(rows.Molecule_Name)};si=[lookup[x] for x in smoke.Molecule_Name];old=np.load(c['files']['smoke_embeddings']['path']);assert np.isfinite(bank[si]).all() and np.allclose(bank[si],old,atol=1e-5,rtol=1e-5);success=int(np.isfinite(bank).all(1).sum());rec={'status':'complete' if success==5655 else 'partial_explicit_failures','requested':5655,'successful':success,'failed':5655-success,'reused':len(idx),'newly_computed':success-len(idx),'all_reused_vectors_bitwise_identical':True,'all_saved_coordinate_chunks_revalidated':True,'validator':'originalreferencegraph+modernCIPcleared+atomorientation+bondstereo+enhancedgroups','smoke_sentinel_max_abs':float(abs(bank[si]-old).max()),'runtime_seconds':time.monotonic()-start,'source_sha256':sha(__file__),'config_sha256':sha(sys.argv[1]),'validator_sha256':sha(Path(__file__).with_name('p9_identity.py')),'embeddings_sha256':sha(out/'embeddings.npy'),'rows_sha256':sha(out/'embedding-rows.csv'),'prior_run':previous['run_id'],'prior_source':previous['source_commit'],'packages':{x:importlib.metadata.version(x) for x in ['atom-jepa','torch','numpy','rdkit','e3nn','torch-geometric']},'scientific_model_geometry_pins_unchanged':True,'no_fits':True,'no_CPU_GPU_mix':True,'failures':failures};savej(rec,out/'COMPLETE.json');print(json.dumps({k:v for k,v in rec.items() if k!='failures'}),flush=True)
