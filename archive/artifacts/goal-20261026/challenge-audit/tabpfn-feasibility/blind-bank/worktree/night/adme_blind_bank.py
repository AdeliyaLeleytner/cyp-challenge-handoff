"""Exact frozen fingerprint reproduction, then blind-bank inference; no fitting."""
from pathlib import Path
import hashlib,json,time,platform,importlib.metadata
import numpy as np,pandas as pd,torch
from chemprop import data,featurizers
from chemprop.data.collate import collate_batch
from chemprop.models.model import MPNN

ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):Path(p).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def event(name,**kw):print(json.dumps({'event':name,**kw}),flush=True)
def ordered_hash(frame):return hashlib.sha256(json.dumps(frame[['Molecule_Name','SMILES']].to_dict('records'),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def state_hash(model):
 h=hashlib.sha256()
 for key,tensor in sorted(model.state_dict().items()):
  h.update(key.encode());h.update(str(tensor.dtype).encode());h.update(str(tuple(tensor.shape)).encode());h.update(tensor.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())
 return h.hexdigest()
def fingerprint(model,smiles,label,out):
 ds=data.MoleculeDataset([data.MoleculeDatapoint.from_smi(s,[0.]) for s in smiles],featurizers.SimpleMoleculeMolGraphFeaturizer());ds.cache=True
 dl=torch.utils.data.DataLoader(ds,num_workers=0,batch_size=256,shuffle=False,drop_last=False,collate_fn=collate_batch)
 vectors=[]
 with torch.inference_mode():
  for index,b in enumerate(dl):
   bmg,Vd,Xd,*_=b;bmg.to('cuda:0');Vd=Vd.to('cuda:0') if Vd is not None else None;Xd=Xd.to('cuda:0') if Xd is not None else None
   vectors.append(model.fingerprint(bmg,Vd,Xd).cpu().numpy());event('encoder_batch_complete',scope=label,batch=index,rows=sum(len(x) for x in vectors))
 result=np.concatenate(vectors);assert result.shape==(len(smiles),600) and result.dtype==np.float32 and np.isfinite(result).all()
 np.save(out,result);return result
def main():
 cfg=json.loads((ROOT/'encoder_config.json').read_text());assert cfg['atol']==cfg['rtol']==1e-5
 assert time.time()<cfg['lease_deadline_unix']-600,'Lease recovery margin reached'
 for key,item in cfg['files'].items():assert digest(item['path'])==item['sha256'],key
 expected=cfg['required_runtime'];actual={p:importlib.metadata.version(p) for p in expected};assert actual==expected
 assert platform.python_version()=='3.11.13' and torch.cuda.is_available()
 precision={'matmul_precision':torch.get_float32_matmul_precision(),'cuda_allow_tf32':torch.backends.cuda.matmul.allow_tf32,'cudnn_allow_tf32':torch.backends.cudnn.allow_tf32,'default_dtype':str(torch.get_default_dtype()),'autocast_enabled':torch.is_autocast_enabled()}
 assert precision['matmul_precision']=='highest' and not precision['cuda_allow_tf32'] and not precision['autocast_enabled'],'Unexpected precision override; inspect historical source rather than change tolerance'
 out=Path(cfg['output_dir']);out.mkdir(parents=True,exist_ok=True);assert not (out/'complete.json').exists()
 save(out/'runtime.json',{'actual_runtime':actual,'python':platform.python_version(),'precision':precision,'gpu':torch.cuda.get_device_name(0)});save(out/'config.json',cfg)
 train=pd.read_csv(cfg['files']['official_train']['path'],usecols=['Molecule_Name','SMILES']);blind=pd.read_csv(cfg['files']['official_test']['path'],usecols=['Molecule_Name','SMILES']);source=pd.read_csv(cfg['files']['adme_source_rows']['path'],usecols=['Molecule_Name','SMILES'])
 assert len(train)==4905 and len(blind)==750 and train.Molecule_Name.is_unique and blind.Molecule_Name.is_unique
 assert train.Molecule_Name.tolist()==source.Molecule_Name.tolist() and train.SMILES.tolist()==source.SMILES.tolist()
 assert not set(train.Molecule_Name)&set(blind.Molecule_Name)
 cached=np.load(cfg['files']['adme_matrix']['path'],allow_pickle=False);assert cached.shape==(4905,600) and np.isfinite(cached).all()
 model=MPNN.load_from_file(cfg['files']['adme_checkpoint']['path']).eval().to('cuda:0');before=state_hash(model);start=time.time()
 reproduced=fingerprint(model,train.SMILES.tolist(),'training_canary',out/'reproduced-training-bank.npy')
 diff=np.abs(reproduced.astype(np.float64)-cached.astype(np.float64));bound=cfg['atol']+cfg['rtol']*np.abs(cached.astype(np.float64));ok=diff<=bound
 canary={'rows':4905,'dimensions':600,'atol':cfg['atol'],'rtol':cfg['rtol'],'all_within_tolerance':bool(ok.all()),'failed_values':int((~ok).sum()),'max_abs_difference':float(diff.max()),'max_scaled_error':float((diff/bound).max()),'reference_sha256':cfg['files']['adme_matrix']['sha256'],'reproduced_sha256':digest(out/'reproduced-training-bank.npy'),'input_ids_smiles_order_sha256':ordered_hash(train),'precision':precision}
 save(out/'canary-comparison.json',canary);event('full_training_canary_comparison',**canary)
 if not ok.all():
  where=np.argwhere(~ok);save(out/'canary-failures.json',[{'row':int(i),'dimension':int(j),'Molecule_Name':train.iloc[i].Molecule_Name,'reference':float(cached[i,j]),'reproduced':float(reproduced[i,j]),'difference':float(diff[i,j])} for i,j in where[:100]])
  raise RuntimeError('Frozen-cache parity failed; no blind bank generated, no tolerance relaxation')
 assert time.time()<cfg['lease_deadline_unix']-600,'Lease recovery margin reached before blind inference'
 bank=fingerprint(model,blind.SMILES.tolist(),'blind750',out/'blind-adme600.npy');assert state_hash(model)==before,'Encoder state changed during inference'
 mapping=pd.read_csv(cfg['files']['id_map']['path']);mapping=mapping[mapping.source.eq('official-test.csv')].set_index('Molecule_Name').loc[blind.Molecule_Name];assert len(mapping)==750 and mapping.request_id.is_unique
 from rdkit import Chem
 for s,requested,rid in zip(blind.SMILES,mapping.request_smiles,mapping.request_id):assert Chem.MolToSmiles(Chem.MolFromSmiles(s))==requested and hashlib.sha256(requested.encode()).hexdigest()==rid
 rows=blind.copy();rows['request_id']=mapping.request_id.to_numpy();rows.to_csv(out/'blind-rows.csv',index=False)
 receipt=json.loads((ROOT/'blind_receipt_template.json').read_text());receipt.update(status='complete',approved=True,actual_runtime=actual,producer_run_id=ROOT.parent.name,producer_commit=None,shape_verified=True,all_finite=True,output_matrix_sha256=digest(out/'blind-adme600.npy'),exact_input_ids_smiles_order_sha256=ordered_hash(blind),output_ids_smiles_order_sha256=ordered_hash(rows),canary_comparison=canary,encoder_state_unchanged=True,encoder_state_sha256=before,producer_current_source_sha256=digest(__file__),scope='Frozen encoder feature identity only; not final acquisition/model/submission approval.',producer_commit_annotation='Recovered receipt must bind the verified ORX recorded commit before downstream use.')
 save(out/'blind-embedding-receipt.remote.json',receipt);save(out/'complete.json',{'status':'complete','seconds':time.time()-start,'training_canary_rows':4905,'blind_rows':750,'dimensions':600,'fits':0,'training_labels_used':False,'all_canary_values_within_tolerance':True});event('verified_blind_bank_complete',seconds=time.time()-start,blind_rows=750,dimensions=600,canary_max_abs=canary['max_abs_difference'])
if __name__=='__main__':main()
