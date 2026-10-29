"""Exactly one documented, same-IP ordinary web form submission; no bulk."""
from pathlib import Path
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.parse import urljoin,urlsplit,urlencode
import urllib.request,urllib.error,json,datetime as dt,re,time
BASE='https://admetlab3.scbdd.com'
root=Path('/workspace/cyp-repro/admetlab_probes')
prior=json.loads((root/'cooldown_probe_45min/metadata.json').read_text())
assert prior['status']==200 and dt.datetime.fromisoformat(prior['started_utc'])>=dt.datetime.fromisoformat('2026-10-24T15:57:15+00:00')
p=root/'webbatch_three_probe';p.mkdir(exist_ok=True)
assert not (p/'attempt.json').exists(),'Refuse repeated web form probe'
import csv
with Path('/workspace/cyp-repro/assets/admetlab-queue.csv').open() as f:actual=next(r for r in csv.DictReader(f) if int(r['priority'])==0 and r['SMILES'] not in {'CCO','O=[N+]([O-])c1ccccc1'})
inputs=[{'request_id':'probe_CCO','SMILES':'CCO'},{'request_id':'probe_nitrobenzene','SMILES':'O=[N+]([O-])c1ccccc1'},actual]
(p/'attempt.json').write_text(json.dumps({'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'inputs':inputs,'maximum_form_posts':1,'same_ip_host':'cyp-chemeleon-57522066'},indent=2))
class SameOrigin(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  url=urljoin(req.full_url,newurl);parsed=urlsplit(url)
  if parsed.scheme!='https' or parsed.netloc!='admetlab3.scbdd.com':raise RuntimeError('Unexpected cross-origin redirect')
  return super().redirect_request(req,fp,code,msg,headers,url)
class ParseForm(HTMLParser):
 def __init__(self):super().__init__();self.inside=False;self.action=None;self.fields={};self.textarea=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='form':
   self.inside=a.get('id')=='form2'
   if self.inside:assert a.get('method','').lower()=='post';self.action=a.get('action')
  elif self.inside and tag=='input' and a.get('name'):self.fields[a['name']]=a.get('value','')
  elif self.inside and tag=='textarea':self.textarea=a.get('name')
 def handle_endtag(self,tag):
  if tag=='form':self.inside=False
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()),SameOrigin())
def request(name,req):
 started=dt.datetime.now(dt.timezone.utc).isoformat();t=time.monotonic()
 try:
  with opener.open(req,timeout=45) as r:body=r.read();status=r.status;headers=dict(r.headers);url=r.url
 except urllib.error.HTTPError as e:body=e.read();status=e.code;headers=dict(e.headers);url=e.url
 except Exception as e:body=str(e).encode();status=None;headers={};url=req.full_url
 sanitized=re.sub(rb'(name="csrfmiddlewaretoken" value=")[^"]+',rb'\1REDACTED',body)
 (p/(name+'.bin')).write_bytes(sanitized)
 meta={'started_utc':started,'status':status,'seconds':time.monotonic()-t,'url':url,'headers':{k:v for k,v in headers.items() if k.lower()!='set-cookie'}}
 (p/(name+'.json')).write_text(json.dumps(meta,indent=2)+'\n')
 return meta,body
meta,body=request('form_get',urllib.request.Request(BASE+'/server/screening'))
if meta['status']!=200:print(json.dumps({'stage':'form_get','meta':meta,'post_attempted':False}));raise SystemExit()
s=body.decode(errors='replace')
if any(x in s.lower() for x in ['cf-chl','g-recaptcha','h-captcha','verify you are human']):print(json.dumps({'stage':'challenge_detected','post_attempted':False}));raise SystemExit()
f=ParseForm();f.feed(s);assert f.action=='/server/screeningCal' and f.fields.get('method')=='2' and f.textarea=='smiles-list' and f.fields.get('csrfmiddlewaretoken')
payload={**f.fields,'smiles-list':'\n'.join(r['SMILES'] for r in inputs)}
(p/'request-metadata.json').write_text(json.dumps({'method':'POST','url':BASE+f.action,'payload':{**payload,'csrfmiddlewaretoken':'REDACTED'},'header_names':['Content-Type','Origin','Referer'],'cookie_handling':'normal same-origin CookieJar'},indent=2))
req=urllib.request.Request(BASE+f.action,data=urlencode(payload).encode(),headers={'Content-Type':'application/x-www-form-urlencoded','Origin':BASE,'Referer':BASE+'/server/screening'},method='POST')
meta,body=request('form_post',req);s=body.decode(errors='replace')
links=re.findall(r'href=["\']([^"\']+)',s)
print(json.dumps({'stage':'form_post','meta':meta,'post_attempted':True,'bytes':len(body),'links':links,'title':re.findall(r'<title>(.*?)</title>',s,re.S)[:1],'challenge_detected':any(x in s.lower() for x in ['cf-chl','g-recaptcha','h-captcha','verify you are human'])}),flush=True)
