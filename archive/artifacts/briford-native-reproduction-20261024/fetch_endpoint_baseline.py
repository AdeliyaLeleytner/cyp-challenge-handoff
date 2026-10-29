from urllib.request import Request,urlopen
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,csv,io,datetime,hashlib
p=Path(__file__).resolve().parent/'sources/previous_submission_breakdown';p.mkdir(parents=True,exist_ok=True);base='https://openadmet-cyp-challenge.hf.space'
def fetch(url,data=None):
 with urlopen(Request(url,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=45) as r:return r.read()
def run(item):
 name,api=item;event=json.loads(fetch(base+'/gradio_api/call/'+api,{'data':[]}));stream=fetch(base+'/gradio_api/call/'+api+'/'+event['event_id']).decode();kind=None;result=None
 for line in stream.splitlines():
  if line.startswith('event:'):kind=line[6:].strip()
  if line.startswith('data:') and kind=='complete':result=json.loads(line[5:].strip())
 assert result and result[0]['url'].startswith(base+'/gradio_api/file=')
 raw=fetch(result[0]['url']);(p/f'{name}.csv').write_bytes(raw);rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))));sel=[r for r in rows if r['Username'] in ['briford','AdeliyaLL-CYP']]
 return name,{'api':api,'sha256':hashlib.sha256(raw).hexdigest(),'rows':sel}
with ThreadPoolExecutor(max_workers=4) as pool:out=dict(pool.map(run,zip(['CYP1A2','CYP2C9','CYP2D6','CYP3A4'],['partial_1','partial_2','partial_3','partial_4'])))
out['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(p/'comparison.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
