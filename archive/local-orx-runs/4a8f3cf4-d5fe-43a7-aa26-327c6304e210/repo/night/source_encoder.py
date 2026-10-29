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
assert c['mode']=='full' and c['layers']==[8,'last'] and c['batch_size']==1
ix=np.array(c['repair_probe_indices']);data=[samples[int(i)] for i in ix];timings={}
def call(name,items,layers):
 t=time.monotonic();value=model.embed(items,layers=layers,degrees=0,per_atom=False,batch_size=1).numpy();timings[name]=time.monotonic()-t;assert np.isfinite(value).all();return value
all9=call('all9_reference',data,c['reference_probe_layers']);lean=call('selected_two',data,c['layers']);rev=call('selected_two_reversed',data[::-1],c['layers'])[::-1];assert all9.shape==(8,9,256) and lean.shape==(8,2,256)
checks={'pre_vs_all9':bool(np.allclose(lean[:,0],all9[:,7],atol=c['atol'],rtol=c['rtol'])),'post_vs_old':bool(np.allclose(lean[:,1],old[ix],atol=c['atol'],rtol=c['rtol'])),'reorder':bool(np.allclose(lean,rev,atol=c['atol'],rtol=c['rtol']))};projection=max(timings['selected_two'],timings['selected_two_reversed'])/8*5655;remaining=c['timeout_seconds']-(time.monotonic()-start)
probe={'checks':checks,'indices':ix.tolist(),'IDs':rows.Molecule_Name.iloc[ix].tolist(),'timing_seconds':timings,'pre_vs_all9_max_abs':float(abs(lean[:,0]-all9[:,7]).max()),'pre_vs_all9_bitwise':bool(np.array_equal(lean[:,0],all9[:,7])),'post_vs_old_max_abs':float(abs(lean[:,1]-old[ix]).max()),'projection_seconds':projection,'remaining_seconds':remaining,'reserve_seconds':60,'scientific_feature_unchanged':True,'unused_layer_provenance_capture_omitted':True};np.save(out/'capture-probe.npy',lean);(out/'CAPTURE_PROBE.json').write_text(json.dumps(probe,indent=2)+'\n');print(json.dumps(probe),flush=True)
assert all(checks.values()),'Selected-output capture parityfailed; no furtherchanges'
if projection+60>remaining:
 report={'status':'runtime_does_not_fit_remaining_allocation','probe':probe,'bank_not_started':True,'source_sha256':sha(__file__),'config_sha256':sha(sys.argv[1])};(out/'COMPLETE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);sys.exit(0)
pre=np.full((5655,256),np.nan,np.float32);post=np.full((5655,256),np.nan,np.float32);out.joinpath('shards').mkdir();max_error=0.;shard_start=0
for i in range(5655):
 t=time.monotonic();value=model.embed([samples[i]],layers=c['layers'],degrees=0,per_atom=False,batch_size=1).numpy();assert value.shape==(1,2,256) and np.isfinite(value).all();pre[i]=value[0,0];post[i]=value[0,1];delta=float(abs(post[i]-old[i]).max());max_error=max(max_error,delta);parity=bool(np.allclose(post[i],old[i],atol=c['atol'],rtol=c['rtol']));record={'start':i,'end':i+1,'seconds':time.monotonic()-t,'old_postnorm_max_abs':delta,'old_postnorm_parity':parity}
 with (out/'batch-outcomes.jsonl').open('a') as handle:handle.write(json.dumps(record)+'\n')
 if (i+1)%128==0 or i==5654 or not parity:
  end=i+1;file=out/'shards'/f'{shard_start:05d}-{end:05d}.npz';np.savez(file,indices=np.arange(shard_start,end),pre_last=pre[shard_start:end],postnorm=post[shard_start:end]);shard_start=end;print(json.dumps({'rows_persisted':end,'total':5655,'elapsed_seconds':time.monotonic()-start,'old_postnorm_max_abs':max_error}),flush=True)
 assert parity,'oldpostnorm parityfailed; preservedoutputs,no tolerancechanges'
assert np.isfinite(pre).all() and np.isfinite(post).all();np.save(out/'last-pre-norm.npy',pre);np.save(out/'post-norm-reference.npy',post);rows.to_csv(out/'rows.csv',index=False);report={'status':'pass','rows':5655,'selected_shape':[5655,256],'old_postnorm_parity':True,'old_postnorm_max_abs':max_error,'selected_feature_sha256':sha(out/'last-pre-norm.npy'),'rows_sha256':sha(out/'rows.csv'),'shards':{f.name:sha(f) for f in sorted((out/'shards').glob('*.npz'))},'stored_only_declared_pre_and_post_reference':True,'runtime_seconds':time.monotonic()-start,'source_sha256':sha(__file__),'config_sha256':sha(sys.argv[1]),'execution':model.execution,'packages':{x:importlib.metadata.version(x) for x in ['atom-jepa','torch','numpy','e3nn','torch-geometric']},'coordinates_reused_unchanged':True,'new_geometry_or_CIP_audit':False,'target_labels_used':False,'declared_feature':'block8 beforefinalnorm,degree0,atommean256'};(out/'COMPLETE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
