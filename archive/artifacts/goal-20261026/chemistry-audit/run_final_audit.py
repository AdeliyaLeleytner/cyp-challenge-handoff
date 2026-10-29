#!/usr/bin/env python3
"""Require exact full-queue coverage before freezing and auditing collected outputs.
Reads collection only. Writes a fresh audit directory. No requests or source edits.
"""
import argparse, collections, csv, hashlib, io, json, subprocess, sys, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('--root',type=Path,default=Path('/Users/adeliyaleleytner/Downloads/ADMETlab-Chrome-direct-500'))
p.add_argument('--queue',type=Path,default=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/admetlab-auto/data/molecules.csv'))
p.add_argument('--map',type=Path,default=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/stage/admetlab-id-map.csv'))
p.add_argument('--expected-rows',type=int,default=32421)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--preflight-only',action='store_true',help='Check coverage without running the chemical audit')
a=p.parse_args()
if a.out.exists():raise SystemExit('Choose a new --out directory; existing audit artifacts are immutable.')
a.out.mkdir(parents=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
rows=lambda b:list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
qbytes=a.queue.read_bytes();q=rows(qbytes);qb={r['request_id']:r['SMILES'] for r in q}
for attempt in range(10):
 mb=(a.root/'results/all-collected-manifest.json').read_bytes();m=json.loads(mb)
 rb=(a.root/'results/all-collected.csv').read_bytes();fb=(a.root/'results/all-collected-features.csv').read_bytes()
 if mb==(a.root/'results/all-collected-manifest.json').read_bytes() and sha(rb)==m['raw_csv_sha256'] and sha(fb)==m['features_sha256']:break
 time.sleep(.5)
else:raise RuntimeError('No stable manifest/raw/feature snapshot')
r=rows(rb);f=rows(fb)
rids=[sha(x['raw_smiles'].encode()) for x in r];fids=[x['request_id'] for x in f]
issues=[]
if len(q)!=a.expected_rows or len(qb)!=len(q):issues.append('unexpected_queue_size_or_duplicate_queue_ids')
if any(sha(s.encode())!=i for i,s in qb.items()):issues.append('queue_id_hash_mismatch')
if len(set(rids))!=len(rids):issues.append('duplicate_raw_requests')
if len(set(fids))!=len(fids):issues.append('duplicate_feature_requests')
missing=sorted(set(qb)-set(rids));extra=sorted(set(rids)-set(qb))
if missing or extra:issues.append('raw_queue_coverage_incomplete_or_extra')
if set(fids)!=set(qb):issues.append('feature_queue_coverage_incomplete_or_extra')
if rids!=fids:issues.append('raw_feature_order_or_identity_mismatch')
if any(x['request_id'] not in qb or x['SMILES']!=qb.get(x['request_id']) for x in f):issues.append('feature_smiles_queue_mismatch')
coverage={'expected_rows':a.expected_rows,'queue_rows':len(q),'raw_rows':len(r),'feature_rows':len(f),'missing_request_ids':missing,'extra_request_ids':extra,'queue_sha256':sha(qbytes),'raw_sha256':sha(rb),'features_sha256':sha(fb),'issues':issues,'complete_exact_coverage':not issues}
(a.out/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
(a.out/'queue-snapshot.csv').write_bytes(qbytes)
print(json.dumps({k:v for k,v in coverage.items() if k not in ['missing_request_ids','extra_request_ids']},indent=2))
if issues:raise SystemExit(2)
if a.preflight_only:raise SystemExit(0)
for name,b in [('collection-manifest.json',mb),('raw-snapshot.csv',rb),('features-snapshot.csv',fb)]: (a.out/name).write_bytes(b)
mapbytes=a.map.read_bytes();(a.out/'source-id-map-snapshot.csv').write_bytes(mapbytes)
result=subprocess.run([sys.executable,str(HERE/'audit_chemistry.py'),'--reuse-snapshot','--map',str(a.out/'source-id-map-snapshot.csv'),'--out',str(a.out),'--endpoint-types',str(HERE/'endpoint-types.json')],capture_output=True,text=True)
(a.out/'audit.stdout.log').write_text(result.stdout);(a.out/'audit.stderr.log').write_text(result.stderr)
if result.returncode:raise SystemExit(result.returncode)
s=json.loads((a.out/'summary.json').read_text())
fail={k:s[k] for k in ['identity_issues','feature_value_errors','alert_index_errors','nonfinite_feature_counts','documented_probability_out_of_range'] if s[k]}
if s['documented_probability_columns_checked']!=64:fail['probability_schema_count']=s['documented_probability_columns_checked']
if s['numeric_feature_columns']!=120:fail['numeric_schema_count']=s['numeric_feature_columns']
if s['mw_check']['formal_charge_mismatches']:fail['formal_charge_mismatches']=s['mw_check']['formal_charge_mismatches']
if s['mw_check']['matches_exact_mass_rounded_2dp']!=len(r):fail['mw_exact_mass_review']=s['mw_check']
verdict={'complete_exact_coverage':True,'mechanical_integrity_checks_passed':not fail,'failures_requiring_review':fail,'source_curation_note':'Five of the seven carbon-free requests are upstream fragments of original salts/metal complexes; see full-pool-preaudit/carbon-free-source-audit/REPORT.md. Passing request identity does not certify original assay identity.','chemical_changes_review_required':'Inspect service-structure-differences.csv, chemical-duplicate-groups.json, all-source-original-relations.csv and applicability slices. Do not merge stereoisomers or change molecules automatically.','predictions_are_not_experimental_labels':True}
(a.out/'final-audit-status.json').write_text(json.dumps(verdict,indent=2)+'\n')
files=[x for x in a.out.iterdir() if x.is_file()]
(a.out/'audit-artifacts-sha256.json').write_text(json.dumps({x.name:sha(x.read_bytes()) for x in sorted(files)},indent=2)+'\n')
print(json.dumps(verdict,indent=2))
raise SystemExit(0 if not fail else 3)
