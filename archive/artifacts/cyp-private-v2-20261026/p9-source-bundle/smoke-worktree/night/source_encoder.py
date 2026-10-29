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
else:raise ValueError('Onlysmoke implemented inthisnode')
report.update(runtime_seconds=time.monotonic()-start,source_sha256=sha(__file__),config_sha256=sha(sys.argv[1]),execution=model.execution,packages={x:importlib.metadata.version(x) for x in ['atom-jepa','torch','numpy','e3nn','torch-geometric']},coordinates_reused_unchanged=True,new_geometry_or_CIP_audit=False,target_labels_used=False,declared_feature='block8 beforefinalnorm,degree0,atommean256');(out/'COMPLETE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);assert report['status']=='pass'
