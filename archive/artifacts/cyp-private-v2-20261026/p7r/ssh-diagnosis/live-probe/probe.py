import json,subprocess,time,datetime,threading,os,signal,sys
from pathlib import Path
R=Path(__file__).resolve().parent
IDENTITY=str(Path.home()/'.ssh/id_ed25519')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(endpoint,name,command,wall=25):
 start=time.time();trace=R/(name+'.jsonl');raw=R/(name+'.stderr');out=R/(name+'.stdout');known=R/'known_hosts';known.touch(exist_ok=True);os.chmod(known,0o600)
 args=['ssh','-vvv','-4','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-i',IDENTITY,'-o','ConnectionAttempts=1','-o','ConnectTimeout=12','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','-o','ControlMaster=no','-o','ControlPath=none','-o','CanonicalizeHostname=no','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(known),'-p',str(endpoint['port']),'root@'+endpoint['host'],command]
 p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,start_new_session=True);lock=threading.Lock();chunks={'stdout':[],'stderr':[]}
 with trace.open('w') as log,raw.open('w') as ef,out.open('w') as of:
  for q in [trace,raw,out]:os.chmod(q,0o600)
  def reader(pipe,kind,target):
   for line in iter(pipe.readline,''):
    chunks[kind].append(line)
    with lock:target.write(line);target.flush();log.write(json.dumps({'utc':utc(),'stream':kind,'line':line.rstrip('\n')})+'\n');log.flush()
  threads=[threading.Thread(target=reader,args=(p.stdout,'stdout',of)),threading.Thread(target=reader,args=(p.stderr,'stderr',ef))]
  for t in threads:t.start()
  timed=False
  try:p.wait(timeout=wall)
  except subprocess.TimeoutExpired:
   timed=True;os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  for t in threads:t.join(timeout=3)
 text=''.join(chunks['stderr']);receipt={'name':name,'started_utc':datetime.datetime.fromtimestamp(start,datetime.timezone.utc).isoformat(),'ended_utc':utc(),'elapsed_seconds':time.time()-start,'endpoint':endpoint,'remote_command_kind':'true' if command=='true' else 'runtime','returncode':p.returncode,'wall_timeout':timed,'tcp_connected':'Connection established' in text,'remote_protocol_received':'Remote protocol version' in text,'server_host_key_received':'Server host key:' in text,'authenticated':'Authenticated to ' in text,'auth_rejected':'Permission denied' in text,'banner_timeout':'during banner exchange' in text,'command_exit_status_reported':'Exit status ' in text,'private_trace':trace.name,'identity_explicit':True,'IPv4_explicit':True}
 (R/(name+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n');return receipt
if __name__=='__main__':
 cfg=json.loads((R/'probe-config.json').read_text());lease=json.loads(Path(cfg['lease_path']).read_text());assert lease['status']=='active' and time.time()<cfg['probe_deadline_unix']
 status=json.loads(subprocess.check_output(['vastai','show','instance',str(cfg['instance_id']),'--raw'],text=True));assert status.get('actual_status')=='running' and status.get('ports',{}).get('22/tcp')
 endpoints={'direct':{'host':status['public_ipaddr'],'port':int(status['ports']['22/tcp'][0]['HostPort'])},'relay':{'host':status['ssh_host'],'port':int(status['ssh_port'])}};route={}
 for n,e in endpoints.items():
  p=subprocess.run(['/sbin/route','-n','get',e['host']],capture_output=True,text=True);route[n]={'utc':utc(),'exit_code':p.returncode,'local_lookup_output':p.stdout}
 (R/'routes-private.json').write_text(json.dumps(route,indent=2));os.chmod(R/'routes-private.json',0o600)
 results={};ts=[]
 for n,e in endpoints.items():
  t=threading.Thread(target=lambda n=n,e=e:results.__setitem__(n,run(e,n+'-true','true')));t.start();ts.append(t)
 for t in ts:t.join()
 print(json.dumps({'phase':'true_probes','results':results}),flush=True)
 runtime=[]
 command="python -c 'import sys,json,torch; print(json.dumps({\"marker\":\"P7R_RUNTIME_READY\",\"python\":sys.version,\"prefix\":sys.prefix,\"torch\":torch.__version__,\"cuda_available\":torch.cuda.is_available(),\"device_count\":torch.cuda.device_count(),\"devices\":[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]}))'"
 for n,r in results.items():
  if r['returncode']==0 and r['authenticated'] and time.time()<cfg['probe_deadline_unix']-35:
   rr=run(endpoints[n],n+'-runtime',command,wall=35);lines=(R/(n+'-runtime.stdout')).read_text().splitlines();data=next((json.loads(x) for x in lines if x.startswith('{') and 'P7R_RUNTIME_READY' in x),None);runtime.append({'path':n,'probe':rr,'runtime':data});print(json.dumps({'phase':'runtime','result':runtime[-1]}),flush=True)
 success=any(r['probe']['returncode']==0 and r['runtime'] and r['runtime']['cuda_available'] and r['runtime']['device_count']==cfg['expected_gpu_count'] and r['runtime']['torch']=='2.6.0+cu124' for r in runtime)
 receipt={'utc':utc(),'instance_id':cfg['instance_id'],'transport':results,'runtime':runtime,'runtime_success':success,'no_model_work':True,'no_network_or_key_changes':True};(R/'DIAGNOSTIC_RESULT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'phase':'diagnostic_complete','runtime_success':success}),flush=True)
