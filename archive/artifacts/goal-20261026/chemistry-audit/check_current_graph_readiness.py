#!/usr/bin/env python3
"""Immutable partial-snapshot readiness scan; no acquisition or full-coverage claim."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,io,json,hashlib,datetime,time,sys,itertools
from rdkit import Chem,RDLogger
RDLogger.DisableLog('rdApp.*')
BASE=Path(__file__).resolve().parent
ROOT=Path('/Users/adeliyaleleytner/Downloads/ADMETlab-Chrome-direct-500/results')
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT=BASE/('graph-readiness-'+stamp);OUT.mkdir()
sha=lambda b:hashlib.sha256(b).hexdigest()
pointer=json.loads((BASE.parent/'data-policy/LATEST_APPROVED_OUTPUT_POLICY.json').read_text());policyroot=Path(pointer['path']);auditroot=policyroot/'final-output-audit-v2'
pb=(policyroot/'OUTPUT_DISPOSITION.json').read_bytes();bb=(auditroot/'reviewed-exceptions.json').read_bytes();binding=json.loads(bb)
assert sha(pb)==pointer['output_disposition_sha256']==binding['policy_sha256'] and sha(bb)==pointer['binding_sha256']
sys.path.insert(0,str(auditroot));from gate import adjudicate
for attempt in range(10):
 mb=(ROOT/'all-collected-manifest.json').read_bytes();manifest=json.loads(mb);rb=(ROOT/'all-collected.csv').read_bytes();fb=(ROOT/'all-collected-features.csv').read_bytes()
 if mb==(ROOT/'all-collected-manifest.json').read_bytes() and sha(rb)==manifest['raw_csv_sha256'] and sha(fb)==manifest['features_sha256']:break
 time.sleep(.5)
else:raise RuntimeError('Could not freeze a stable raw/numeric snapshot')
for name,b in [('raw-snapshot.csv',rb),('features-snapshot.csv',fb),('collection-manifest.json',mb),('OUTPUT_DISPOSITION.json',pb),('reviewed-exceptions.json',bb)]: (OUT/name).write_bytes(b)
for name in ['gate.py','schema.json','endpoint-types.json']:(OUT/name).write_bytes((auditroot/name).read_bytes())
schema=json.loads((OUT/'schema.json').read_text());types=json.loads((OUT/'endpoint-types.json').read_text())
column_map={c:'ADMETLAB::'+'::'.join(schema['web_column_to_endpoint'].get(c,['csv_extra',c])) for c in types['entries']};probs=[c for c,x in types['entries'].items() if x['kind']=='classification_probability' and x.get('probability_bounds_checked')];assert len(column_map)==120 and len(probs)==64
reviewed={r['request_id']:r for r in binding['exceptions']}
map_path=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/stage/admetlab-id-map.csv');mapbytes=map_path.read_bytes();assert sha(mapbytes)==binding['source_map_sha256'];aliases=defaultdict(list)
for r in csv.DictReader(io.StringIO(mapbytes.decode())):aliases[r['request_id']].append({'source':r['source'],'Molecule_Name':r['Molecule_Name']})
cohort_path=BASE/'corrected-native-reference/stage/cohorts.json';cohorts=json.loads(cohort_path.read_text())['cohorts'];role_sets={c:{role:set(info[role+'_ids']) for role in ['train','test']} for c,info in cohorts.items()}
def roles(aa):
 ids={a['Molecule_Name'] for a in aa};return {c:{role:sorted(ids&members) for role,members in ss.items() if ids&members} for c,ss in role_sets.items()}
ledger=[];differences=[];issues=[];issue_raw=[];issue_features=[];requests=defaultdict(list);services=defaultdict(list);seen=set();counts=Counter();relations=Counter();raw_text_differences=0
rr=csv.DictReader(io.StringIO(rb.decode('utf-8-sig')));ff=csv.DictReader(io.StringIO(fb.decode('utf-8-sig')))
for row,(raw,feat) in enumerate(itertools.zip_longest(rr,ff)):
 if raw is None or feat is None:raise RuntimeError('Raw/feature count mismatch')
 result=adjudicate(raw,feat,column_map,probs,reviewed);rid=result['request_id'];assert rid not in seen;seen.add(rid);assert rid in aliases
 req=Chem.MolFromSmiles(raw['raw_smiles']);srv=Chem.MolFromSmiles(raw['smiles']);rc=Chem.MolToSmiles(req,isomericSmiles=True) if req is not None else None;sc=Chem.MolToSmiles(srv,isomericSmiles=True) if srv is not None else None
 record={'row':row,'request_id':rid,'request_smiles':raw['raw_smiles'],'service_smiles':raw['smiles'],'request_canonical':rc,'service_canonical':sc,'status':result['status'],'relation':result['relation'],'chemistry_eligible':result['chemistry_eligible'],'errors':result['errors']}
 ledger.append(record);counts[result['status']]+=1;relations[result['relation']]+=1;raw_text_differences+=raw['raw_smiles']!=raw['smiles']
 if rc is not None:requests[rc].append(rid)
 if sc is not None:services[sc].append(rid)
 if rc!=sc: differences.append({**record,'aliases':aliases[rid],'heldout_roles':roles(aliases[rid])})
 if result['errors']:issues.append({**record,'aliases':aliases[rid],'heldout_roles':roles(aliases[rid])});issue_raw.append(raw);issue_features.append(feat)
assert len(ledger)==manifest['rows']
byid={r['request_id']:r for r in ledger};collision_groups=[]
for canonical,ids in services.items():
 if len(ids)>1:
  collision_groups.append({'service_canonical':canonical,'request_ids':ids,'members':[{**byid[rid],'aliases':aliases[rid],'heldout_roles':roles(aliases[rid])} for rid in ids]})
request_groups={c:ids for c,ids in requests.items() if len(ids)>1}
# Actual frozen training membership is relevant only if a collision exists.
if collision_groups:
 import pandas as pd
 for group in collision_groups:
  for member in group['members']:
   names={a['Molecule_Name'] for a in member['aliases']};membership={}
   for cohort in ['own750','briford529']:
    for component in ['union18','2d6isoform6','mtaux8','2d6single']:
     p=BASE/'corrected-native-reference/stage/corrected'/cohort/'prepared'/(component+'.csv');d=pd.read_csv(p,usecols=['molecule_name']);present=sorted(names&set(d.molecule_name))
     if present:membership[cohort+'/'+component]=present
   member['actual_corrected_native_training_membership']=membership
def csvwrite(name,rows):
 if not rows:(OUT/name).write_text('');return
 rows=[{k:json.dumps(v,sort_keys=True) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows]
 with (OUT/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
csvwrite('graph-ledger.csv',ledger);csvwrite('graph-differences.csv',differences);csvwrite('unlisted-issues.csv',issues);csvwrite('issue-raw-evidence.csv',issue_raw);csvwrite('issue-feature-evidence.csv',issue_features)
(OUT/'service-collisions.json').write_text(json.dumps(collision_groups,indent=2)+'\n');(OUT/'request-collisions.json').write_text(json.dumps(request_groups,indent=2)+'\n')
official=Counter()
for r in ledger:
 if r['chemistry_eligible']:
  for a in aliases[r['request_id']]:
   if a['source'].startswith('official-'):official[a['source']]+=1
summary={'snapshot_utc':manifest['utc'],'snapshot_rows':len(ledger),'requested_pool_size':32421,'pending_at_snapshot':32421-len(ledger),'final_full_audit_claimed':False,'stable_raw_and_features_sha_verified':True,'raw_sha256':sha(rb),'features_sha256':sha(fb),'policy_sha256':sha(pb),'binding_sha256':sha(bb),'map_sha256':sha(mapbytes),'cohort_definition_sha256':sha(cohort_path.read_bytes()),'status_counts':dict(counts),'strict_relation_counts':dict(relations),'literal_smiles_differences':raw_text_differences,'request_exact_isomeric_collision_groups':len(request_groups),'service_exact_isomeric_collision_groups':len(collision_groups),'unlisted_gate_issue_rows':len(issues),'chemistry_eligible_rows':sum(r['chemistry_eligible'] for r in ledger),'official_eligible_counts':dict(official),'rows_preserved_no_merging':True,'no_api_requests_models_rentals':True,'action_before_remaining_acquisition':'Review exact saved issues/collisions; no automatic merge/approval.' if issues or collision_groups or request_groups else 'No new issue detected in this snapshot; continue acquisition and perform the separate final full-pool audit.'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(OUT/'audit-artifacts-sha256.json').write_text(json.dumps({p.name:sha(p.read_bytes()) for p in sorted(OUT.iterdir()) if p.is_file()},indent=2)+'\n');print(json.dumps({'out':str(OUT),**summary},indent=2))
