import json,sys,subprocess,os,hashlib,time,importlib.metadata
from pathlib import Path
c=json.loads(Path(sys.argv[1]).read_text());out=Path(c['output']);out.mkdir(parents=True,exist_ok=False)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for k,v in c['files'].items():assert sha(v['path'])==v['sha256'],k
def size():return sum(p.stat().st_size for p in Path(c['task_root']).rglob('*') if p.is_file())
assert size()<1024**3
before={p:importlib.metadata.version(p) for p in ['torch','numpy','rdkit']};assert before['torch'].startswith('2.8.')
d=json.loads(Path(c['files']['dependencies']['path']).read_text());wheels=[]
for r in d['wheels']:assert sha(r['wheel'])==r['sha256'];wheels.append(r['wheel'])
subprocess.run(['/opt/homebrew/bin/uv','pip','install','--no-index','--no-deps','--python',sys.executable,'--target',c['deps_target'],*wheels],check=True)
after={p:importlib.metadata.version(p) for p in before};assert before==after
assert not list(Path(c['deps_target']).glob('torch-*.dist-info'));assert size()<1024**3
(out/'environment-receipt.json').write_text(json.dumps({'shared_before':before,'shared_after':after,'isolated_deps':c['deps_target'],'total_task_bytes_after_install':size(),'no_shared_mutation':True},indent=2)+'\n')
env=os.environ.copy();env['PYTHONPATH']=c['deps_target'];start=time.monotonic()
try:r=subprocess.run([sys.executable,'night/p9a_smoke.py',sys.argv[1]],env=env,timeout=c['timeout_seconds']);code=r.returncode
except subprocess.TimeoutExpired:code=124
receipt={'returncode':code,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':c['timeout_seconds'],'task_bytes':size(),'no_fits':True,'private':True};(out/'supervisor.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True);sys.exit(code)
