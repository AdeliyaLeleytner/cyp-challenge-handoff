"""Official ADMETlab3 ordinary web batching, one consistent web_default route.

No API vectors are mixed into this dataset. Rows associate by the returned
raw_smiles field, never by returned row order. No automatic form-POST retry.
"""
from pathlib import Path
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.parse import urljoin,urlsplit,urlencode,quote
import ast,csv,datetime as dt,hashlib,io,json,math,re,signal,sys,time
import urllib.request,urllib.error
from .admetlab_features import atomic_bytes,save,sha,now,ContractError,write_outputs

BASE='https://admetlab3.scbdd.com'
PROVENANCE={'source_mode':'web_default','backend':'documented_web_batch','api_probe_vectors_used':False}

class WebError(RuntimeError):pass
class SameOrigin(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  url=urljoin(req.full_url,newurl);p=urlsplit(url)
  if p.scheme!='https' or p.netloc!='admetlab3.scbdd.com':raise WebError('Cross-origin redirect refused')
  return super().redirect_request(req,fp,code,msg,headers,url)
class Form(HTMLParser):
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

def parse_batch(body,inputs,cfg,taskid):
 reader=csv.DictReader(io.StringIO(body.decode('utf-8-sig')));fields=reader.fieldnames or []
 if len(set(fields))!=len(fields):raise ContractError('DuplicateCSVheaders')
 if not {'raw_smiles','smiles'}<=set(fields):raise ContractError('WebCSVmustcarryraw_smilesandsmiles')
 if set(cfg['forbidden_api_legacy_columns'])&set(fields):raise ContractError('UnexpectedAPIlegacycolumns;source-regimereviewrequired')
 mapping=cfg['web_column_to_endpoint'];required=set(mapping)
 if not required<=set(fields):raise ContractError('Missingwebendpointcolumns:'+','.join(sorted(required-set(fields))))
 expected={r['SMILES']:r for r in inputs}
 if len(expected)!=len(inputs):raise ContractError('InputSMILESnotunique')
 seen=set();success=[];failed=[];associations=[]
 for index,row in enumerate(reader):
  raw=row['raw_smiles']
  if raw not in expected:raise ContractError('Unknownraw_smilesinreturnedCSV')
  if raw in seen:raise ContractError('Duplicatedraw_smilesinreturnedCSV')
  seen.add(raw);source=expected[raw];features={};categories={};missing=[];schema=[]
  for col,text in row.items():
   if col in {'raw_smiles','smiles'}:continue
   group,name=mapping.get(col,['csv_extra',col]);prefix='ADMETLAB::'+group+'::'+name
   schema.append({'category':group,'name':name,'web_column':col,'value_type':'web_csv','extra_fields':[]})
   if text is None or text.strip()=='':features[prefix]=None;missing.append(prefix)
   elif text.startswith('['):
    try:items=ast.literal_eval(text)
    except (ValueError,SyntaxError):raise ContractError('InvalidCSVrulelist:'+col)
    if not isinstance(items,list):raise ContractError('CSVrulevalueisnotlist')
    categories[prefix]=items;features[prefix]=float(len([x for x in items if x not in (None,'','-')]))
   else:
    try:value=float(text)
    except ValueError:
     categories[prefix]=text;features[prefix+'::category='+quote(text,safe='')]=1.
    else:
     features[prefix]=value if math.isfinite(value) else None
     if not math.isfinite(value):missing.append(prefix)
  identity={'request_id':source['request_id'],'SMILES':raw,'priority':source['priority'],'service_smiles':row['smiles'],'taskid':taskid}
  if not row['smiles'] or 'invalid' in row['smiles'].lower():
   failed.append({**identity,'reason':'service_reported_invalid_smiles','returned_row_index':index});continue
  success.append({**identity,'features':features,'categories':categories,'missing':missing,'schema':schema,'endpoint_count':len(schema),'cached':False,'received_utc':now(),**PROVENANCE})
  associations.append({'request_id':source['request_id'],'input_index':inputs.index(source),'returned_row_index':index,'raw_smiles':raw,'service_smiles':row['smiles'],'association':'exactraw_smiles'})
 for raw in expected.keys()-seen:failed.append({**expected[raw],'reason':'service_omitted_input_row'})
 return success,failed,{'input_count':len(inputs),'returned_count':len(seen),'mapped_count':len(success),'failed_count':len(failed),'associations':associations,'columns':fields}

class WebClient:
 def __init__(self,cfg):
  self.cfg=cfg;self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()),SameOrigin());self.last_start=0.;self.requests=0;self.reason=None
 def fetch(self,name,req,folder):
  wait=max(0.,self.cfg['minimum_request_gap_seconds']-(time.monotonic()-self.last_start))
  if wait:time.sleep(wait)
  self.last_start=time.monotonic();self.requests+=1;started=now();body=b'';status=None;headers={};url=req.full_url
  try:
   with self.opener.open(req,timeout=self.cfg['http_timeout_seconds']) as r:body=r.read(64*1024*1024+1);status=r.status;headers=dict(r.headers);url=r.url
  except urllib.error.HTTPError as e:body=e.read();status=e.code;headers=dict(e.headers);url=e.url
  except Exception as e:body=str(e).encode()
  if len(body)>64*1024*1024:raise WebError('Responseexceeds64MiBbound')
  redacted=re.sub(rb'(name="csrfmiddlewaretoken" value=")[^"]+',rb'\1REDACTED',body)
  atomic_bytes(folder/(name+'.bin'),redacted)
  meta={'started_utc':started,'status':status,'seconds':time.monotonic()-self.last_start,'url':url,'method':req.method,'headers':{k:v for k,v in headers.items() if k.lower()!='set-cookie'},'wire_sha256':hashlib.sha256(body).hexdigest(),**PROVENANCE}
  save(folder/(name+'.json'),meta)
  if status!=200:
   self.reason=f'HTTP{status}for{req.method}{url};noretry';raise WebError(self.reason)
  text=body.decode(errors='replace')
  if any(x in text.lower() for x in ['cf-chl','g-recaptcha','h-captcha','verify you are human']):raise WebError('Automationchallengepresent;stopwithoutbypass')
  return meta,body
 def batch(self,inputs,folder,cfg):
  folder.mkdir(parents=True,exist_ok=True);inputhash=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
  inp=folder/'inputs.json'
  if inp.exists():assert json.loads(inp.read_text())['input_sha256']==inputhash
  else:save(inp,{'input_sha256':inputhash,'rows':inputs,**PROVENANCE})
  result=folder/'result.json';csvpath=folder/'download.csv'
  if result.exists():info=json.loads(result.read_text());assert info['input_sha256']==inputhash
  else:
   if (folder/'post-attempt.json').exists():raise WebError('AmbiguouspreviousformPOST;norepeatwithoutrootreview')
   _,body=self.fetch('form-get',urllib.request.Request(BASE+'/server/screening'),folder)
   form=Form();form.feed(body.decode())
   if form.action!='/server/screeningCal' or form.fields.get('method')!='2' or form.textarea!='smiles-list' or not form.fields.get('csrfmiddlewaretoken'):raise ContractError('Officialformcontractchanged')
   payload={**form.fields,'smiles-list':'\n'.join(r['SMILES'] for r in inputs)}
   save(folder/'post-attempt.json',{'started_utc':now(),'input_sha256':inputhash,'payload':{**payload,'csrfmiddlewaretoken':'REDACTED'},**PROVENANCE})
   req=urllib.request.Request(BASE+form.action,data=urlencode(payload).encode(),headers={'Content-Type':'application/x-www-form-urlencoded','Origin':BASE,'Referer':BASE+'/server/screening'},method='POST')
   meta,body=self.fetch('form-post',req,folder)
   match=re.fullmatch(r'/server/result/([A-Za-z0-9_-]+)',urlsplit(meta['url']).path)
   if not match:raise ContractError('SubmissiondidnotreturnownresultURL')
   taskid=match.group(1);links=set(re.findall(r'href=["\']([^"\']+/download/csv)',body.decode()))
   expected='/server/result/'+taskid+'/download/csv'
   if links!={expected}:raise ContractError('OwnCSVdownloadlinkmissingorambiguous')
   details=sorted(set(re.findall(r'href=["\'](/server/detail/[^"\']+)',body.decode())))
   info={'input_sha256':inputhash,'taskid':taskid,'result_url':meta['url'],'download_url':BASE+expected,'detail_links':details,**PROVENANCE};save(result,info)
  if not csvpath.exists():
   _,body=self.fetch('csv-get',urllib.request.Request(info['download_url']),folder);atomic_bytes(csvpath,body)
  completed=folder/'complete.json'
  if completed.exists():assert json.loads(completed.read_text())['csv_sha256']==sha(csvpath)
  successes,failed,association=parse_batch(csvpath.read_bytes(),inputs,cfg,info['taskid'])
  for item in successes:item['cached']=completed.exists()
  save(folder/'association.json',association);save(folder/'failed-rows.json',failed)
  save(completed,{'status':'complete' if not failed else 'complete_with_errors','input_sha256':inputhash,'csv_sha256':sha(csvpath),'rows':len(inputs),'successes':len(successes),**PROVENANCE})
  return successes,failed,association

