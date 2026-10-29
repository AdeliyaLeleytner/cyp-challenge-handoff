"""Unlaunched fixed-coordinate GPU parity/throughput worker; no training."""
import argparse,json,time,hashlib,importlib.metadata
from pathlib import Path
import numpy as np,pandas as pd,torch
from atom_jepa import AtomJEPA
pa=argparse.ArgumentParser();pa.add_argument('--inputs',type=Path,required=True);pa.add_argument('--output',type=Path,required=True);a=pa.parse_args();a.output.mkdir(parents=True,exist_ok=False);manifest=json.load(open(a.inputs/'manifest.json'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for k,h in manifest['files'].items():assert sha(a.inputs/k)==h,k
assert torch.__version__.startswith('2.6.') and torch.cuda.is_available();torch.set_num_threads(2);torch.manual_seed(42);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.set_float32_matmul_precision('highest');rows=pd.read_csv(a.inputs/'smoke-rows.csv');base=np.load(a.inputs/'embeddings.npy');coords=np.load(a.inputs/'coordinates.npz');assert len(rows)==32 and base.shape==(32,256);samples=[{'atomic_numbers':coords[f'z_{i}'],'node_coordinates':coords[f'pos_{i}']} for i in range(32)];t=time.monotonic();m=AtomJEPA.from_pretrained(str(a.inputs/'checkpoint'),device='cuda',precision='fp32',cuequivariance=False,compile=False);m.eval();torch.cuda.synchronize();load=time.monotonic()-t;torch.cuda.reset_peak_memory_stats()
def run(samples,batch):
 torch.cuda.synchronize();start=time.monotonic();v=m.embed(samples,layers='last',degrees=0,per_atom=False,batch_size=batch).numpy();torch.cuda.synchronize();return v,time.monotonic()-start
v,t1=run(samples,1);repeat,t2=run(samples,1);rev,t3=run(samples[::-1],1);rev=rev[::-1];batch,t8=run(samples,8)
checks={}
for name,value,ref in [('cpu_gpu',v,base),('repeat',repeat,v),('reorder',rev,v),('batch8',batch,v)]:
 assert value.shape==(32,256) and np.isfinite(value).all();checks[name]={'allclose':bool(np.allclose(value,ref,atol=1e-5,rtol=1e-5)),'max_abs':float(np.max(abs(value-ref))),'max_relative_with_1e-8floor':float(np.max(abs(value-ref)/np.maximum(abs(ref),1e-8)))}
np.save(a.output/'gpu-embeddings-batch1.npy',v);np.save(a.output/'gpu-embeddings-batch8.npy',batch);rows.to_csv(a.output/'embedding-rows.csv',index=False);r={'status':'pass' if all(x['allclose'] for x in checks.values()) else 'parity_failed','checks':checks,'timing_seconds':{'load':load,'forward32_batch1':t1,'repeat32_batch1':t2,'reverse32_batch1':t3,'forward32_batch8':t8},'gpu':torch.cuda.get_device_name(),'torch':torch.__version__,'cuda':torch.version.cuda,'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'execution':m.execution,'packages':{x:importlib.metadata.version(x) for x in ['atom-jepa','e3nn','torch-geometric','numpy']},'exact_same_CPU_coordinates':True,'no_geometry_regeneration_in_this_worker':True,'input_manifest_sha256':sha(a.inputs/'manifest.json'),'source_sha256':sha(__file__),'no_fits':True};(a.output/'RESULT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);assert r['status']=='pass'
