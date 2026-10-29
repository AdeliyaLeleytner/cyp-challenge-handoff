from pathlib import Path
import json,hashlib,re,string,csv
from urllib.parse import parse_qs
ROOT=Path('/Users/adeliyaleleytner/Downloads/ADMETlab-Chrome-direct-500')
BASE=Path('/Users/adeliyaleleytner/Downloads/ADMETlab-direct-official-500')
paths=list(ROOT.glob('probes/*/run/batches/*/http-*.json'))+list(ROOT.glob('batches/*/http-*.json'))+list(BASE.glob('batches/*/http-*.json'))
chars=string.ascii_letters+string.digits
def csrf_secret(token):
 if len(token)==32:return token
 if len(token)==64 and all(x in chars for x in token):return ''.join(chars[(chars.index(y)-chars.index(x))%len(chars)] for x,y in zip(token[:32],token[32:]))
 return None
rows=[]
for p in sorted(paths):
 d=json.loads(p.read_text())
 if d.get('method')!='POST':continue
 headers=p.with_suffix('.headers').read_text() if p.with_suffix('.headers').exists() else ''
 blocks=re.split(r'(?=HTTP/\S+ \d+)',headers)
 final=blocks[-1] if blocks else ''
 hs={}
 for line in final.splitlines()[1:]:
  if ':' in line:
   k,v=line.split(':',1);hs[k.lower()]=v.strip()
 body=p.with_suffix('.body').read_bytes() if p.with_suffix('.body').exists() else b''
 form=p.with_suffix('.form')
 fields=parse_qs(form.read_text(),keep_blank_values=True) if form.exists() else {}
 smiles=fields.get('smiles-list',[''])[0].replace('\r\n','\n').splitlines()
 earlier=[]
 for q in p.parent.glob('http-*.json'):
  e=json.loads(q.read_text())
  if e.get('method')=='GET' and e.get('url','').endswith('/server/screening') and e.get('utc','')<=d['utc'] and e.get('http_status')==200:earlier.append((e['utc'],q))
 cookie=None
 if earlier:
  get_path=max(earlier)[1].with_suffix('.headers')
  if get_path.exists():
   m=re.search(r'(?im)^set-cookie:\s*csrftoken=([^;\s]+)',get_path.read_text())
   if m:cookie=m.group(1)
 token=fields.get('csrfmiddlewaretoken',[''])[0]
 sessions=[]
 log=p.parent.parent.parent/'events.jsonl'
 if log.exists():
  for line in log.read_text().splitlines():
   e=json.loads(line)
   if e.get('event')=='proxy_request' and e.get('method')=='POST' and e.get('utc','')<=d['utc']:sessions.append(e)
 row={'file':str(p),'utc':d['utc'],'transport':d.get('interface'),'http_status':d.get('http_status'),'molecules':len(smiles),'form_bytes':form.stat().st_size if form.exists() else None,'fields':sorted(fields),'method_field':fields.get('method'),'csrf_matches_get_cookie':csrf_secret(token)==csrf_secret(cookie) if cookie and token else None,'cookie_from_form_get_present':cookie is not None,'server':hs.get('server'),'retry_after':hs.get('retry-after'),'limit_headers':{k:v for k,v in hs.items() if 'limit' in k or k in ('retry-after','cf-ray','x-request-id','via')},'vary':hs.get('vary'),'content_type':hs.get('content-type'),'body_bytes':len(body),'body_sha256':hashlib.sha256(body).hexdigest()}
 rows.append(row)
Path('artifacts/admetlab-auto/rate-limit-audit/requests.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:print(json.dumps({k:v for k,v in row.items() if k not in ('file','body_sha256','fields','cookie_from_form_get_present')}))