def export(root,rows,results,errors,cfg,client,started,status):
 # Reuse the stable table/schema/missing-output contract of the single-call client.
 report=write_outputs(root,rows,results,errors,{**cfg,'feature':'web_default','requests_per_second':1/cfg['minimum_request_gap_seconds'],'max_inflight':1},status,client,started)
 report.update(PROVENANCE);save(root/'status.json',report)
 schema=json.loads((root/'feature-schema.json').read_text());schema.update(PROVENANCE);schema['schema_note']='All120livewebendpointidentitiesretained; verifiedToxicophores/FAF-Drugs4alias; rulelistentrycountsandrawlists,nodataderivedfromatomindices; noAPIvectorsorunreturnedlegacycolumnsfabricated.';save(root/'feature-schema.json',schema)
 return report

def run(cfg):
 assert cfg['source_mode']=='web_default' and cfg['batch_size']<=1000 and cfg['pilot_size']==100 and cfg['minimum_request_gap_seconds']>=.2
 assert sha(cfg['queue_path'])==cfg['queue_sha256'];assert sha(cfg['id_map_path'])==cfg['id_map_sha256']
 root=Path(cfg['output_dir']);root.mkdir(parents=True,exist_ok=True)
 import fcntl
 lock=(root/'dispatch.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with Path(cfg['queue_path']).open() as f:rows=list(csv.DictReader(f))
 assert len({r['request_id'] for r in rows})==len(rows)==len({r['SMILES'] for r in rows})
 rows=sorted(rows,key=lambda r:int(r['priority']));client=WebClient(cfg);results={};errors=[];started=time.monotonic();resolved=set();core=[r for r in rows if int(r['priority'])==0];core_ids={r['request_id'] for r in core};core_done=False;status='running'
 save(root/'config.json',cfg);save(root/'id-map-provenance.json',{'path':cfg['id_map_path'],'sha256':sha(cfg['id_map_path'])})
 # Fixed pilot then<=1000 batches, never crossing the priority0/core boundary.
 batches=[]
 for priority in sorted({int(r['priority']) for r in rows}):
  group=[r for r in rows if int(r['priority'])==priority]
  if not batches:batches.append(group[:cfg['pilot_size']]);group=group[cfg['pilot_size']:]
  batches.extend(group[i:i+cfg['batch_size']] for i in range(0,len(group),cfg['batch_size']))
 def interrupted(signum,frame):raise KeyboardInterrupt(f'Signal{signum}')
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 try:
  for index,batch in enumerate(batches):
   if time.monotonic()-started>cfg['maximum_runtime_seconds']:raise WebError('Authorizedruntimecapreached')
   t=time.monotonic();success,failed,association=client.batch(batch,root/'batches'/f'{index:04d}',cfg)
   for r in success:results[r['request_id']]=r
   errors+=failed;resolved|={r['request_id'] for r in batch}
   duration=time.monotonic()-t
   print(json.dumps({'event':'webbatch_complete','batch_index':index,'input_count':len(batch),'successes':len(success),'failed':len(failed),'seconds':duration,**PROVENANCE}),flush=True)
   if index==0:
    previous_pilot=root/'pilot-result.json'
    if previous_pilot.exists() and all(r['cached'] for r in success):duration=json.loads(previous_pilot.read_text())['seconds']
    eta=duration/max(1,len(batch))*(len(rows)-len(batch));pilot={'status':'passed' if not failed else 'requires_review','seconds':duration,'rows':len(batch),'successes':len(success),'estimated_remaining_seconds_linear':eta,'input_identity_contract':'exactraw_smiles','all_endpoint_columns':association['columns'],**PROVENANCE};save(root/'pilot-result.json',pilot);print(json.dumps({'event':'webbatch_pilot',**pilot}),flush=True)
    if failed or eta>cfg['maximum_runtime_seconds']-(time.monotonic()-started):raise WebError('PilotincompleteorlinearETAexceedsauthorizedruntime;rootreviewrequired')
   if not core_done and core_ids<=resolved:
    q=root/'priority0';q.mkdir(exist_ok=True);selected={k:v for k,v in results.items() if k in core_ids};core_status='complete' if len(selected)==len(core) else 'complete_with_errors';export(q,core,selected,[e for e in errors if e['request_id'] in core_ids],cfg,client,started,core_status);save(root/'priority0_milestone.json',{'status':core_status,'rows':len(core),'successes':len(selected),'features_sha256':sha(q/'features.csv'),'features_path':str(q/'features.csv'),**PROVENANCE});core_done=True
   export(root,rows,results,errors,cfg,client,started,'running')
  status='complete' if len(results)==len(rows) else 'complete_with_errors'
 except BaseException as exc:
  status='stopped_partial';client.reason=type(exc).__name__+': '+str(exc);raise
 finally:
  report=export(root,rows,results,errors,cfg,client,started,status);save(root/'failed-rows.json',errors);save(root/'run-summary.json',report)
  if status=='complete':save(root/'complete.json',{'status':'complete','queue_sha256':cfg['queue_sha256'],'rows':len(rows),'features_sha256':sha(root/'features.csv'),'no_endpoint_filtering':True,'no_uncertainty_invented':True,**PROVENANCE})
  fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
 return report

if __name__=='__main__':
 report=run(json.loads(Path('admetlab_web_config.json').read_text()));sys.exit(0 if report['status']=='complete' else 2)
