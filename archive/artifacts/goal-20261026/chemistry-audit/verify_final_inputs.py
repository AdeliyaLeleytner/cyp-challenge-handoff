#!/usr/bin/env python3
"""Read-only checksum/coverage/official-vector check, not a second chemical audit."""
from pathlib import Path
import csv,json,hashlib,math,datetime
from collections import Counter
import numpy as np
BASE=Path(__file__).resolve().parent
FULL=BASE/'final-32421-v3';OLD=BASE/'intermediate-output-audit';OUT=BASE/'final-input-verification';OUT.mkdir(exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def readcsv(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:yield from csv.DictReader(f)
manifest=json.loads((FULL/'audit-artifacts-sha256.json').read_text())
for name,digest in manifest.items():assert sha(FULL/name)==digest,name
summary=json.loads((FULL/'summary.json').read_text());assert summary['audit_version']=='final-output-v3' and summary['outcomes_complete'] and summary['mechanical_checks_passed'] and summary['mechanical_errors']==[]
for key,file in [('raw_sha256','raw-snapshot.csv'),('features_sha256','features-snapshot.csv'),('queue_sha256','queue-snapshot.csv'),('source_map_sha256','source-id-map-snapshot.csv'),('reviewed_policy_sha256','OUTPUT_DISPOSITION-snapshot.json'),('reviewed_exceptions_binding_sha256','reviewed-exceptions.json'),('reviewed_standardizations_sha256','reviewed-standardizations.json')]:assert sha(FULL/file)==summary[key],key
queue=list(readcsv(FULL/'queue-snapshot.csv'));q={r['request_id']:r['SMILES'] for r in queue};assert len(queue)==len(q)==32421;assert all(hashlib.sha256(s.encode()).hexdigest()==rid for rid,s in q.items())
mapping=list(readcsv(FULL/'source-id-map-snapshot.csv'));official=[r for r in mapping if r['source'] in ('official-train.csv','official-test.csv')];required={r['request_id'] for r in official};assert len(official)==len(required)==5655
role_counts=Counter(r['source'] for r in official);assert role_counts=={'official-train.csv':4905,'official-test.csv':750}
oldcert=json.loads((OLD/'OFFICIAL5655_SCOPE_CERTIFICATE.json').read_text());assert sha(OLD/'raw-snapshot.csv')==oldcert['raw_sha256'];assert sha(OLD/'features-snapshot.csv')==oldcert['features_sha256'];assert summary['source_map_sha256']==oldcert['map_sha256'];assert summary['queue_sha256']==oldcert['queue_sha256']
oldmap=list(readcsv(OLD/'official5655-request-membership.csv'));oldroles={(r['source'],r['Molecule_Name']):r['request_id'] for r in oldmap};newroles={(r['source'],r['Molecule_Name']):r['request_id'] for r in official};assert newroles==oldroles
columns=oldcert['base_feature_columns'];assert len(columns)==len(set(columns))==120
oldfeatures={r['request_id']:r for r in readcsv(OLD/'features-snapshot.csv') if r['request_id'] in required};assert set(oldfeatures)==required
raw_ids=[];raw_identity={}
for row in readcsv(FULL/'raw-snapshot.csv'):
 rid=hashlib.sha256(row['raw_smiles'].encode()).hexdigest();raw_ids.append(rid);assert q[rid]==row['raw_smiles'];raw_identity[rid]=(row['raw_smiles'],row['smiles'])
assert len(raw_ids)==len(raw_identity)==32421 and set(raw_ids)==set(q)
feature_ids=[];official_matrix=[];official_ids=[];numeric_text_differences=0;numeric_mismatches=[];identity_mismatches=[]
for row in readcsv(FULL/'features-snapshot.csv'):
 rid=row['request_id'];feature_ids.append(rid);assert (row['SMILES'],row['service_smiles'])==raw_identity[rid]
 if rid in required:
  old=oldfeatures[rid]
  if any(old[k]!=row[k] for k in ('request_id','SMILES','service_smiles')):identity_mismatches.append(rid)
  aa=np.array([float(old[c]) for c in columns],dtype=np.float64);bb=np.array([float(row[c]) for c in columns],dtype=np.float64)
  assert np.isfinite(aa).all() and np.isfinite(bb).all()
  if not np.array_equal(aa,bb):numeric_mismatches.append(rid)
  numeric_text_differences+=sum(old[c]!=row[c] for c in columns)
  official_ids.append(rid);official_matrix.append(bb)
assert raw_ids==feature_ids and len(set(feature_ids))==32421;assert len(official_ids)==5655 and set(official_ids)==required;assert not numeric_mismatches and not identity_mismatches
ledger=list(readcsv(FULL/'outcome-ledger.csv'));ld={r['request_id']:r for r in ledger};assert len(ledger)==len(ld)==32421 and set(ld)==set(q);assert all(json.loads(r['errors'])==[] for r in ledger)
truth=lambda v:str(v).lower()=='true'
eligible={r['request_id'] for r in ledger if truth(r['chemistry_eligible'])};eligible_file={r['request_id'] for r in readcsv(FULL/'feature-eligible-request-ids.csv')};assert eligible==eligible_file and len(eligible)==32418 and required<=eligible
numeric=sum(truth(r['numeric_endpoint_complete']) for r in ledger);assert numeric==32419
policy=json.loads((FULL/'OUTPUT_DISPOSITION-snapshot.json').read_text());rejects={r['request_id'] for r in ledger if r['status']=='service_rejected'};unresolved={r['request_id'] for r in ledger if r['status']=='numeric_returned_unresolved_service_structure'};normalized={r['request_id'] for r in ledger if r['relation']=='exact_reviewed_internal_proton_transfer'}
assert rejects==set(policy['service_rejected_requests']) and len(rejects)==2;assert unresolved==set(policy['feature_identity_excluded_requests']) and len(unresolved)==1;assert normalized==set(policy['reviewed_standardization_requests']) and len(normalized)==1;assert not required&(rejects|unresolved)
duplicates=json.loads((FULL/'chemical-duplicate-groups.json').read_text());assert all(not v for v in duplicates.values())
ordering=np.argsort(official_ids);matrix=np.asarray(official_matrix)[ordering];sorted_ids=[official_ids[i] for i in ordering]
certificate={'verification_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Independent final-audit checksum/coverage and exact official120-vector identity check; no chemical audit rerun.','full_audit_path':str(FULL),'full_audit_summary_sha256':sha(FULL/'summary.json'),'full_audit_file_manifest_sha256':sha(FULL/'audit-artifacts-sha256.json'),'declared_audit_files_verified':len(manifest),'all_declared_audit_file_hashes_match':True,'outcomes':32421,'unique_raw_request_ids':32421,'unique_feature_request_ids':32421,'unique_ledger_request_ids':32421,'queue_ids_exactly_covered':True,'pending_collection_requests':0,'duplicate_request_ids':0,'exact_isomeric_collision_groups':0,'numeric_prediction_rows':32419,'chemistry_eligible_rows':32418,'terminal_rejections':2,'known_unresolved_graph_rows_retained_excluded':1,'unreviewed_anomalies':0,'approved_proton_transfer_rows':1,'official_train_rows':4905,'official_test_rows':750,'official_identity_and_role_mapping_unchanged':True,'official_request_and_service_SMILES_exactly_unchanged':True,'official_base_feature_columns':120,'official_numeric_values_compared':5655*120,'official_numeric_vectors_exactly_equal':True,'numeric_mismatch_rows':[],'official_numeric_text_cell_differences':numeric_text_differences,'official_all_finite_eligible':True,'official_matrix_sorted_by_request_id_sha256':hashlib.sha256(np.ascontiguousarray(matrix).tobytes()).hexdigest(),'official_sorted_request_ids_sha256':hashlib.sha256(json.dumps(sorted_ids,separators=(',',':')).encode()).hexdigest(),'evaluation_snapshot_path':str(OLD),'evaluation_scope_certificate_sha256':sha(OLD/'OFFICIAL5655_SCOPE_CERTIFICATE.json'),'raw_sha256':summary['raw_sha256'],'features_sha256':summary['features_sha256'],'queue_sha256':summary['queue_sha256'],'source_map_sha256':summary['source_map_sha256'],'output_policy_sha256':summary['reviewed_policy_sha256'],'source_supervision_disposition_separate':True,'limitations':['No outstanding acquisition outcomes or unreviewed audit anomalies; Sb remains a known unresolved returned graph and is excluded, not chemically resolved.','Terminal service rejections are retained as outcomes, not successful predictions or imputed values.','The exact proton-transfer convention is approved for feature representation only; original states and identities remain distinct.','This does not certify prediction accuracy, encoder/teacher pretraining independence or original external assay identity.','The exported dataset is a separate forthcoming roundtrip check.']}
(OUT/'FINAL_INPUT_CERTIFICATE.json').write_text(json.dumps(certificate,indent=2)+'\n');print(json.dumps({'certificate_path':str(OUT/'FINAL_INPUT_CERTIFICATE.json'),'certificate_sha256':sha(OUT/'FINAL_INPUT_CERTIFICATE.json'),**{k:certificate[k] for k in ['declared_audit_files_verified','outcomes','official_numeric_values_compared','official_numeric_vectors_exactly_equal','official_numeric_text_cell_differences','pending_collection_requests','unreviewed_anomalies']}},indent=2))
