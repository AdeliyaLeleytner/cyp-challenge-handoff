from pathlib import Path
import json,urllib.request,urllib.parse,hashlib,datetime,concurrent.futures
P=Path(__file__).resolve().parent;R=P/'round2';R.mkdir(exist_ok=True);(R/'raw').mkdir(exist_ok=True)
old=json.loads((P/'activity-occurrences.json').read_text());sel=json.loads((P/'assay-selection.json').read_text());used={x for v in sel.values() for x in v['chosen_assay_ids']};contexts={}
for name,quota in [('CYP3A4_midazolam',1000),('CYP2D6_dextromethorphan',1200),('CYP2D6_bufuralol',697)]:
 assays=json.loads((P/'raw'/f'{name}-metadata.json').read_text())['assays']; assays=sorted([a for a in assays if a['assay_chembl_id'] not in used],key=lambda a:int(a['assay_chembl_id'][6:]));used.update(a['assay_chembl_id'] for a in assays);contexts[name]={'quota':quota,'assays':assays,'assay_ids':[a['assay_chembl_id'] for a in assays]}
(R/'PLAN.json').write_text(json.dumps({'reason':'Parent-authorized expansion after low initial yield; same saved metadata pools, no value-based selection','initial_records':len(old),'absolute_cap':3000,'contexts':contexts},indent=2)+'\n')
def run(pair):
 name,c=pair;rows=[];ledger=[];offset=0
 while len(rows)<c['quota']:
  lim=min(250,c['quota']-len(rows));url='https://www.ebi.ac.uk/chembl/api/data/activity.json?'+urllib.parse.urlencode({'assay_chembl_id__in':','.join(c['assay_ids']),'standard_type':'IC50','limit':lim,'offset':offset});p=R/'raw'/f'{name}-{offset}.json'
  if p.exists(): b=p.read_bytes()
  else:b=urllib.request.urlopen(url,timeout=90).read();p.write_bytes(b)
  d=json.loads(b);a=d['activities'];assert len(a)<=lim;assert all(x['assay_chembl_id'] in c['assay_ids'] and x['standard_type']=='IC50' for x in a)
  ledger.append({'url':url,'file':str(p),'sha256':hashlib.sha256(b).hexdigest(),'count':len(a),'total_matching':d['page_meta']['total_count'],'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()});rows += [{'retrieval_round':2,'retrieval_context':name,'retrieval_page':str(p),'retrieval_url':url,'activity':x} for x in a];print(name,len(rows),d['page_meta']['total_count'],flush=True)
  if not a or not d['page_meta'].get('next'):break
  offset+=len(a)
 (R/f'{name}-occurrences.json').write_text(json.dumps(rows,indent=2)+'\n');return rows,ledger
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:results=list(ex.map(run,contexts.items()))
rows=old+[x for rr,_ in results for x in rr];assert len(rows)<=3000;assert len({x['activity']['activity_id'] for x in rows})==len(rows)
(P/'expanded-activity-occurrences.json').write_text(json.dumps(rows,indent=2)+'\n');(R/'query-ledger.json').write_text(json.dumps([x for _,ll in results for x in ll],indent=2)+'\n');print(json.dumps({'total':len(rows),'main':len(rows)-7,'unique_activity_ids':len(rows)}),flush=True)
