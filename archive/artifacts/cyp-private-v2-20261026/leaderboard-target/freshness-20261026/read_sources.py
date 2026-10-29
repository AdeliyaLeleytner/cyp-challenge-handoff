from pathlib import Path
import json,urllib.request,urllib.error,datetime,hashlib,concurrent.futures
P=Path(__file__).resolve().parent;ledger=[]
def fetch(name,url):
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CYP-private-read-only-audit'}),timeout=30) as r:b=r.read(4000000);status=r.status
 except urllib.error.HTTPError as e:b=e.read(10000);status=e.code
 f=P/name;f.write_bytes(b);f.chmod(0o600);rec={'name':name,'url':url,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};ledger.append(rec);return json.loads(b) if name.endswith('.json') else b
jobs=[('space-meta.json','https://huggingface.co/api/spaces/openadmet/cyp-challenge'),('rubyy-meta.json','https://huggingface.co/api/models/basedonAI/openadmet-cyp-inhibition-rubyy'),('rasayan-meta.json','https://api.github.com/repos/whis9/rasayan-cyp')]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:r=list(ex.map(lambda z:fetch(*z),jobs))
space,rubyy,rasayan=r;jobs=[(n,'https://huggingface.co/spaces/openadmet/cyp-challenge/resolve/'+space['sha']+'/'+n) for n in ['app.py','submission.py','config.py','leaderboards.py','models.py','utils.py']];jobs += [('rubyy-README.md','https://huggingface.co/basedonAI/openadmet-cyp-inhibition-rubyy/resolve/'+rubyy['sha']+'/README.md'),('rasayan-tree.json','https://api.github.com/repos/whis9/rasayan-cyp/git/trees/'+rasayan['default_branch']+'?recursive=1'),('api-info.json','https://openadmet-cyp-challenge.hf.space/gradio_api/info')]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(lambda z:fetch(*z),jobs))
(P/'FETCH_LEDGER.json').write_text(json.dumps(ledger,indent=2)+'\n');print(json.dumps({'space_revision':space['sha'],'space_files':[x['rfilename'] for x in space.get('siblings',[])],'rubyy_revision':rubyy['sha'],'rubyy_files':[x['rfilename'] for x in rubyy.get('siblings',[])],'rasayan_size':rasayan['size'],'rasayan_pushed_at':rasayan['pushed_at'],'statuses':{x['name']:x['status'] for x in ledger}},indent=2))
