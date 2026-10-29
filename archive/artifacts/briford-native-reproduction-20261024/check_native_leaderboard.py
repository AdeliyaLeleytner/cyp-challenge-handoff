"""Read-only check for the NEW native submission, not the previous alias row."""
from pathlib import Path
from urllib.request import Request,urlopen
import argparse,csv,datetime,hashlib,io,json
P=Path(__file__).resolve().parent;BASE='https://openadmet-cyp-challenge.hf.space'
def fetch(url,data=None):
 with urlopen(Request(url,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=45) as r:return r.read()
def check(intent_dir,dispatched_utc):
 intent=json.loads((Path(intent_dir)/'intent.json').read_text());args=intent['api_arguments_without_file'];now=datetime.datetime.now(datetime.timezone.utc)
 out=P/'official_results'/now.strftime('%Y%m%dT%H%M%SZ');out.mkdir(parents=True,exist_ok=False)
 event=fetch(BASE+'/gradio_api/call/partial',{'data':[]});(out/'event.json').write_bytes(event)
 stream=fetch(BASE+'/gradio_api/call/partial/'+json.loads(event)['event_id']);(out/'response.sse').write_bytes(stream);kind=None;data=None
 for line in stream.decode().splitlines():
  if line.startswith('event:'):kind=line[6:].strip()
  if line.startswith('data:') and kind=='complete':data=json.loads(line[5:].strip())
 assert data and data[0]['url'].startswith(BASE+'/gradio_api/file=')
 raw=fetch(data[0]['url']);(out/'leaderboard.csv').write_bytes(raw);rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
 lower=datetime.datetime.fromisoformat(dispatched_utc.replace('Z','+00:00')).replace(second=0,microsecond=0)
 matches=[]
 for row in rows:
  if row.get('Username')!=args['user_alias'] or row.get('Model Report Link')!=args['model_tag']:continue
  when=datetime.datetime.strptime(row['Submitted'],'%Y-%m-%d %H:%M UTC').replace(tzinfo=datetime.timezone.utc)
  if when>=lower:matches.append(row)
 result={'checked_utc':now.isoformat(),'status':'native_result_visible' if matches else 'native_result_not_yet_visible','matches':matches,'reference_rows':[r for r in rows if r.get('Username')=='briford'],'leaderboard_rows':len(rows),'leaderboard_sha256':hashlib.sha256(raw).hexdigest(),'intent_sha256':hashlib.sha256((Path(intent_dir)/'intent.json').read_bytes()).hexdigest(),'matching_rule':'alias AND exact new model_tag AND submission minute at/after actual dispatch; previous adapted submission is not a match'}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return out,result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--intent-dir',required=True);p.add_argument('--dispatched-utc',required=True);a=p.parse_args();out,r=check(a.intent_dir,a.dispatched_utc);print(json.dumps({'path':str(out),**r},ensure_ascii=False))
