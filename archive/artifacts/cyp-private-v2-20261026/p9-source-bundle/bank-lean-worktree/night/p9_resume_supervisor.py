import json,sys,subprocess,os,hashlib,time
from pathlib import Path
c=json.loads(Path(sys.argv[1]).read_text());assert c['previous_snapshot'],'terminalprior-snapshot pin absent';out=Path(c['output']);out.mkdir(parents=True,exist_ok=False)
for k,v in {**c['files'],'previous_snapshot':c['previous_snapshot']}.items():assert hashlib.sha256(Path(v['path']).read_bytes()).hexdigest()==v['sha256'],k
env=os.environ.copy();env['PYTHONPATH']=c['deps_target'];start=time.monotonic()
try:r=subprocess.run([sys.executable,'night/p9_resume_bank.py',sys.argv[1]],env=env,timeout=c['timeout_seconds']);code=r.returncode
except subprocess.TimeoutExpired:code=124
rec={'returncode':code,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':c['timeout_seconds'],'no_fits':True,'private':True,'single_authorized_resume':True};(out/'supervisor.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec),flush=True);sys.exit(code)
