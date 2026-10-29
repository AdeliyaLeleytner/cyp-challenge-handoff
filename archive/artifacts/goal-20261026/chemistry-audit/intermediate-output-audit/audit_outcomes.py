#!/usr/bin/env python3
"""Read-only independent status/identity audit over the frozen intermediate snapshot."""
from pathlib import Path
from collections import Counter
import ast,csv,hashlib,json,math
from rdkit import Chem,RDLogger,rdBase
RDLogger.DisableLog('rdApp.*')
OUT=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def rows(p):
 with p.open() as f:return list(csv.DictReader(f))
r=rows(OUT/'raw-snapshot.csv');f=rows(OUT/'features-snapshot.csv');q=rows(OUT/'queue-snapshot.csv');aliases=rows(OUT/'source-id-map-snapshot.csv')
manifest=json.loads((OUT/'collection-manifest.json').read_text());assert sha((OUT/'raw-snapshot.csv').read_bytes())==manifest['raw_csv_sha256'];assert sha((OUT/'features-snapshot.csv').read_bytes())==manifest['features_sha256']
policy=json.loads((OUT/'DISPOSITION-snapshot.json').read_text());qp=Path(policy['quarantine_manifest']);qb=qp.read_bytes();assert sha(qb)==policy['quarantine_sha256'];(OUT/'approved-quarantine-snapshot.csv').write_bytes(qb)
quarantine={x['request_id'] for x in rows(OUT/'approved-quarantine-snapshot.csv')}
schema=json.loads(Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/admetlab-auto/schema.json').read_text())
byalias={}
for a in aliases:byalias.setdefault(a['request_id'],[]).append({'source':a['source'],'Molecule_Name':a['Molecule_Name']})
byfeat={x['request_id']:x for x in f};qid={x['request_id']:x['SMILES'] for x in q}
endpoints=[c for c in r[0] if c not in ('smiles','raw_smiles')]
base=[c for c in f[0] if c.startswith('ADMETLAB::') and '::category=' not in c];flags=[c for c in f[0] if '::category=' in c]
errors=[];outcomes=[];rejected=[];parsefail=[];rejected_raw=[];rejected_feat=[];base_nonfinite=Counter()
for i,x in enumerate(r):
 rid=sha(x['raw_smiles'].encode());ff=byfeat[rid];bad=[c for c in endpoints if x[c]=='Invalid Molecule'];status='service_rejected' if len(bad)==len(endpoints) else ('partial_service_rejection' if bad else 'prediction_row')
 if qid.get(rid)!=x['raw_smiles'] or ff['SMILES']!=x['raw_smiles'] or ff['service_smiles']!=x['smiles']:errors.append({'row':i,'request_id':rid,'issue':'identity_mismatch'})
 raw_unknown=[]
 for c in endpoints:
  cat,name=schema['web_column_to_endpoint'].get(c,['csv_extra',c]);fc='ADMETLAB::'+cat+'::'+name;v=x[c];actual=ff.get(fc,'')
  isreject=v=='Invalid Molecule'
  flag=fc+'::category=Invalid%20Molecule'
  flag_value=ff.get(flag,'')
  parsed_flag=float(flag_value) if flag_value else 0.0
  if parsed_flag!=float(isreject):errors.append({'request_id':rid,'column':c,'issue':'rejection_flag_mismatch','raw_flag':flag_value})
  if isreject or not v.strip():expected=None
  elif v.startswith('['):expected=float(sum(z not in (None,'','-') for z in ast.literal_eval(v)))
  else:
   try:expected=float(v)
   except ValueError:expected=None;raw_unknown.append(c)
  value=None if actual=='' else float(actual)
  if value is None or not math.isfinite(value):base_nonfinite[fc]+=1
  if expected is None and value is None:pass
  elif expected is None or value is None or not math.isclose(expected,value,rel_tol=1e-12,abs_tol=1e-12):errors.append({'request_id':rid,'column':c,'issue':'numeric_conversion_mismatch'})
 if raw_unknown:errors.append({'request_id':rid,'issue':'unhandled_raw_status','columns':raw_unknown})
 aa=byalias.get(rid,[]);off=[a for a in aa if a['source'].startswith('official-')]
 record={'request_id':rid,'request_smiles':x['raw_smiles'],'service_smiles':x['smiles'],'status':status,'rejected_endpoints':len(bad),'aliases':aa,'official_aliases':off,'approved_source_quarantine':rid in quarantine}
 outcomes.append(record)
 if bad:rejected.append({**record,'raw_endpoint_values':{c:x[c] for c in endpoints},'numeric_values':{c:ff[c] for c in base},'category_flags':{c:ff[c] for c in flags},'retry_recommended':False});rejected_raw.append(x);rejected_feat.append(ff)
 req=Chem.MolFromSmiles(x['raw_smiles']);srv=Chem.MolFromSmiles(x['smiles'])
 if req is None or srv is None:parsefail.append({**record,'request_rdkit_parse':req is not None,'service_rdkit_parse':srv is not None,'request_canonical':Chem.MolToSmiles(req,isomericSmiles=True) if req is not None else None,'reported_MW':x.get('MW'),'reported_fChar':x.get('fChar'),'reported_elements_note':'Do not replace returned structure or attribute its predictions to a reconstructed graph.'})
def writecsv(name,rr,fieldnames=None):
 if not rr:(OUT/name).write_text('');return
 rr=[{k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in a.items()} for a in rr]
 with (OUT/name).open('w') as f:w=csv.DictWriter(f,fieldnames=fieldnames or list(rr[0]));w.writeheader();w.writerows(rr)
writecsv('outcome-ledger.csv',outcomes);writecsv('rejected-raw-evidence.csv',rejected_raw);writecsv('rejected-features-evidence.csv',rejected_feat)
(OUT/'service-rejections.json').write_text(json.dumps(rejected,indent=2)+'\n');(OUT/'service-parse-failures.json').write_text(json.dumps(parsefail,indent=2)+'\n');(OUT/'independent-output-errors.json').write_text(json.dumps(errors,indent=2)+'\n')
ids=[x['request_id'] for x in outcomes]
summary={'snapshot_utc':manifest['utc'],'snapshot_outcomes':len(r),'requested_pool_size':len(q),'remaining_at_snapshot':len(set(qid)-set(ids)),'full_collection_complete':False,'status_counts':dict(Counter(x['status'] for x in outcomes)),'raw_unique_request_ids':len(set(ids)),'feature_unique_request_ids':len(byfeat),'duplicate_raw_request_ids':len(ids)-len(set(ids)),'duplicate_feature_request_ids':len(f)-len(byfeat),'extra_request_ids':sorted(set(ids)-set(qid)),'raw_feature_order_equal':ids==[x['request_id'] for x in f],'base_endpoint_columns':len(base),'status_indicator_columns':len(flags),'independent_identity_conversion_flag_errors':len(errors),'base_nonfinite_counts':dict(base_nonfinite),'all_missing_numeric_values_explained_by_explicit_rejections':all(n==len(rejected) for n in base_nonfinite.values()) and len(base_nonfinite)==len(base),'rejected_official_rows':sum(bool(x['official_aliases']) for x in rejected),'rejected_rows_in_approved_source_quarantine':sum(x['approved_source_quarantine'] for x in rejected),'service_parse_failure_rows':len(parsefail),'rdkit':rdBase.rdkitVersion,'disposition_snapshot_sha256':sha((OUT/'DISPOSITION-snapshot.json').read_bytes()),'quarantine_snapshot_sha256':sha(qb),'interpretation':'Exact outcomes coverage is distinct from successful numeric prediction coverage. Invalid Molecule is a terminal service outcome, not a retry or a numerical pseudo-label. Source-supervision policy remains separately versioned.'}
(OUT/'outcomes-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='base_nonfinite_counts'},indent=2));print(json.dumps(parsefail,indent=2))
