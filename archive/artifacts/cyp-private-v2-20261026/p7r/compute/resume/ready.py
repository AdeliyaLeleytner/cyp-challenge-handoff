import json,subprocess,time,datetime,importlib.util,os
from pathlib import Path
R=Path(__file__).resolve().parent;C=R.parent
x=json.loads((C/'ACTIVE_LEASE.json').read_text());i=x['instance_id'];lease=Path(x['lease_path']);s=json.loads(lease.read_text());end=s['started_unix']+480
spec=importlib.util.spec_from_file_location('probe',C.parent/'ssh-diagnosis/live-probe/probe.py');probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe);probe.R=R
while time.time()<end:
 d=json.loads(subprocess.check_output(['vastai','show','instance',str(i),'--raw'],text=True,timeout=25));a={k:d.get(k) for k in ['id','actual_status','status_msg','ssh_host','ssh_port','dph_total','disk_space','disk_usage','cpu_ram','cpu_cores_effective']};(R/'status.json').write_text(json.dumps(a,indent=2));print(json.dumps({'status':d.get('actual_status'),'elapsed':round(time.time()-s['started_unix'])}),flush=True)
 if d.get('actual_status')=='running':
  log=subprocess.run(['vastai','logs',str(i),'--tail','50','--raw'],capture_output=True,text=True,timeout=25);(R/'boot.log').write_text(log.stdout)
  if 'Server listening on' in log.stdout:
   e={'host':d['ssh_host'],'port':int(d['ssh_port'])};p=probe.run(e,'relay-ready-true','true')
   if p['returncode']==0 and p['authenticated']:
    cmd="python -c 'import sys,json,torch,shutil; print(json.dumps({\"marker\":\"P7R_PROFILE_READY\",\"python\":sys.version,\"prefix\":sys.prefix,\"torch\":torch.__version__,\"cuda_count\":torch.cuda.device_count(),\"devices\":[torch.cuda.get_device_name(j) for j in range(torch.cuda.device_count())],\"free_bytes\":shutil.disk_usage(\"/workspace\").free}))'"
    p=probe.run(e,'relay-ready-runtime',cmd,wall=40);lines=(R/'relay-ready-runtime.stdout').read_text().splitlines();v=next((json.loads(q) for q in lines if q.startswith('{') and 'P7R_PROFILE_READY' in q),None)
    if p['returncode']==0 and v and v['torch']=='2.6.0+cu124' and v['cuda_count']==2:
     assert v['free_bytes']>7*1024**3 and float(d['dph_total'])<.30
     s=json.loads(lease.read_text());assert s['status']=='active';s.update(deadline_unix=s['started_unix']+3600,actual_hourly_usd=float(d['dph_total']),host_SSH_verified=True,ready_unix=time.time(),profile_extension_cost_bound_usd=float(d['dph_total']),reviewed_profile_extension='Runtime/relay verified;60minute cap<0.30USD inside3.127remaining; no scientific scope change',disk_budget={'available_bytes':v['free_bytes'],'reserved_disk_GB':d.get('disk_space'),'required_extra_GB':7,'tracked_source_bytes':7471512,'full_checkpoint_estimate_GB':3.6});lease.write_text(json.dumps(s,indent=2)+'\n')
     name=f'cyp-private-p7r-{i}';cfg=Path.home()/'.ssh/config';txt=cfg.read_text()
     if 'Host '+name+'\n' not in txt:cfg.write_text(txt+'\nHost '+name+'\n  HostName '+e['host']+'\n  Port '+str(e['port'])+'\n  User root\n  AddressFamily inet\n  IdentityFile ~/.ssh/id_ed25519\n  IdentitiesOnly yes\n  BatchMode yes\n  StrictHostKeyChecking accept-new\n  UserKnownHostsFile '+str(R/'known_hosts')+'\n  ServerAliveInterval 15\n  ServerAliveCountMax 4\n  ConnectTimeout 15\n')
     (R/'READY.json').write_text(json.dumps({'instance_id':i,'ssh_alias':name,'endpoint':e,'runtime':v,'actual_hourly_usd':s['actual_hourly_usd'],'profile_deadline_unix':s['deadline_unix'],'disk_check_passed':True},indent=2));print(json.dumps({'ready':True,'instance_id':i,'alias':name,'rate':s['actual_hourly_usd']}),flush=True);raise SystemExit(0)
   if p.get('auth_rejected'):break
 time.sleep(12)
raise SystemExit('Readiness not established inside bound; teardown required')
