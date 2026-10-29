#!/usr/bin/env python3
"""Final-only audit of all32,421 outcomes with exact reviewed exception bindings."""
import argparse,csv,datetime,io,json,sys,time
from pathlib import Path
from collections import Counter,defaultdict
from rdkit import Chem,rdBase
from gate import adjudicate,sha,canon

HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('--root',type=Path,default=Path('/Users/adeliyaleleytner/Downloads/ADMETlab-Chrome-direct-500'))
p.add_argument('--queue',type=Path,default=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/admetlab-auto/data/molecules.csv'))
p.add_argument('--map',type=Path,default=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/stage/admetlab-id-map.csv'))
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
if a.out.exists():raise SystemExit('Use a new output directory; snapshots are immutable.')
a.out.mkdir(parents=True)
def records(b):return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
binding=json.loads((HERE/'reviewed-exceptions.json').read_text())
policy_path=Path(binding['policy_path']);policy_bytes=policy_path.read_bytes()
if sha(policy_bytes)!=binding['policy_sha256']:raise SystemExit('Reviewed policy changed; explicit new binding/review is required.')
policy=json.loads(policy_bytes)
for item in policy['files'].values():
 if sha(Path(item['path']).read_bytes())!=item['sha256']:raise SystemExit('Reviewed exception manifest changed.')
std_item=policy['files']['reviewed-standardizations.json'];std_records=json.loads(Path(std_item['path']).read_text());standardizations={r['request_id']:r for r in std_records}
if len(standardizations)!=len(std_records) or set(standardizations)!=set(policy['reviewed_standardization_requests']):raise SystemExit('Reviewed standardization policy IDs mismatch.')
kind_files={'service_rejected':'service-rejections.json','unresolved_service_structure':'feature-eligibility-exclusions.json','reviewed_internal_proton_transfer':'reviewed-standardizations.json'}
declared_ids={'service_rejected':set(policy['service_rejected_requests']),'unresolved_service_structure':set(policy['feature_identity_excluded_requests']),'reviewed_internal_proton_transfer':set(policy['reviewed_standardization_requests'])}
for kind,ids_expected in declared_ids.items():
 if {r['request_id'] for r in binding['exceptions'] if r['kind']==kind}!=ids_expected:raise SystemExit('Binding/policy ID mismatch:'+kind)
if len(binding['exceptions'])!=len({r['request_id'] for r in binding['exceptions']}) or any(r['kind'] not in kind_files for r in binding['exceptions']):raise SystemExit('Duplicate or unknown reviewed exception kind.')
for record in binding['exceptions']:
 item=policy['files'][kind_files[record['kind']]]
 if record['approval_manifest_sha256']!=item['sha256']:raise SystemExit('Reviewed record approval hash mismatch.')
 if record['kind']=='reviewed_internal_proton_transfer':
  approved=standardizations[record['request_id']]
  for key in ['request_smiles','service_smiles','raw_row_sha256','exact_atom_map','allowed_atom_changes','proof_sha256','parent_approval_sha256']:
   if record.get(key)!=approved.get(key):raise SystemExit('Reviewed standardization proof changed:'+key)
  if approved['approval_status']!='approved_parent_review_for_feature_representation_only':raise SystemExit('Standardization lacks parent review.')
qbytes=a.queue.read_bytes();mb_map=a.map.read_bytes();q=records(qbytes);mapping=records(mb_map)
if sha(qbytes)!=binding['queue_sha256'] or sha(mb_map)!=binding['source_map_sha256']:raise SystemExit('Reviewed fixed queue or ID map changed.')
queue={r['request_id']:r['SMILES'] for r in q}
if len(q)!=32421 or len(queue)!=32421 or any(sha(s.encode())!=rid for rid,s in queue.items()):raise SystemExit('Full fixed queue identity/count check failed.')
for attempt in range(10):
 mb=(a.root/'results/all-collected-manifest.json').read_bytes();manifest=json.loads(mb)
 rb=(a.root/'results/all-collected.csv').read_bytes();fb=(a.root/'results/all-collected-features.csv').read_bytes()
 if mb==(a.root/'results/all-collected-manifest.json').read_bytes() and sha(rb)==manifest['raw_csv_sha256'] and sha(fb)==manifest['features_sha256']:break
 time.sleep(.5)
else:raise SystemExit('No stable collection snapshot available.')
raw=records(rb);features=records(fb);ids=[sha(r['raw_smiles'].encode()) for r in raw];fids=[r['request_id'] for r in features]
coverage={'snapshot_utc':manifest['utc'],'requested_outcomes':32421,'observed_outcomes':len(raw),'missing_request_ids':sorted(set(queue)-set(ids)),'extra_request_ids':sorted(set(ids)-set(queue)),'duplicates':len(ids)-len(set(ids)),'feature_duplicates':len(fids)-len(set(fids)),'raw_feature_order_equal':ids==fids}
complete=len(raw)==len(features)==32421 and set(ids)==set(queue) and not coverage['duplicates'] and not coverage['feature_duplicates'] and ids==fids
coverage['outcomes_complete']=complete;(a.out/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
if not complete:raise SystemExit(2)
if manifest['rows']!=len(raw):raise SystemExit('Manifest row count disagrees with actual outcomes.')
if any(queue[rid]!=r['raw_smiles'] for rid,r in zip(ids,raw)):raise SystemExit('Queue/request mismatch.')
for name,b in [('raw-snapshot.csv',rb),('features-snapshot.csv',fb),('collection-manifest.json',mb),('queue-snapshot.csv',qbytes),('source-id-map-snapshot.csv',mb_map),('OUTPUT_DISPOSITION-snapshot.json',policy_bytes)]: (a.out/name).write_bytes(b)
schema=json.loads((HERE/'schema.json').read_text());types=json.loads((HERE/'endpoint-types.json').read_text())
if sha((HERE/'schema.json').read_bytes())!=binding['schema_sha256'] or sha((HERE/'endpoint-types.json').read_bytes())!=binding['endpoint_types_sha256']:raise SystemExit('Reviewed endpoint schema changed.')
rawcols=set(raw[0])-{'raw_smiles','smiles'}
if rawcols!=set(types['entries']) or len(rawcols)!=120:raise SystemExit('Unexpected raw endpoint schema; review required.')
column_map={c:'ADMETLAB::'+'::'.join(schema['web_column_to_endpoint'].get(c,['csv_extra',c])) for c in rawcols}
probs=[c for c,x in types['entries'].items() if x['kind']=='classification_probability' and x.get('probability_bounds_checked')]
if len(probs)!=64:raise SystemExit('Expected64 documented probability endpoints.')
allowed_features=set(column_map.values())|{x+'::category=Invalid%20Molecule' for x in column_map.values()}|{'request_id','SMILES','service_smiles'}
if set(features[0])-allowed_features or not set(column_map.values())<=set(features[0]):raise SystemExit('Unexpected numeric/status feature schema.')
reviewed={x['request_id']:x for x in binding['exceptions']}
outcomes=[];errors=[];groups={'request':defaultdict(list),'service':defaultdict(list)}
for r,f in zip(raw,features):
 o=adjudicate(r,f,column_map,probs,reviewed);outcomes.append(o)
 if o['errors']:errors.append({'request_id':o['request_id'],'errors':o['errors']})
 for which,col in [('request','raw_smiles'),('service','smiles')]:
  m=Chem.MolFromSmiles(r[col])
  if m is not None:groups[which][canon(m)].append(o['request_id'])
byid={o['request_id']:o for o in outcomes};official=Counter();official_bad=[]
actual_standardized={o['request_id'] for o in outcomes if o['relation']=='exact_reviewed_internal_proton_transfer' and o['chemistry_eligible']}
if actual_standardized!=set(standardizations):errors.append({'issue':'reviewed_standardization_missing_or_failed'})
for r in mapping:
 if r['source'].startswith('official-'):
  o=byid.get(r['request_id'])
  if o is None or not o['chemistry_eligible']:official_bad.append(r['Molecule_Name'])
  else:official[r['source']]+=1
if official!=Counter({'official-train.csv':4905,'official-test.csv':750}) or official_bad:errors.append({'issue':'official_finite_eligible_coverage_failed','bad_ids':official_bad,'eligible_counts':dict(official)})
duplicates={k:{g:rr for g,rr in gg.items() if len(rr)>1} for k,gg in groups.items()}
# Duplicates are preserved and reported; any new service collision needs review.
if duplicates['request'] or duplicates['service']:errors.append({'issue':'unexpected_exact_isomeric_graph_collision'})
def writecsv(name,rr,fields):
 with (a.out/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rr)
writecsv('outcome-ledger.csv',[{k:json.dumps(v) if isinstance(v,list) else v for k,v in r.items()} for r in outcomes],['request_id','status','numeric_endpoint_complete','chemistry_eligible','relation','errors'])
writecsv('feature-eligible-request-ids.csv',[{'request_id':r['request_id']} for r in outcomes if r['chemistry_eligible']],['request_id'])
counts=Counter(r['status'] for r in outcomes)
summary={'audit_version':'final-output-v3','audited_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'outcomes_complete':True,'requested_outcomes':32421,'numeric_prediction_rows':sum(r['numeric_endpoint_complete'] for r in outcomes),'chemistry_eligible_rows':sum(r['chemistry_eligible'] for r in outcomes),'service_rejected_rows':counts['service_rejected'],'unresolved_service_structure_rows':counts['numeric_returned_unresolved_service_structure'],'official_train_eligible':official['official-train.csv'],'official_test_eligible':official['official-test.csv'],'documented_probability_columns_checked':64,'base_endpoint_columns':120,'mechanical_errors':errors,'mechanical_checks_passed':not errors,'raw_sha256':sha(rb),'features_sha256':sha(fb),'queue_sha256':sha(qbytes),'source_map_sha256':sha(mb_map),'reviewed_policy_sha256':sha(policy_bytes),'reviewed_standardization_rows':len(actual_standardized),'reviewed_standardization_request_ids':sorted(actual_standardized),'reviewed_standardizations_sha256':std_item['sha256'],'reviewed_exceptions_binding_sha256':sha((HERE/'reviewed-exceptions.json').read_bytes()),'relations':dict(Counter(r['relation'] for r in outcomes)),'runtime_rdkit':rdBase.rdkitVersion,'scope':'Mechanical requested-output/chemistry eligibility only; no training approval, source-label recuration or prediction-accuracy claim. Apply separate supervision policy.'}
(a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(a.out/'chemical-duplicate-groups.json').write_text(json.dumps(duplicates,indent=2)+'\n')
for name in ['reviewed-exceptions.json','schema.json','endpoint-types.json','gate.py','standardization.py','run_final_audit.py']:(a.out/name).write_bytes((HERE/name).read_bytes())
(a.out/'reviewed-standardizations.json').write_bytes(Path(std_item['path']).read_bytes())
(a.out/'audit-artifacts-sha256.json').write_text(json.dumps({x.name:sha(x.read_bytes()) for x in sorted(a.out.iterdir()) if x.is_file()},indent=2)+'\n')
print(json.dumps(summary,indent=2));raise SystemExit(0 if not errors else 3)
