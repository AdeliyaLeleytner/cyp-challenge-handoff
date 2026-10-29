from pathlib import Path
import datetime as dt,subprocess,time,json
p=Path(__file__).resolve().parent;target=dt.datetime.fromisoformat('2026-10-24T15:57:15+00:00')
print(json.dumps({'status':'waiting','not_before_utc':target.isoformat(),'maximum_prediction_requests':1}),flush=True)
while dt.datetime.now(dt.timezone.utc)<target:
    if (p/'CANCEL_COOLDOWN_PROBE').exists():raise SystemExit('Cancelled; no network request sent')
    time.sleep(min(30,max(.1,(target-dt.datetime.now(dt.timezone.utc)).total_seconds())))
if (p/'CANCEL_COOLDOWN_PROBE').exists():raise SystemExit('Cancelled; no network request sent')
remote='''from pathlib import Path
import datetime as dt,urllib.request,urllib.error,json,time
p=Path('/workspace/cyp-repro/admetlab_probes/cooldown_probe_45min');p.mkdir(parents=True,exist_ok=True)
if (p/'metadata.json').exists():raise RuntimeError('Refusing duplicate one-off probe')
payload={'SMILES':'O=[N+]([O-])c1ccccc1','feature':True}
started=dt.datetime.now(dt.timezone.utc).isoformat();t=time.monotonic()
req=urllib.request.Request('https://admetlab3.scbdd.com/api/single/admet',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
try:
 with urllib.request.urlopen(req,timeout=30) as r:body=r.read();status=r.status;headers=dict(r.headers)
except urllib.error.HTTPError as e:body=e.read();status=e.code;headers=dict(e.headers)
except Exception as e:body=str(e).encode();status=None;headers={}
headers={k:('REDACTED' if k.lower()=='set-cookie' else v) for k,v in headers.items()}
meta={'started_utc':started,'status':status,'seconds':time.monotonic()-t,'headers':headers,'payload':payload,'prediction_requests':1,'retries':0,'same_ip_host':'cyp-chemeleon-57522066'}
(p/'response.bin').write_bytes(body);(p/'metadata.json').write_text(json.dumps(meta,indent=2)+'\\n')
print(json.dumps({'meta':meta,'body_preview':body.decode(errors='replace')[:250],'bytes':len(body)}),flush=True)
'''
r=subprocess.run(['ssh','-o','ConnectTimeout=15','cyp-chemeleon-57522066','python','-u','-'],input=remote,text=True,capture_output=True,timeout=60)
(p/'cooldown45-ssh-result.json').write_text(json.dumps({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'finished_utc':dt.datetime.now(dt.timezone.utc).isoformat()},indent=2)+'\n');print(r.stdout,flush=True);print('SSH_EXIT',r.returncode,flush=True)
if r.returncode==0:
 q=subprocess.run(['rsync','-az','cyp-chemeleon-57522066:/workspace/cyp-repro/admetlab_probes/cooldown_probe_45min/',str(p/'cooldown-probe-45min')+'/'],capture_output=True,text=True,timeout=60)
 print('COPY_EXIT',q.returncode,flush=True)
