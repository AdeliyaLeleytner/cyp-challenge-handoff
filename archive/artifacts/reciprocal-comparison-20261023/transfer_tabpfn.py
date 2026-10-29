import urllib.request,json,subprocess,time
from pathlib import Path
base=Path(__file__).resolve().parent
meta=json.loads((base/'tabpfn-source.json').read_text())
url=f"https://huggingface.co/{meta['repository']}/resolve/{meta['revision']}/{meta['filename']}"
head=urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=30)
# Pass a public CDN redirect through stdin; never expose its ephemeral query signature in logs.
remote="""import sys,json,urllib.request,hashlib,time
from pathlib import Path
x=json.load(sys.stdin);p=Path('/root/.cache/tabpfn')/x['filename'];p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.partial');h=hashlib.sha256();n=0;t=time.monotonic()
with urllib.request.urlopen(x['url'],timeout=60) as r,tmp.open('wb') as out:
 while True:
  b=r.read(4*1024*1024)
  if not b:break
  out.write(b);h.update(b);n+=len(b)
assert n==x['size'],(n,x['size']);tmp.replace(p)
print(json.dumps({'path':str(p),'size':n,'sha256':h.hexdigest(),'seconds':time.monotonic()-t}))
"""
import shlex
cmd=['ssh','-o','ConnectTimeout=15','cyp-vast-57405450','/opt/conda/bin/python -c '+shlex.quote(remote)]
p=subprocess.run(cmd,input=json.dumps({'url':head.url,'filename':meta['filename'],'size':meta['public_head_size']}),capture_output=True,text=True)
print('TRANSFER_EXIT',p.returncode,flush=True)
# Tracebacks can contain signed URLs; only emit success JSON, otherwise a short status.
if p.returncode==0:
 lines=p.stdout.splitlines();result=json.loads(next(l for l in reversed(lines) if l.startswith('{')));(base/'tabpfn-transfer.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
else:print('Public CDN transfer failed; detailed stderr intentionally omitted.',flush=True)
