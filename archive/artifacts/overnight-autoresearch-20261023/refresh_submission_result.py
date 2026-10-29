"""Read-only official leaderboard refresh; never uploads a submission."""
from pathlib import Path
from urllib.request import Request,urlopen
import datetime,hashlib,json,csv,io
P=Path(__file__).resolve().parent
base='https://openadmet-cyp-challenge.hf.space'
now=datetime.datetime.now(datetime.timezone.utc)
out=P/'official_results'/now.strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
def fetch(url,data=None):
    req=Request(url,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json','User-Agent':'CYP-research-result-check/1'})
    with urlopen(req,timeout=45) as r:return r.read()
event=fetch(base+'/gradio_api/call/partial',{'data':[]});(out/'event.json').write_bytes(event)
stream=fetch(base+'/gradio_api/call/partial/'+json.loads(event)['event_id']);(out/'response.sse').write_bytes(stream)
records=[];kind=None
for line in stream.decode().splitlines():
    if line.startswith('event:'):kind=line[6:].strip()
    if line.startswith('data:') and kind=='complete':records=json.loads(line[5:].strip())
assert len(records)==1 and records[0]['url'].startswith(base+'/gradio_api/file=')
raw=fetch(records[0]['url']);(out/'leaderboard.csv').write_bytes(raw)
rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
matches=[row for row in rows if any('adeliyall' in str(v).lower() for v in row.values())]
record={'checked_utc':now.isoformat(),'source':'/partial official live regression CSV callback','leaderboard_sha256':hashlib.sha256(raw).hexdigest(),'rows':len(rows),'matches':matches,'status':'visible_result_found' if matches else 'not_yet_visible','limitation':'Public row alone does not cryptographically bind a CSV hash. Match new timestamp,alias,and model_tag against local accepted receipt.'}
(out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'path':str(out),'status':record['status'],'matches':matches},ensure_ascii=False))
