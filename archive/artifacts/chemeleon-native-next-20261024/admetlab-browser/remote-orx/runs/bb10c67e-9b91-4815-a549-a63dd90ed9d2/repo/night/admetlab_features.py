"""Bounded all-endpoint ADMETlab3 acquisition. No GPU or package installation.

One verified official single-SMILES request per molecule. Atomic raw-response
cache is the source of truth; valid cached successes are never re-requested.
The circuit breaker counts consecutive HTTP/network/semantic failures in
response-completion order, reset by any verified successful response. Work
already in flight is drained; no new requests/retries start after it opens.
"""
from pathlib import Path
import argparse, ast, concurrent.futures as cf, csv, datetime as dt, hashlib, http.client, io
import json, math, os, signal, ssl, sys, threading, time
from urllib.parse import urlsplit, quote
from email.utils import parsedate_to_datetime

UTC=dt.timezone.utc

def now():return dt.datetime.now(UTC).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def atomic_bytes(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_name(path.name+f'.{threading.get_ident()}.tmp');tmp.write_bytes(data);os.replace(tmp,path)
def save(path,obj):atomic_bytes(path,(json.dumps(obj,allow_nan=False,ensure_ascii=False,indent=2)+'\n').encode())
def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

class ContractError(ValueError):pass
class Halted(RuntimeError):pass

def flatten_success(response,smiles):
 if not isinstance(response,dict) or response.get('status')!='success' or response.get('code')!=200:
  raise ContractError('Response is not declared status=success,code=200')
 data=response.get('data')
 if not isinstance(data,dict) or data.get('raw_smiles')!=smiles:
  raise ContractError('Returned raw_smiles does not exactly match this request')
 grouped=data.get('data')
 if not isinstance(grouped,dict):raise ContractError('Missing grouped endpoint data')
 features={};categories={};missing=[];schema=[];names=set()
 def value(path,v):
  if isinstance(v,bool):features[path]=float(v)
  elif isinstance(v,(int,float)):
   features[path]=float(v) if math.isfinite(v) else None
   if features[path] is None:missing.append(path)
  elif v is None:features[path]=None;missing.append(path)
  elif isinstance(v,str):
   try:
    numeric=float(v)
   except ValueError:
    categories[path]=v;features[path+'::category='+quote(v,safe='')]=1.0
   else:
    features[path]=numeric if math.isfinite(numeric) else None
    if features[path] is None:missing.append(path)
  elif isinstance(v,list):
   present=[x for x in v if x not in (None,'','-')]
   features[path+'::count']=float(len(present));categories[path]=v
  elif isinstance(v,dict):
   for k,x in v.items():value(path+'::'+str(k),x)
  else:raise ContractError('Unsupported endpoint type: '+path)
 for group,items in grouped.items():
  if not isinstance(items,list):raise ContractError('Endpoint category is not a list: '+group)
  for item in items:
   if not isinstance(item,dict) or not isinstance(item.get('name'),str) or 'value' not in item:
    raise ContractError('Malformed endpoint item in '+group)
   name=item['name'];identity=(group,name)
   if identity in names:raise ContractError('Duplicate endpoint identity')
   names.add(identity);prefix='ADMETLAB::'+group+'::'+name
   value(prefix,item['value'])
   extras=[]
   for k,v in item.items():
    if k not in {'name','display','explanation','decision','value'}:
     value(prefix+'::'+k,v);extras.append(k)
   schema.append({'category':group,'name':name,'display':item.get('display'),'value_type':type(item['value']).__name__,'extra_fields':extras})
 # Keep any future response-level uncertainty/numeric fields, without inventing them.
 for k,v in data.items():
  if k not in {'raw_smiles','smiles','data','structure','taskid'}:value('ADMETLAB::response::'+k,v)
 if not names or not features:raise ContractError('No endpoint values returned')
 return {'features':features,'categories':categories,'missing':missing,'schema':schema,'endpoint_count':len(names),'service_smiles':data.get('smiles'),'taskid':data.get('taskid')}

def verify_endpoint_schema(parsed,cfg):
 expected=set(cfg.get('expected_endpoint_identities',[]))
 observed={r['category']+'::'+r['name'] for r in parsed['schema']}
 missing=expected-observed
 if missing:raise ContractError('Successful response missing expected endpoint identities: '+','.join(sorted(missing)))
 # Additional live endpoints are retained; no fixed119-column truncation.

class Gate:
 def __init__(self,cfg,stop):
  self.cfg=cfg;self.stop=stop;self.lock=threading.Lock();self.next_at=0.;self.cooldown=0.;self.consecutive=0;self.reason=None;self.requests=0
 def permit(self):
  while not self.stop.is_set():
   with self.lock:
    t=time.monotonic();delay=max(self.next_at,self.cooldown)-t
    if delay<=0:self.next_at=t+1/self.cfg['requests_per_second'];self.requests+=1;return
   self.stop.wait(min(delay,.5))
  raise Halted(self.reason or 'stop requested')
 def outcome(self,ok,status=None,retry_after=None,message=''):
  with self.lock:
   if ok:self.consecutive=0;return
   self.consecutive+=1
   lower=message.lower()
   if status in {401,402,403,404,405,410} or any(s in lower for s in ['quota','banned','suspended','daily limit','payment required']):self.reason=f'nonretryable service status={status}: '+message[:150]
   if retry_after is not None:
    if retry_after>self.cfg['max_retry_after_seconds']:self.reason=f'Retry-After {retry_after}s exceeds bounded pause; resume later'
    else:self.cooldown=max(self.cooldown,time.monotonic()+retry_after)
   if self.consecutive>=self.cfg['circuit_breaker_consecutive_errors']:self.reason=self.reason or f'{self.consecutive} consecutive failed responses'
   if self.reason:self.stop.set()

class Transport:
 def __init__(self,cfg):
  parsed=urlsplit(cfg['base_url']);assert parsed.scheme=='https' and parsed.hostname=='admetlab3.scbdd.com'
  self.cfg=cfg;self.hostname=parsed.hostname;self.local=threading.local();self.connections=[];self.lock=threading.Lock()
 def call(self,payload,endpoint=None):
  conn=getattr(self.local,'connection',None)
  if conn is None:
   conn=http.client.HTTPSConnection(self.hostname,timeout=self.cfg['timeout_seconds'],context=ssl.create_default_context());self.local.connection=conn
   with self.lock:self.connections.append(conn)
  try:
   conn.request('POST',endpoint or self.cfg['endpoint'],body=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Accept':'application/json','User-Agent':'CYP-research-feature-client/1.0'})
   result=conn.getresponse();body=result.read(2*1024*1024+1)
   if len(body)>2*1024*1024:raise ContractError('Response exceeds2MiB bounded limit')
   return result.status,dict(result.getheaders()),body
  except Exception:
   conn.close();self.local.connection=None;raise
 def close(self):
  for conn in self.connections:conn.close()

def retry_seconds(headers):
 value=next((v for k,v in headers.items() if k.lower()=='retry-after'),None)
 if value is None:return None
 try:return max(0.,float(value))
 except ValueError:
  try:return max(0.,(parsedate_to_datetime(value)-dt.datetime.now(UTC)).total_seconds())
  except Exception:return None

def paths(root,request_id):
 key=hashlib.sha256(request_id.encode()).hexdigest();d=root/'cache'/key[:2]
 return d/(key+'.response.json'),d/(key+'.meta.json')

def cached_prediction(root,row,cfg):
 raw,meta=paths(root,row['request_id'])
 if not (raw.exists() and meta.exists()):return None
 m=json.loads(meta.read_text())
 if m['request_id']!=row['request_id'] or m['submitted_SMILES']!=row['SMILES'] or m['feature']!=cfg['feature'] or m['endpoint']!=cfg['endpoint'] or m['base_url']!=cfg['base_url']:raise ContractError('Cache identity/options mismatch: '+row['request_id'])
 if sha(raw)!=m['response_sha256']:raise ContractError('Cache raw response hash mismatch: '+row['request_id'])
 parsed=flatten_success(json.loads(raw.read_text()),row['SMILES']);verify_endpoint_schema(parsed,cfg)
 return {**row,**parsed,'cached':True,'received_utc':m['received_utc'],'response_sha256':m['response_sha256']}

def merge_csv(prediction,body):
 rows=list(csv.DictReader(io.StringIO(body.decode('utf-8-sig'))))
 if len(rows)!=1:raise ContractError('Single-molecule CSV must contain exactly one row')
 row=rows[0]
 if row.get('taskId')!=prediction['taskid'] or row.get('smiles')!=prediction['service_smiles']:raise ContractError('CSV taskId/smiles identity mismatch')
 result={**prediction,'features':dict(prediction['features']),'categories':dict(prediction['categories']),'missing':list(prediction['missing']),'schema':list(prediction['schema'])}
 # Exact119 names align with JSON in the live smoke response. Aliases are only
 # accepted when punctuation-insensitive normalization matches one unique name.
 existing={item['name'] for item in result['schema']}
 norm=lambda x:''.join(c.lower() for c in x if c.isalnum())
 aliases={}
 for name in existing:aliases.setdefault(norm(name),[]).append(name)
 result['csv_name_mapping']={};result['csv_extra_names']=[]
 for name,text in row.items():
  if name in {'taskId','smiles'}:continue
  match=name if name in existing else aliases.get(norm(name),[None])[0] if len(aliases.get(norm(name),[]))==1 else None
  result['csv_name_mapping'][name]=match
  if match is not None:
   # Rule CSVs carry matched-substructure lists while JSON carries their count.
   if text.startswith('['):
    try:items=ast.literal_eval(text)
    except (ValueError,SyntaxError):raise ContractError('Invalid rule list in CSV: '+name)
    if not isinstance(items,list):raise ContractError('Rule CSV value is not a list')
    prefix='ADMETLAB::csv_rule::'+name;present=[x for x in items if x not in (None,'','-')]
    result['features'][prefix+'::count']=float(len(present));result['categories'][prefix]=items
   continue
  prefix='ADMETLAB::csv_extra::'+name;result['csv_extra_names'].append(name)
  if text=='':result['features'][prefix]=None;result['missing'].append(prefix)
  else:
   try:value=float(text)
   except ValueError:
    result['features'][prefix+'::category='+quote(text,safe='')]=1.;result['categories'][prefix]=text
   else:
    result['features'][prefix]=value if math.isfinite(value) else None
    if not math.isfinite(value):result['missing'].append(prefix)
  result['schema'].append({'category':'csv_extra','name':name,'value_type':'missing' if text=='' else 'csv_value','extra_fields':[]})
 result['endpoint_count']=len(result['schema'])
 return result

def cached(root,row,cfg):
 prediction=cached_prediction(root,row,cfg)
 if prediction is None:return None
 raw,_=paths(root,row['request_id']);csvraw=raw.with_suffix('.csv');csvmeta=raw.with_suffix('.csvmeta.json')
 if not (csvraw.exists() and csvmeta.exists()):return None
 meta=json.loads(csvmeta.read_text())
 if meta['taskid']!=prediction['taskid'] or meta['csv_sha256']!=sha(csvraw):raise ContractError('CSV cache identity/hash mismatch')
 return merge_csv(prediction,csvraw.read_bytes())

def request_phase(row,payload,endpoint,phase,validate,cfg,root,gate,transport):
 errors=[]
 for attempt in range(cfg['max_transient_retries']+1):
  try:gate.permit()
  except Halted:return None,errors,True
  started=time.monotonic();started_utc=now();status=None;headers={};body=b''
  try:
   status,headers,body=transport.call(payload,endpoint=endpoint)
   if status==200:
    parsed=validate(body);gate.outcome(True)
    return (parsed,body,{'received_utc':now(),'http_status':status,'attempt':attempt,'request_started_utc':started_utc,'response_headers':{k:v for k,v in headers.items() if k.lower()!='set-cookie'},'seconds':time.monotonic()-started}),errors,False
   raise RuntimeError(f'HTTP{status}')
  except Exception as exc:
   message=str(exc);delay=retry_seconds(headers)
   key=hashlib.sha256(row['request_id'].encode()).hexdigest();stamp=time.time_ns()
   error_path=root/'errors'/f'{key}-{phase}-{stamp}.body';atomic_bytes(error_path,body)
   error={'request_id':row['request_id'],'SMILES':row['SMILES'],'phase':phase,'endpoint':endpoint,'attempt':attempt,'utc':now(),'status':status,'request_started_utc':started_utc,'response_headers':{k:v for k,v in headers.items() if k.lower()!='set-cookie'},'kind':type(exc).__name__,'message':message,'seconds':time.monotonic()-started,'retry_after_seconds':delay,'response_body':str(error_path.relative_to(root))}
   errors.append(error);save(error_path.with_suffix('.json'),error)
   gate.outcome(False,status,delay,message+' '+body[:1024].decode(errors='replace'))
   transient=status is None or status==429 or (status is not None and 500<=status<=599)
   if isinstance(exc,(ContractError,json.JSONDecodeError,UnicodeDecodeError)):
    gate.reason='Response schema/identity failure: '+message;gate.stop.set();transient=False
   if not transient or attempt>=cfg['max_transient_retries'] or gate.stop.is_set():break
   if gate.stop.wait(max(delay or 0.,2**attempt)):break
 return None,errors,False

def acquire(row,cfg,root,gate,transport):
 errors=[];prediction=cached_prediction(root,row,cfg);raw,meta=paths(root,row['request_id'])
 if prediction is None:
  def check_json(body):
   parsed=flatten_success(json.loads(body),row['SMILES']);verify_endpoint_schema(parsed,cfg);return parsed
  result,failures,pending=request_phase(row,{'SMILES':row['SMILES'],'feature':cfg['feature']},cfg['endpoint'],'prediction',check_json,cfg,root,gate,transport);errors+=failures
  if result is None:return {'row':row,'errors':errors,'pending':pending}
  parsed,body,info=result;atomic_bytes(raw,body)
  save(meta,{'request_id':row['request_id'],'submitted_SMILES':row['SMILES'],'feature':cfg['feature'],'base_url':cfg['base_url'],'endpoint':cfg['endpoint'],'response_sha256':sha(raw),**info})
  prediction={**row,**parsed,'cached':False,'received_utc':info['received_utc'],'response_sha256':sha(raw)}
 if not prediction['taskid']:raise ContractError('No taskid available for complete CSV retrieval')
 result,failures,pending=request_phase(row,{'taskId':prediction['taskid']},cfg['csv_endpoint'],'csv',lambda body:merge_csv(prediction,body),cfg,root,gate,transport);errors+=failures
 if result is None:return {'row':row,'errors':errors,'pending':pending}
 merged,body,info=result;csvraw=raw.with_suffix('.csv');atomic_bytes(csvraw,body)
 save(raw.with_suffix('.csvmeta.json'),{'request_id':row['request_id'],'taskid':prediction['taskid'],'csv_sha256':sha(csvraw),'endpoint':cfg['csv_endpoint'],**info})
 merged['cached']=False
 return {'success':merged,'errors':errors}

def write_outputs(root,rows,results,errors,cfg,status,gate,started):
 columns=sorted(set().union(*(r['features'].keys() for r in results.values()))) if results else []
 target=root/'features.csv';tmp=target.with_suffix('.csv.tmp')
 identity=['request_id','SMILES','priority','service_smiles','taskid']
 with tmp.open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=identity+columns);writer.writeheader()
  for row in rows:
   item=results.get(row['request_id'])
   if item is None:continue
   values={c:item['features'].get(c,0. if '::category=' in c or '::contains=' in c else None) for c in columns}
   writer.writerow({**{c:item.get(c) for c in identity},**values})
 os.replace(tmp,target)
 with (root/'missing-or-pending.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=['request_id','SMILES','priority']);writer.writeheader();writer.writerows(row for row in rows if row['request_id'] not in results)
 with (root/'categorical-and-missing.jsonl').open('w') as f:
  for row in rows:
   item=results.get(row['request_id'])
   if item and (item['categories'] or item['missing']):f.write(json.dumps({'request_id':row['request_id'],'categories':item['categories'],'missing':item['missing']})+'\n')
 observed={}
 for item in results.values():
  for entry in item['schema']:observed[(entry['category'],entry['name'])]=entry
 save(root/'feature-schema.json',{'endpoint_schema':list(observed.values()),'feature_columns':columns,'schema_note':'JSON endpoints plus all CSV-only columns and rule-list lengths retained; unverified list items are not one-hot encoded. All returned endpoint values and numeric extras retained. decision/display/explanation remain in raw cache, not mistaken for independent endpoints. No synthetic uncertainty added.'})
 elapsed=time.monotonic()-started;completed=len(results);fresh=sum(not r['cached'] for r in results.values());rate=fresh/elapsed if elapsed else 0
 report={'status':status,'updated_utc':now(),'queue_size':len(rows),'successes':completed,'cached_successes':completed-fresh,'new_successes':fresh,'remaining':len(rows)-completed,'requests_started':gate.requests,'error_events':len(errors),'endpoint_names_observed':len(observed),'feature_columns':len(columns),'elapsed_seconds':elapsed,'new_successes_per_second':rate,'estimated_remaining_seconds':(len(rows)-completed)/rate if rate>0 else None,'circuit_reason':gate.reason,'queue_sha256':cfg['queue_sha256'],'feature':cfg['feature'],'global_requests_per_second':cfg['requests_per_second'],'max_inflight':cfg['max_inflight'],'official_requests_per_second_limit':cfg['official_requests_per_second_limit']}
 save(root/'status.json',report);print(json.dumps({'event':'admetlab_status',**report}),flush=True)
 return report

def run(cfg,transport=None):
 assert 0<cfg['requests_per_second']<=cfg['official_requests_per_second_limit']<=5
 assert 1<=cfg['max_inflight']<=8 and cfg['max_transient_retries']<=2
 assert sha(cfg['queue_path'])==cfg['queue_sha256'],'Queue hash mismatch'
 root=Path(cfg['output_dir']);root.mkdir(parents=True,exist_ok=True)
 # Exclusive host-local lock prevents two simultaneous dispatchers for the same cache.
 import fcntl
 lock=(root/'dispatch.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with Path(cfg['queue_path']).open() as f:rows=list(csv.DictReader(f))
 if not all(set(r)=={'request_id','SMILES','priority'} and r['request_id'] and r['SMILES'].strip() for r in rows):raise ContractError('Invalid queue schema/empty identity')
 if len({r['request_id'] for r in rows})!=len(rows):raise ContractError('Duplicate request_id')
 rows=sorted(rows,key=lambda r:int(r['priority']));results={};errors=[];todo=[];started=time.monotonic();stop=threading.Event();gate=Gate(cfg,stop)
 own_transport=transport is None;transport=transport or Transport(cfg)
 save(root/'config.json',cfg)
 idmap=Path(cfg.get('id_map_path',''))
 if cfg.get('id_map_sha256'):assert idmap.is_file() and sha(idmap)==cfg['id_map_sha256'],'ID map hash mismatch'
 if idmap.is_file():save(root/'id-map-provenance.json',{'path':str(idmap),'sha256':sha(idmap)})
 for row in rows:
  found=cached(root,row,cfg)
  if found is None:todo.append(row)
  else:results[row['request_id']]=found
 def halt(signum,frame):gate.reason=f'local signal {signum}';stop.set()
 old_signals={}
 if threading.current_thread() is threading.main_thread():
  for sig in (signal.SIGTERM,signal.SIGINT):old_signals[sig]=signal.signal(sig,halt)
 in_flight={};position=0;last_export=0;status='running';resolved=set(results);core=[r for r in rows if int(r['priority'])==0];core_ids={r['request_id'] for r in core};core_emitted=False
 try:
  with cf.ThreadPoolExecutor(max_workers=cfg['max_inflight']) as pool:
   while position<len(todo) or in_flight:
    while not stop.is_set() and position<len(todo) and len(in_flight)<cfg['max_inflight']:
     row=todo[position]
     if int(row['priority'])>0 and any(int(active['priority'])==0 for active in in_flight.values()):break
     position+=1;in_flight[pool.submit(acquire,row,cfg,root,gate,transport)]=row
    if not in_flight:break
    done,_=cf.wait(in_flight,timeout=cfg.get('queue_poll_seconds',.2),return_when=cf.FIRST_COMPLETED)
    for future in done:
     row=in_flight.pop(future);value=future.result();errors.extend(value.get('errors',[]))
     if 'success' in value:results[row['request_id']]=value['success'];resolved.add(row['request_id'])
     elif not value.get('pending',False):resolved.add(row['request_id'])
    if not core_emitted and core_ids<=resolved:
     core_result={k:v for k,v in results.items() if k in core_ids};core_status='complete' if len(core_result)==len(core) else 'complete_with_errors'
     (root/'priority0').mkdir(exist_ok=True)
     write_outputs(root/'priority0',core,core_result,[e for e in errors if e['request_id'] in core_ids],cfg,core_status,gate,started)
     save(root/'priority0_milestone.json',{'status':core_status,'rows':len(core),'successes':len(core_result),'features_path':str(root/'priority0/features.csv'),'features_sha256':sha(root/'priority0/features.csv')})
     print(json.dumps({'event':'admetlab_priority0_ready','status':core_status,'rows':len(core),'successes':len(core_result)}),flush=True);core_emitted=True
    if time.monotonic()-last_export>=60:
     write_outputs(root,rows,results,errors,cfg,'running',gate,started);last_export=time.monotonic()
   status='complete' if len(results)==len(rows) else 'stopped_partial' if stop.is_set() else 'complete_with_errors'
 except BaseException as exc:
  status='failed';gate.reason=gate.reason or type(exc).__name__+': '+str(exc);stop.set();raise
 finally:
  if own_transport:transport.close()
  for sig,handler in old_signals.items():signal.signal(sig,handler)
  if not core_emitted and core_ids<=set(results):
   (root/'priority0').mkdir(exist_ok=True);core_result={k:v for k,v in results.items() if k in core_ids}
   write_outputs(root/'priority0',core,core_result,[],cfg,'complete',gate,started)
   save(root/'priority0_milestone.json',{'status':'complete','rows':len(core),'successes':len(core_result),'features_path':str(root/'priority0/features.csv'),'features_sha256':sha(root/'priority0/features.csv')})
  report=write_outputs(root,rows,results,errors,cfg,status,gate,started)
  save(root/'run-summary.json',report)
  if status=='complete':save(root/'complete.json',{'status':'complete','queue_sha256':cfg['queue_sha256'],'rows':len(rows),'features_sha256':sha(root/'features.csv'),'no_endpoint_filtering':True,'no_uncertainty_invented':True})
  fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
 return report

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--config',default='admetlab_config.json');args=parser.parse_args()
 report=run(json.loads(Path(args.config).read_text()));sys.exit(0 if report['status']=='complete' else 2)
