import json,sys,subprocess,os,time,signal
from pathlib import Path
import psutil
c=json.loads(Path(sys.argv[1]).read_text());assert all(c[k] for k in ['bank_complete','bank_rows','bank_features','bank_audit']),'bank pins absent';out=Path(c['output']);out.mkdir(parents=True,exist_ok=False)
cap=min(c['memory_max_bytes'],psutil.virtual_memory().available-1024**3);assert cap>=1.5*1024**3,'insufficient safe CPU memory headroom';env=os.environ.copy();env['PYTHONPATH']=c['deps_target'];start=time.monotonic();p=subprocess.Popen([sys.executable,'night/p9_tabicl_profile.py',sys.argv[1]],env=env,start_new_session=False);peak=0;reason=None
while p.poll() is None:
 try:rss=psutil.Process(p.pid).memory_info().rss;peak=max(peak,rss)
 except psutil.NoSuchProcess:break
 if rss>cap:reason='memory_cap'
 if time.monotonic()-start>c['timeout_seconds']:reason='runtime_cap'
 if reason:p.terminate();break
 time.sleep(1)
try:code=p.wait(timeout=10)
except subprocess.TimeoutExpired:p.kill();code=p.wait()
r={'returncode':code,'stop_reason':reason,'peak_rss_bytes':peak,'memory_cap_bytes':cap,'elapsed_seconds':time.monotonic()-start,'source_model_unchanged':True};(out/'supervisor.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);sys.exit(code if code else (1 if reason else 0))
