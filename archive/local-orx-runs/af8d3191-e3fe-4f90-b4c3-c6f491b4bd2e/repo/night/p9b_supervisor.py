import json,sys,subprocess,os,hashlib,time
from pathlib import Path
c=json.loads(Path(sys.argv[1]).read_text());out=Path(c['output']);out.mkdir(parents=True,exist_ok=False)
for k,v in c['files'].items():assert hashlib.sha256(Path(v['path']).read_bytes()).hexdigest()==v['sha256'],k
assert Path(c['deps_target']).exists()
env=os.environ.copy();env['PYTHONPATH']=c['deps_target'];start=time.monotonic()
try:r=subprocess.run([sys.executable,'night/p9b_bank.py',sys.argv[1]],env=env,timeout=c['timeout_seconds']);code=r.returncode
except subprocess.TimeoutExpired:code=124
size=sum(x.stat().st_size for root in [Path(c['task_root']),Path(c['deps_target']).parent] for x in root.rglob('*') if x.is_file());assert size<1024**3
rec={'returncode':code,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':c['timeout_seconds'],'p9a_plus_p9b_bytes':size,'no_fits':True,'private':True};(out/'supervisor.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec),flush=True);sys.exit(code)
