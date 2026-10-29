import json,subprocess,time,sys,datetime
from pathlib import Path
from lease_control import destroy_verified
R=Path(__file__).resolve().parent;c=json.loads((R/'probe-config.json').read_text());i=c['instance_id'];lease=Path(c['lease_path'])
while time.time()<c['probe_deadline_unix']-75:
 s=json.loads(lease.read_text())
 if s['status']!='active':break
 try:
  p=subprocess.run(['vastai','show','instance',str(i),'--raw'],capture_output=True,text=True,timeout=25);d=json.loads(p.stdout);keep={k:d.get(k) for k in ['id','actual_status','status_msg','public_ipaddr','ports','ssh_host','ssh_port','dph_total']};(R/'live-status.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**keep},indent=2));print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':d.get('actual_status')}),flush=True)
  if d.get('dph_total',0)>.45:raise RuntimeError('Actual hourly total exceeds diagnostic ceiling')
  if d.get('actual_status')=='running' and d.get('ports',{}).get('22/tcp'):
   p=subprocess.run(['vastai','logs',str(i),'--tail','60','--raw'],capture_output=True,text=True,timeout=25);(R/'live-boot-log.txt').write_text(p.stdout);ready='Server listening on' in p.stdout
   if ready:
    q=subprocess.run([sys.executable,str(R/'probe.py')],timeout=max(1,int(c['probe_deadline_unix']-time.time())))
    if q.returncode==0:
     result=json.loads((R/'DIAGNOSTIC_RESULT.json').read_text())
     if result['runtime_success']:print(json.dumps({'runtime_success':True,'instance_id':i,'review_deadline_unix':s['deadline_unix']}),flush=True);sys.exit(0)
    break
 except Exception as e:print(json.dumps({'diagnostic_error_type':type(e).__name__,'message':str(e)[:250]}),flush=True)
 time.sleep(12)
print(json.dumps({'runtime_success':False,'action':'destroy_verified','instance_id':i}),flush=True)
print(json.dumps(destroy_verified(lease,i)),flush=True)
