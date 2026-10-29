import json,sys,subprocess,os,time,signal,hashlib
from pathlib import Path
import psutil
c=json.load(open(sys.argv[1]));out=Path(c['output']);out.mkdir(parents=True,exist_ok=False)
for r in list(c['files'].values())+c['coordinate_files']:assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256']
cap=min(c['memory_max_bytes'],psutil.virtual_memory().available-1024**3);assert cap>=1.5*1024**3;env=os.environ.copy();env['PYTHONPATH']=c['deps_target'];start=time.monotonic();p=subprocess.Popen([sys.executable,'night/source_encoder.py',sys.argv[1]],env=env,start_new_session=False);peak=0;reason=None
while p.poll() is None:
 try:rss=psutil.Process(p.pid).memory_info().rss;peak=max(peak,rss)
 except psutil.NoSuchProcess:break
 if rss>cap:reason='memory_cap'
 if time.monotonic()-start>c['timeout_seconds']:reason='runtime_cap'
 if reason:p.terminate();break
 time.sleep(.5)
try:code=p.wait(timeout=10)
except subprocess.TimeoutExpired:p.kill();code=p.wait()
r={'returncode':code,'stop_reason':reason,'peak_rss_bytes':peak,'memory_cap_bytes':cap,'elapsed_seconds':time.monotonic()-start,'cap_seconds':c['timeout_seconds'],'no_new_geometry_or_CIP_audit':True};(out/'supervisor.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);sys.exit(code if code else int(reason is not None))
