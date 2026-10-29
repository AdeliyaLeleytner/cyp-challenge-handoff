#!/usr/bin/env python3
"""Private bounded raw IC50 panel acquisition. No filtering, fitting or publication."""
from pathlib import Path
import urllib.request,urllib.parse,json,time,datetime,hashlib,concurrent.futures
ROOT=Path(__file__).resolve().parent
selected=json.loads((ROOT/'assay-selection.json').read_text());plan=json.loads((ROOT/'ACQUISITION_PLAN.json').read_text())
assert sum(x['context']['quota'] for x in selected.values())+7==2957<=3000
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fetch_context(pair):
 name,item=pair;ids=item['chosen_assay_ids'];quota=item['context']['quota'];rows=[];events=[];offset=0
 while len(rows)<quota and ids:
  limit=min(250,quota-len(rows));params={'assay_chembl_id__in':','.join(ids),'standard_type':'IC50','limit':limit,'offset':offset};url='https://www.ebi.ac.uk/chembl/api/data/activity.json?'+urllib.parse.urlencode(params)
  path=ROOT/'raw'/f'{name}-activities-{offset}.json';start=time.time();b=urllib.request.urlopen(url,timeout=60).read();data=json.loads(b);items=data['activities'];assert len(items)<=limit;path.write_bytes(b)
  assert all(x['assay_chembl_id'] in ids and x['standard_type']=='IC50' for x in items)
  events.append({'context':name,'url':url,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'offset':offset,'requested_limit':limit,'returned':len(items),'total_matching':data['page_meta']['total_count'],'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'seconds':time.time()-start,'path':str(path)})
  rows.extend({'retrieval_context':name,'retrieval_page':str(path),'retrieval_url':url,'activity':x} for x in items)
  print(json.dumps({'context':name,'received':len(rows),'quota':quota,'total_matching':data['page_meta']['total_count']}),flush=True)
  if not items or not data['page_meta'].get('next'):break
  offset+=len(items)
 (ROOT/(name+'-occurrences.json')).write_text(json.dumps(rows,indent=2)+'\n')
 return rows,events
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(fetch_context,selected.items()):results.append(r)
rows=[r for rr,_ in results for r in rr];events=[e for _,ee in results for e in ee]
control=ROOT.parent/'biochem_sources/CHEMBL10-CYP1A2-example.json';data=json.loads(control.read_text());assert len(data['activities'])==7
rows.extend({'retrieval_context':'CHEMBL10_CYP1A2_curation_control','retrieval_page':str(control),'retrieval_url':'https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id=CHEMBL3356&molecule_chembl_id=CHEMBL10&limit=10','activity':x} for x in data['activities'])
assert len(rows)<=2957;assert len({r['activity']['activity_id'] for r in rows})==len(rows),'Unexpected duplicated activity IDs; preserve occurrences and investigate'
(ROOT/'activity-occurrences.json').write_text(json.dumps(rows,indent=2)+'\n');(ROOT/'activity-query-ledger.json').write_text(json.dumps(events,indent=2)+'\n')
version_url='https://www.ebi.ac.uk/chembl/api/data/status.json'
try:
 b=urllib.request.urlopen(version_url,timeout=30).read();(ROOT/'raw/chembl-status.json').write_bytes(b);version=json.loads(b)
except Exception as e:version={'query_url':version_url,'error':str(e)}
receipt={'acquired_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'activity_occurrences':len(rows),'unique_activity_ids':len(rows),'main_IC50_records':len(rows)-7,'curation_control_records':7,'user_cap':3000,'plan_cap':2957,'assay_selection_sha256':digest(ROOT/'assay-selection.json'),'plan_sha256':digest(ROOT/'ACQUISITION_PLAN.json'),'raw_occurrences_sha256':digest(ROOT/'activity-occurrences.json'),'version_response':version,'no_rows_discarded':True,'no_structure_or_label_rewriting':True,'no_fits_spending_publication':True}
(ROOT/'ACQUISITION_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
