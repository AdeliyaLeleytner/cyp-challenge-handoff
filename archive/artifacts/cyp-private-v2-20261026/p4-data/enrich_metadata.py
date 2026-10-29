from pathlib import Path
import json,urllib.request,urllib.parse,hashlib,datetime,concurrent.futures
P=Path(__file__).resolve().parent;R=P/'metadata';R.mkdir(exist_ok=True);rows=json.loads((P/'expanded-activity-occurrences.json').read_text());acts=[x['activity'] for x in rows];docs=sorted({x['document_chembl_id'] for x in acts if x.get('document_chembl_id')});assays={a['assay_chembl_id'] for v in json.loads((P/'assay-selection.json').read_text()).values() for a in v['assays']};assays|={a['assay_chembl_id'] for v in json.loads((P/'round2/PLAN.json').read_text())['contexts'].values() for a in v['assays']};missing=sorted({x['assay_chembl_id'] for x in acts}-assays);jobs=[]
for i in range(0,len(docs),50): jobs.append((f'documents-{i}.json','https://www.ebi.ac.uk/chembl/api/data/document.json?'+urllib.parse.urlencode({'document_chembl_id__in':','.join(docs[i:i+50]),'limit':100})))
jobs.append(('control-assays.json','https://www.ebi.ac.uk/chembl/api/data/assay.json?'+urllib.parse.urlencode({'assay_chembl_id__in':','.join(missing),'limit':100})))
for src in sorted({x['src_id'] for x in acts}):jobs.append((f'source-{src}.json',f'https://www.ebi.ac.uk/chembl/api/data/source/{src}.json'))
for name,url in [('bindingdb-info.html','https://www.bindingdb.org/rwd/bind/info.jsp'),('bindingdb-download.html','https://www.bindingdb.org/rwd/bind/chemsearch/marvin/Download.jsp'),('bindingdb-rest.html','https://www.bindingdb.org/rwd/bind/BindingDBRESTfulAPI.jsp')]:jobs.append((name,url))
def get(job):
 name,url=job;p=R/name
 try:
  if p.exists():b=p.read_bytes()
  else:b=urllib.request.urlopen(url,timeout=60).read();p.write_bytes(b)
  return {'file':str(p),'url':url,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 except Exception as e:return {'file':str(p),'url':url,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:ledger=list(ex.map(get,jobs))
(R/'LEDGER.json').write_text(json.dumps(ledger,indent=2)+'\n');print(json.dumps(ledger,indent=2))
