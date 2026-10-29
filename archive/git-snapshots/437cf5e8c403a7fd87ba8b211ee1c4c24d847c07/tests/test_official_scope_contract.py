import unittest,json,hashlib
from pathlib import Path
from night.admet_outcome_contract import validate_feature_snapshot,require_official_coverage,validate_status_flags,ContractError,SUFFIX

class Tests(unittest.TestCase):
 def test_missing_one_official_request_stops(self):
  ids={f'request{i}' for i in range(5655)}
  with self.assertRaisesRegex(ContractError,'Missing official'):require_official_coverage(ids,ids-{'request17'},set())
 def test_excluded_official_request_stops(self):
  ids={f'request{i}' for i in range(5655)}
  with self.assertRaisesRegex(ContractError,'rejected or feature-ineligible'):require_official_coverage(ids,ids,{'request17'})
 def fixture(self):
  columns={f'endpoint{i}':f'ADMETLAB::test::{i}' for i in range(120)}
  raw={'raw_smiles':'Cl','smiles':'Cl',**{key:'Invalid Molecule' for key in columns}}
  rid=hashlib.sha256(b'Cl').hexdigest();feature={'request_id':rid,**{base:'' for base in columns.values()},**{base+SUFFIX:'1.0' for base in columns.values()}}
  approved={rid:{'request_smiles':'Cl','service_smiles':'Cl','kind':'service_rejected','raw_row_sha256':hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()}}
  return columns,raw,feature,approved
 def test_approved_rejection_remains_blank(self):
  columns,raw,feature,approved=self.fixture();self.assertTrue(validate_status_flags(raw,feature,columns,approved));self.assertTrue(all(feature[x]=='' for x in columns.values()))
 def test_rejected_values_cannot_be_filled(self):
  columns,raw,feature,approved=self.fixture();feature[next(iter(columns.values()))]='0'
  with self.assertRaisesRegex(ContractError,'fabricated'):validate_status_flags(raw,feature,columns,approved)
 def test_unknown_rejection_cannot_pass(self):
  columns,raw,feature,_=self.fixture()
  with self.assertRaisesRegex(ContractError,'Unapproved'):validate_status_flags(raw,feature,columns,{})
 def test_wrong_rejection_flag_cannot_pass(self):
  columns,raw,feature,approved=self.fixture();feature[next(iter(columns.values()))+SUFFIX]='0'
  with self.assertRaisesRegex(ContractError,'indicator'):validate_status_flags(raw,feature,columns,approved)
 def test_final_default_refuses_scoped_snapshot(self):
  cfg=json.loads((Path(__file__).resolve().parents[1]/'full_feature_config.json').read_text());cfg['stage']='finalfit'
  with self.assertRaisesRegex(ContractError,'all32421'):validate_feature_snapshot(cfg)

if __name__=='__main__':unittest.main()
