import sys,json,hashlib,shutil,collections,gc
from pathlib import Path
B=Path(__file__).resolve().parents[1];sys.path.insert(0,str(B/'p7r/full-worktree'))
import torch
S=B/'p10/stage';R=B/'p7r/recovered/full-results';remote=json.loads((B/'p7r/remote-file-manifest.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tensor_hash(d):
 h=hashlib.sha256()
 for k in sorted(d):
  v=d[k].detach().cpu().contiguous();h.update(k.encode());h.update(str(v.dtype).encode());h.update(str(tuple(v.shape)).encode());h.update(v.numpy().tobytes())
 return h.hexdigest()
shutil.copytree(B/'p7r/stage/common',S/'common',dirs_exist_ok=True);shutil.copytree(B/'p7r/stage/features',S/'features',dirs_exist_ok=True);records=[]
for parent in ['zero','repaired']:
 for fold in range(5):
  src=R/f'{parent}_f{fold}';out=S/'parents'/f'{parent}_f{fold}';out.mkdir(parents=True,exist_ok=True);p=next((src/'checkpoints').glob('*.ckpt'));expected=remote['files'][str(p.relative_to(R))]['sha256'];assert sha(p)==expected
  ck=torch.load(p,map_location='cpu',weights_only=False);state=ck['state_dict'];filtered=collections.OrderedDict((k,v.detach().cpu().clone()) for k,v in state.items() if not k.startswith(('predictor.criterion.','metrics.')))
  th=tensor_hash(filtered);dest=out/'model-only.pt';torch.save({'prediction_state':filtered,'source_checkpoint_sha256':expected,'prediction_tensor_sha256':th,'parent_epoch':int(ck['epoch']),'excluded_scope':'optimizer/scheduler and loss-metric buffers only'},dest);loaded=torch.load(dest,map_location='cpu',weights_only=False);assert tensor_hash(loaded['prediction_state'])==th
  for k,v in filtered.items():assert torch.equal(v,state[k]) and v.dtype==state[k].dtype
  copied={}
  for name in ['initial.json','feature_transform.json','complete.json','test_raw.csv']:
   assert sha(src/name)==remote['files'][str((src/name).relative_to(R))]['sha256'];shutil.copy2(src/name,out/name);copied[name]=sha(out/name)
  records.append({'parent':parent,'fold':fold,'original_checkpoint_sha256':expected,'model_only_sha256':sha(dest),'prediction_tensor_sha256':th,'predictive_tensor_count':len(filtered),'exact_tensor_parity':True,'parent_epoch':int(ck['epoch']),'bytes':dest.stat().st_size,'files':copied});del ck,state,filtered,loaded;gc.collect()
manifest={'scope':'P10 matched continuation, no parent fullcheckpoint mutated','parents':records,'parent_source_commit':'8fad9cdf0aba0e1974eba3e7a8e11c6b3b42ce41','parent_run':'c95e19e7-e392-4a10-84c5-75d5af23f628','row_and_fold_inputs_unchanged':True,'files':{str(p.relative_to(S)):sha(p) for p in S.rglob('*') if p.is_file()}};(S/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'parent_exports':len(records),'bytes':sum(x['bytes'] for x in records),'all_predictive_tensors_exact':True,'fits':0}))
