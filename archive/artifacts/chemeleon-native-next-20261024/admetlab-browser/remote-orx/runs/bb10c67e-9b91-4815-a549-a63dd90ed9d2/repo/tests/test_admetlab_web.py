import unittest,json,csv,io
from pathlib import Path
from night.admetlab_web import parse_batch,ContractError
class WebContract(unittest.TestCase):
 def setUp(self):
  p=Path(__file__).parent/'admetlab_fixture';self.cfg=json.loads(Path('admetlab_web_config.json').read_text());self.body=(p/'web-three.csv').read_bytes();self.inputs=[{'priority':'0',**r} for r in json.loads((p/'web-three-inputs.json').read_text())['inputs']];self.rows=list(csv.DictReader(io.StringIO(self.body.decode('utf-8-sig'))))
 def encode(self,rows):
  b=io.StringIO();w=csv.DictWriter(b,fieldnames=list(self.rows[0]));w.writeheader();w.writerows(rows);return b.getvalue().encode()
 def test_actual_schema_and_rule_counts(self):
  out,failed,_=parse_batch(self.body,self.inputs,self.cfg,'task');self.assertFalse(failed);self.assertEqual(len(out),3)
  for r in out:self.assertEqual(len(r['features']),120)
  nitro=out[1];self.assertEqual(nitro['features']['ADMETLAB::toxicityrule::Toxicophores'],2);self.assertIn('ADMETLAB::csv_extra::Other_assay_interference',nitro['features']);self.assertFalse(any('contains=' in c for c in nitro['features']))
 def test_reordering_uses_exact_identity(self):
  a,_,_=parse_batch(self.body,self.inputs,self.cfg,'task');b,_,_=parse_batch(self.encode(self.rows[::-1]),self.inputs,self.cfg,'task');self.assertEqual({x['request_id']:x['features'] for x in a},{x['request_id']:x['features'] for x in b})
 def test_missing_row_is_explicit(self):
  ok,failed,_=parse_batch(self.encode(self.rows[:-1]),self.inputs,self.cfg,'task');self.assertEqual(len(ok),2);self.assertEqual(failed[0]['request_id'],self.inputs[-1]['request_id'])
 def test_ambiguous_identity_rejected(self):
  for rows in [self.rows+[self.rows[0]],[dict(self.rows[0],raw_smiles='unknown')]+self.rows[1:]]:
   with self.assertRaises(ContractError):parse_batch(self.encode(rows),self.inputs,self.cfg,'task')
if __name__=='__main__':unittest.main()
