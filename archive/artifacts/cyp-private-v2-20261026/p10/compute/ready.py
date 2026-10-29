import json,subprocess,time,datetime,importlib.util
from pathlib import Path
C=Path(__file__).resolve().parent;B=C.parents[1];x=json.loads((C/'ACTIVE_LEASE.json').read_text());i=x['instance_id'];L=Path(x['lease_path']);s=json.loads(L.read_text());end=s['started_unix']+480
spec=importlib.util.spec_from_file_location('probe',B/'p7r/ssh-diagnosis/live-probe/probe.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.R=C
while time.time()<end:
 d=json.loads(subprocess.check_output(['vastai','show','instance',str(i),'--raw'],text=True,timeout=25));record={k:d.get(k) for k in ['id','actual_status','status_msg','ssh_host','ssh_port','dph_total','disk_space','disk_usage']};(C/'status.json').write_text(json.dumps(record,indent=2));print(json.dumps({'status':d.get('actual_status'),'elapsed':round(time.time()-s['started_unix'])}),flush=True)
 if d.get('actual_status')=='running':
  p=subprocess.run(['vastai','logs',str(i),'--tail','50','--raw'],capture_output=True,text=True,timeout=25);(C/'boot.log').write_text(p.stdout)
  if 'Server listening on' in p.stdout:
   endpoint={'host':d['ssh_host'],'port':int(d['ssh_port'])};v=m.run(endpoint,'relay-true','true')
   if v['returncode']==0 and v['authenticated']:
    cmd="python -c 'import sys,torch,json,shutil; print(json.dumps({\"marker\":\"P10_READY\",\"python\":sys.version,\"prefix\":sys.prefix,\"torch\":torch.__version__,\"GPU_count\":torch.cuda.device_count(),\"free_bytes\":shutil.disk_usage(\"/workspace\").free}))'"
    q=m.run(endpoint,'relay-runtime',cmd,wall=40);data=next((json.loads(z) for z in (C/'relay-runtime.stdout').read_text().splitlines() if z.startswith('{') and 'P10_READY' in z),None)
    if q['returncode']==0 and data and data['torch']=='2.6.0+cu124' and data['GPU_count']==s['num_gpus']:
     assert data['free_bytes']>8*1024**3 and d['disk_space']>=30 and d['dph_total']<.63;s=json.loads(L.read_text());assert s['status']=='active';s.update(deadline_unix=s['started_unix']+2700,host_ready_verified=True,actual_hourly_usd=d['dph_total'],runtime_readback=data,profile_deadline_review='45minute profile maximum<0.473USD, below1.20total; full20 remains profile-gated');L.write_text(json.dumps(s,indent=2)+'\n')
     name=f'cyp-private-p10-{i}';cfg=Path.home()/'.ssh/config';text=cfg.read_text()
     if 'Host '+name+'\n' not in text:cfg.write_text(text+'\nHost '+name+'\n  HostName '+endpoint['host']+'\n  Port '+str(endpoint['port'])+'\n  User root\n  AddressFamily inet\n  IdentityFile ~/.ssh/id_ed25519\n  IdentitiesOnly yes\n  BatchMode yes\n  StrictHostKeyChecking accept-new\n  UserKnownHostsFile '+str(C/'known_hosts')+'\n  ConnectTimeout 15\n  ServerAliveInterval 15\n  ServerAliveCountMax 4\n')
     (C/'READY.json').write_text(json.dumps({'instance_id':i,'alias':name,'runtime':data,'actual_hourly_usd':d['dph_total']},indent=2));print(json.dumps({'ready':True,'instance_id':i,'alias':name,'rate':d['dph_total']}),flush=True);raise SystemExit(0)
   if v.get('auth_rejected'):break
 time.sleep(12)
raise SystemExit('P10 readiness not established; verifiedteardown required')
