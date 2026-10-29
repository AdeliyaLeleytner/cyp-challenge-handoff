#!/usr/bin/env python3
"""Verify the exported projection and status semantics without changing any data."""
from pathlib import Path
from collections import Counter
import csv,json,hashlib,itertools,math,datetime
BASE=Path(__file__).resolve().parent;GOAL=BASE.parent
DATA=GOAL/'audited-dataset';AUDIT=BASE/'final-32421-v3';OUT=BASE/'final-input-verification'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def rows(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:
  r=csv.DictReader(f);assert len(r.fieldnames)==len(set(r.fieldnames))
  yield from r
def boolean(s):
 assert str(s).lower() in ('true','false'),repr(s)
 return str(s).lower()=='true'
m=json.loads((DATA/'manifest.json').read_text());assert m['rows']==32421 and m['model_feature_columns']==120
for name,expected in m['files'].items():assert sha(DATA/name)==expected,name
assert sha(AUDIT/'audit-artifacts-sha256.json')==m['source_audit_manifest_sha256'];assert sha(GOAL/'export_audited_features.py')==m['exporter_sha256']
assert sha(DATA/'source-id-map.csv')==sha(AUDIT/'source-id-map-snapshot.csv');assert sha(DATA/'outcome-ledger.csv')==sha(AUDIT/'outcome-ledger.csv');assert sha(DATA/'service-outcome-policy.json')==sha(AUDIT/'OUTPUT_DISPOSITION-snapshot.json')
qrows=list(rows(DATA/'source-supervision-quarantine.csv'));q={r['request_id'] for r in qrows};assert len(qrows)==len(q)==28 and sha(DATA/'source-supervision-quarantine.csv')==m['source_quarantine_sha256']
source_policy=json.loads((DATA/'source-supervision-policy.json').read_text());assert sha(DATA/'source-supervision-policy.json')==m['source_policy_sha256'];assert source_policy['quarantine_sha256']==m['source_quarantine_sha256']
ledger={r['request_id']:r for r in rows(DATA/'outcome-ledger.csv')};assert len(ledger)==32421
counts=Counter();seen=set();numeric_text_cells=0;relations=Counter();exceptions=[]
sources={};source_order=[]
for source in rows(AUDIT/'features-snapshot.csv'):
 rid=source['request_id'];assert rid not in sources;source_order.append(rid);sources[rid]={k:v for k,v in source.items() if k in ('request_id','SMILES','service_smiles') or (k.startswith('ADMETLAB::') and '::category=' not in k)}
queue_order=[r['request_id'] for r in rows(AUDIT/'queue-snapshot.csv')];export_order=[]
for row,export in enumerate(rows(DATA/'admetlab-32421-audited-features.csv')):
 source=sources[export['request_id']];export_order.append(export['request_id'])
 rid=export['request_id'];assert rid not in seen;seen.add(rid)
 assert all(export[c]==source[c] for c in ['request_id','SMILES','service_smiles'])
 if row==0:
  columns=[c for c in source if c.startswith('ADMETLAB::') and '::category=' not in c]
  actual=[c for c in export if c.startswith('ADMETLAB::')]
  assert columns==actual and len(columns)==120
  assert set(export)-set(columns)=={'request_id','SMILES','service_smiles','outcome_status','service_structure_relation','numeric_prediction_complete','chemistry_eligible','source_supervision_excluded','fresh_supervision_eligible'}
 assert all(export[c]==source[c] for c in columns),'Numeric text changed';numeric_text_cells+=len(columns)
 ld=ledger[rid];assert export['outcome_status']==ld['status'] and export['service_structure_relation']==ld['relation']
 numeric=boolean(export['numeric_prediction_complete']);eligible=boolean(export['chemistry_eligible']);source_excluded=boolean(export['source_supervision_excluded']);fresh=boolean(export['fresh_supervision_eligible'])
 assert numeric==boolean(ld['numeric_endpoint_complete']) and eligible==boolean(ld['chemistry_eligible'])
 assert source_excluded==(rid in q);assert fresh==(eligible and rid not in q)
 if numeric:assert all(math.isfinite(float(export[c])) for c in columns)
 else:assert export['outcome_status']=='service_rejected' and all(export[c]=='' for c in columns)
 counts['rows']+=1;counts['numeric_prediction_rows']+=numeric;counts['chemistry_eligible_rows']+=eligible;counts['source_supervision_excluded_rows']+=source_excluded;counts['fresh_supervision_eligible_rows']+=fresh;counts[export['outcome_status']]+=1;relations[export['service_structure_relation']]+=1
 if not eligible:exceptions.append({k:export[k] for k in ['request_id','SMILES','service_smiles','outcome_status','chemistry_eligible','source_supervision_excluded','fresh_supervision_eligible']})
assert len(seen)==32421 and seen==set(ledger)
assert export_order==queue_order,'Export does not preserve its declared fixed queue order'
for field in ['rows','numeric_prediction_rows','chemistry_eligible_rows','fresh_supervision_eligible_rows']:assert counts[field]==m[field],field
assert counts['service_rejected']==m['service_rejected_rows']==2;assert counts['numeric_returned_unresolved_service_structure']==m['unresolved_service_structure_rows']==1
assert m['lossless_csv_round_trip_verified'] is True and m['smiles_rewritten'] is False and m['numeric_values_imputed'] is False
certificate={'verification_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'export_directory':str(DATA),'export_manifest_sha256':sha(DATA/'manifest.json'),'exported_files_hash_verified':len(m['files']),'exporter_source_sha256_verified':m['exporter_sha256'],'source_full_audit_manifest_sha256':m['source_audit_manifest_sha256'],'independent_final_input_certificate_sha256':sha(OUT/'FINAL_INPUT_CERTIFICATE.json'),'unique_requests':len(seen),'all_request_ids_and_both_SMILES_fields_exactly_match_audit_by_request_id':True,'export_row_order_matches_fixed_queue':True,'export_order_equals_source_feature_file_order':export_order==source_order,'row_order_note':'Exporter deliberately uses fixed queue order; join to feature snapshots by request_id, not positional row number.','base_feature_names_and_order_match':True,'base_numeric_text_cells_exactly_compared':numeric_text_cells,'numeric_text_changes':0,'rejected_base_values_remain_blank':True,'numeric_values_imputed':False,'all_status_and_eligibility_flags_recomputed_from_ledger_and_source28':True,'counts':dict(counts),'relation_counts':dict(relations),'known_feature_ineligible_rows_preserved':exceptions,'roundtrip_receipt_independently_supported':True,'roundtrip_scope':'Lossless declared CSV projection of120basevalues+identities+auditmetadata, not a claim that rawresponse/categorical columns were included; those remain in the immutable fullaudit.','limitations':'Known2rejections and1unresolvedSb graph are retained; source28 and output eligibility are distinct. This does not certify biological prediction accuracy or all original assay curation.'}
(OUT/'DATASET_EXPORT_CERTIFICATE.json').write_text(json.dumps(certificate,indent=2)+'\n');print(json.dumps({'certificate_path':str(OUT/'DATASET_EXPORT_CERTIFICATE.json'),'certificate_sha256':sha(OUT/'DATASET_EXPORT_CERTIFICATE.json'),'counts':dict(counts),'numeric_text_cells':numeric_text_cells,'export_manifest_sha256':certificate['export_manifest_sha256']},indent=2))
