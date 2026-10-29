"""Destroy only the authorized instance after a verified terminal recovery."""
from pathlib import Path
import json,subprocess,time,datetime
ROOT=Path(__file__).resolve().parent;INSTANCE=57740054;VAST='/Users/adeliyaleleytner/.local/bin/vastai'
control=json.loads((ROOT/'execution-control.json').read_text());cert=json.loads((ROOT/'recovery-certificate.json').read_text())
assert control['authorized_instance_id']==cert['instance_id']==INSTANCE and INSTANCE!=55892464
assert control['status'] in ('recovered_complete','recovered_partial') and control['run_id']==cert['run_id']
assert cert['all_remote_hashes_match'] and cert['remote_stable_across_recovery']
def instances():
 r=subprocess.run([VAST,'show','instances','--raw'],capture_output=True,text=True,check=True,timeout=60);data=json.loads(r.stdout)
 return data if isinstance(data,list) else data.get('instances',[])
before=[x for x in instances() if int(x.get('id',-1))==INSTANCE]
if before:
 assert len(before)==1
 r=subprocess.run([VAST,'destroy','instance',str(INSTANCE),'-y','--raw'],capture_output=True,text=True,check=True,timeout=60)
 try:reply=json.loads(r.stdout)
 except ValueError:reply={'message':'CLI returned non-JSON; instance absence is the verification criterion'}
 sanitized={k:v for k,v in reply.items() if k in ('success','msg','message','error')} if isinstance(reply,dict) else {'response_type':type(reply).__name__}
else:sanitized={'message':'Instance already absent before destruction call'}
remaining=[x for x in instances() if int(x.get('id',-1))==INSTANCE]
for _ in range(5):
 if not remaining:break
 time.sleep(5);remaining=[x for x in instances() if int(x.get('id',-1))==INSTANCE]
assert not remaining,'Destruction is not yet verified; do not mark billing stopped'
lease_path=ROOT.parents[1]/'compute/control-lease.json';lease=json.loads(lease_path.read_text());assert lease['instance_id']==INSTANCE
finished=time.time();report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'instance_id':INSTANCE,'run_id':control['run_id'],'destroyed_and_absent_verified':True,'other_instances_modified':False,'response':sanitized,'quote_based_lease_cost_usd':(finished-lease['created_at_unix'])/3600*lease['hourly_usd'],'cost_note':'Estimate from this lease quote and elapsed lifetime, not an itemized invoice or account-balance delta.'}
(ROOT/'resource-cleanup.json').write_text(json.dumps(report,indent=2)+'\n')
lease.update(status='destroyed',destroyed_at_unix=finished,destruction_verified=True);tmp=lease_path.with_suffix('.tmp');tmp.write_text(json.dumps(lease,indent=2)+'\n');tmp.replace(lease_path)
control.update(status='destroyed',teardown_verified=True);(ROOT/'execution-control.json').write_text(json.dumps(control,indent=2)+'\n');print(json.dumps(report))
