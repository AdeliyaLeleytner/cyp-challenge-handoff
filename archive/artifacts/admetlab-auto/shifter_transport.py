"""Curl transport with protected Shifter credentials and per-request sessions (or explicitly selected sticky sessions)."""
import argparse,json,subprocess,re,stat,uuid
from pathlib import Path
from urllib.parse import urlsplit
from collect import StopRun,save,now
from direct_http import Direct
SECRET=Path.home()/'.config/cyp-inhibition/shifter.json'

def config(session):
 if not re.fullmatch(r'[A-Za-z0-9]+',session):raise StopRun('Session must be alphanumeric')
 if stat.S_IMODE(SECRET.stat().st_mode)&0o077:raise StopRun('Proxy credentials must be private (0600)')
 value=json.loads(SECRET.read_text())
 if value['proxy'] not in ('http://p.shifter.io:443','https://p.shifter.io:443'):raise StopRun('Unexpected proxy gateway')
 def quote(x):
  if '\n' in x or '\r' in x:raise StopRun('Invalid curl configuration value')
  return '"'+x.replace('\\','\\\\').replace('"','\\"')+'"'
 user=value['username']+'-sid-'+session+'-ttl-600'
 return 'proxy = '+quote(value['proxy'])+'\nproxy-user = '+quote(user+':'+value['password'])+'\n'

class ShifterDirect(Direct):
 def __init__(self,c,session=None,timeout=900,rotate_per_request=True):
  super().__init__(c,interface='shifter_per_request' if rotate_per_request else 'shifter_sticky',timeout=timeout)
  self.session=session
  self.rotate_per_request=rotate_per_request
 def request(self,i,url,payload=None):
  if self.rotate_per_request:self.session='cyp'+uuid.uuid4().hex[:16]
  self.c.emit('proxy_request',batch=i+1,method='POST' if payload is not None else 'GET',url=url,session_id=self.session,rotation_per_request=self.rotate_per_request)
  previous=self.timeout
  self.timeout=previous if payload is not None else min(previous,90)
  try:return super().request(i,url,payload)
  finally:self.timeout=previous
 def transport_args(self):return ['--config','-','--noproxy','','--interface','en0']
 def curl_stdin(self):return config(self.session)

def main():
 p=argparse.ArgumentParser();p.add_argument('--session',required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 body=a.output/'ip-check.json'
 args=['/usr/bin/curl','--config','-','--noproxy','','--interface','en0','--silent','--show-error','--connect-timeout','15','--max-time','30','--output',str(body),'--write-out','%{http_code}\t%{remote_ip}\t%{local_ip}\t%{proxy_used}','http://ip-info.com/json']
 result=subprocess.run(args,input=config(a.session),capture_output=True,text=True)
 parts=result.stdout.strip().split('\t')
 summary={'utc':now(),'gateway':'p.shifter.io:443','session':a.session,'http_status':parts[0],'gateway_ip':parts[1] if len(parts)>1 else None,'local_ip':parts[2] if len(parts)>2 else None,'proxy_used':parts[3] if len(parts)>3 else None,'curl_exit':result.returncode,'error':result.stderr.strip()}
 if result.returncode==0 and parts[0]=='200':
  try:
   data=json.loads(body.read_text());summary['response']={k:data.get(k) for k in ['ip','country','asn','user_type']}
  except ValueError:summary['response']='Non-JSON response; inspect saved file'
 save(a.output/'connection-check.json',summary)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
