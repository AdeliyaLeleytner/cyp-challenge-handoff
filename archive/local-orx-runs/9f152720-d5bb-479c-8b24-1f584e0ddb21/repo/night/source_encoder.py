import json,sys,time,hashlib,importlib.metadata
from pathlib import Path
import numpy as np,pandas as pd,torch
from atom_jepa import AtomJEPA
c=json.load(open(sys.argv[1]));out=Path(c['output']);start=time.monotonic();torch.set_num_threads(c['threads']);torch.manual_seed(42);np.random.seed(42)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert importlib.metadata.version('atom-jepa')=='0.3.0' and torch.__version__.startswith('2.8.');audit=json.load(open(c['files']['coordinate_audit']['path']));assert audit['status']=='complete_pass' and audit['persisted_coordinate_rows']==5655 and not audit['flagged'];rows=pd.read_csv(c['files']['rows']['path']);old=np.load(c['files']['old_postnorm']['path']);assert len(rows)==5655 and rows.Molecule_Name.is_unique and old.shape==(5655,256) and np.isfinite(old).all();samples={}
for record in c['coordinate_files']:
 z=np.load(record['path'])
 for key in z.files:
  if not key.startswith('z_'):continue
  i=int(key[2:]);assert i not in samples;samples[i]={'atomic_numbers':z[key],'node_coordinates':z[f'pos_{i}']}
assert set(samples)==set(range(5655))
model=AtomJEPA.from_pretrained(c['checkpoint'],device='cpu',precision='fp32',cuequivariance=False,compile=False);model.eval();load_seconds=time.monotonic()-start
if c['mode']=='smoke':
 chosen=pd.read_csv(c['files']['smoke_rows']['path']);ix=pd.Series(np.arange(len(rows)),index=rows.Molecule_Name).loc[chosen.Molecule_Name].to_numpy();assert rows.SMILES.iloc[ix].tolist()==chosen.SMILES.tolist();data=[samples[int(i)] for i in ix];timings={}
 def call(name,data,layers,batch):
  t=time.monotonic();v=model.embed(data,layers=layers,degrees=0,per_atom=False,batch_size=batch).numpy();timings[name]=time.monotonic()-t;assert np.isfinite(v).all();return v
 all9=call('all9_batch8',data,c['layers'],c['batch_size']);assert all9.shape==(32,9,256);direct=call('direct_pre_block8_batch1',data,8,1);repeat=call('repeat_all9_batch8',data,c['layers'],c['batch_size']);rev=call('reordered_all9_batch8',data[::-1],c['layers'],c['batch_size'])[::-1];checks={}
 for name,value,ref in [('old_postnorm',all9[:,8,:],old[ix]),('pre_slice_matches_direct8',all9[:,7,:],direct),('repeat',repeat,all9),('reorder',rev,all9)]:checks[name]={'allclose':bool(np.allclose(value,ref,atol=c['atol'],rtol=c['rtol'])),'max_abs':float(abs(value-ref).max())}
 np.save(out/'pooled-layers-and-postnorm.npy',all9);np.save(out/'last-pre-norm.npy',all9[:,7,:]);chosen.to_csv(out/'rows.csv',index=False);report={'status':'pass' if all(v['allclose'] for v in checks.values()) else 'parity_failed','rows':32,'checks':checks,'timing_seconds':timings,'load_and_inputs_seconds':load_seconds,'selected_pre_vs_old_post_mean_absolute_difference':float(abs(all9[:,7,:]-old[ix]).mean()),'selected_pre_vs_old_post_max_absolute_difference':float(abs(all9[:,7,:]-old[ix]).max())}
else:
 assert c['mode']=='full';all_pre=np.full((5655,8,256),np.nan,np.float32);post=np.full((5655,256),np.nan,np.float32);out.joinpath('shards').mkdir();max_post_error=0.;shard_start=0;ledger=[]
 for begin in range(0,5655,c['batch_size']):
  end=min(begin+c['batch_size'],5655);t=time.monotonic();value=model.embed([samples[i] for i in range(begin,end)],layers=c['layers'],degrees=0,per_atom=False,batch_size=c['batch_size']).numpy();assert value.shape==(end-begin,9,256) and np.isfinite(value).all();all_pre[begin:end]=value[:,:8,:];post[begin:end]=value[:,8,:];difference=float(abs(post[begin:end]-old[begin:end]).max());max_post_error=max(max_post_error,difference);parity=bool(np.allclose(post[begin:end],old[begin:end],atol=c['atol'],rtol=c['rtol']));record={'start':begin,'end':end,'seconds':time.monotonic()-t,'old_postnorm_max_abs':difference,'old_postnorm_parity':parity};ledger.append(record)
  with (out/'batch-outcomes.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
  if end%128==0 or end==5655 or not parity:
   file=out/'shards'/f'{shard_start:05d}-{end:05d}.npz';np.savez(file,indices=np.arange(shard_start,end),pre_layers=all_pre[shard_start:end],postnorm=post[shard_start:end]);shard_start=end;print(json.dumps({'rows_persisted':end,'total':5655,'elapsed_seconds':time.monotonic()-start,'old_postnorm_max_abs':max_post_error}),flush=True)
  assert parity,'oldpostnorm parityfailed; outputs preserved, no fill or retry'
 assert np.isfinite(all_pre).all() and np.isfinite(post).all();np.save(out/'all-pre-norm-layers.npy',all_pre);np.save(out/'last-pre-norm.npy',all_pre[:,7,:]);np.save(out/'post-norm-reference.npy',post);rows.to_csv(out/'rows.csv',index=False);report={'status':'pass','rows':5655,'selected_shape':[5655,256],'all_pre_layer_shape':[5655,8,256],'old_postnorm_parity':True,'old_postnorm_max_abs':max_post_error,'load_and_inputs_seconds':load_seconds,'selected_pre_vs_old_post_mean_absolute_difference':float(abs(all_pre[:,7,:]-old).mean()),'selected_feature_sha256':sha(out/'last-pre-norm.npy'),'all_pre_layers_sha256':sha(out/'all-pre-norm-layers.npy'),'rows_sha256':sha(out/'rows.csv'),'shards':{f.name:sha(f) for f in sorted((out/'shards').glob('*.npz'))},'other_layers_provenance_only':True}

report.update(runtime_seconds=time.monotonic()-start,source_sha256=sha(__file__),config_sha256=sha(sys.argv[1]),execution=model.execution,packages={x:importlib.metadata.version(x) for x in ['atom-jepa','torch','numpy','e3nn','torch-geometric']},coordinates_reused_unchanged=True,new_geometry_or_CIP_audit=False,target_labels_used=False,declared_feature='block8 beforefinalnorm,degree0,atommean256');(out/'COMPLETE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);assert report['status']=='pass'
