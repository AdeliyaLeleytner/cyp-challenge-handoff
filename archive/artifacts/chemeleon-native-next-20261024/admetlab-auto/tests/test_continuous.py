import csv,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch,Mock
from urllib.parse import parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import continuous_shifter as worker
from collect import Collector,ROOT,StopRun

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  with (ROOT/'tests/response.csv').open(encoding='utf-8-sig',newline='') as f:self.rows=list(csv.DictReader(f))
  source=self.root/'input.csv'
  with source.open('w',newline='') as f:
   w=csv.writer(f);w.writerow(['SMILES']);w.writerows([[r['raw_smiles']] for r in self.rows])
  self.c=Collector(source,self.root/'output',500)
  self.form=self.root/'form.html';self.form.write_text('<form id="form2" action="/server/screeningCal" method="post"><input name="method" value="2"></form>')
  self.gate=Mock();self.csv=ROOT/'tests/response.csv'
 def tearDown(self):self.c.close();self.tmp.cleanup()
 def test_retries_same_batch_only_after_explicit429_then_validates(self):
  calls=[]
  (self.c.root/'cookies.txt').write_text('synthetic stable cookie jar')
  def submit(i,url,payload):
   calls.append(parse_qs(payload)['smiles-list'][0])
   if len(calls)==1:self.c.set_state(0,phase='rate_limited');raise StopRun('HTTP429')
   return 302,{'location':'/server/result/test'},self.form
  with patch.object(worker,'Paced') as proxy,patch.object(worker,'Direct') as direct:
   proxy.return_value.follow.return_value=(self.c.base+'/server/screening',self.form)
   proxy.return_value.request.side_effect=submit
   direct.return_value.request.return_value=(200,{},self.csv)
   with self.assertRaises(StopRun):worker.cycle(self.c,self.gate)
   self.assertFalse(self.c.completed(0))
   self.assertTrue(worker.cycle(self.c,self.gate));self.assertTrue(self.c.completed(0))
   self.assertTrue(worker.cycle(self.c,self.gate));self.assertEqual(len(calls),2)
   self.assertEqual(calls[0],calls[1])
   self.assertEqual(proxy.return_value.follow.call_count,1,'Explicit429 retry should reuse the unchanged prepared form')
 def test_uncertain_post_is_not_repeated(self):
  with patch.object(worker,'Paced') as proxy:
   proxy.return_value.follow.return_value=(self.c.base+'/server/screening',self.form)
   proxy.return_value.request.side_effect=TimeoutError('unknown POST outcome')
   with self.assertRaises(TimeoutError):worker.cycle(self.c,self.gate)
   self.assertEqual(self.c.state(0)['phase'],'submitting')
   with self.assertRaises(StopRun):worker.cycle(self.c,self.gate)
   self.assertEqual(proxy.return_value.request.call_count,1)
 def test_invalid_csv_does_not_complete_batch(self):
  bad=self.root/'bad.csv'
  with bad.open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=self.rows[0]);w.writeheader();w.writerows([{**r,'raw_smiles':'WRONG'} for r in self.rows])
  with patch.object(worker,'Paced') as proxy,patch.object(worker,'Direct') as direct:
   proxy.return_value.follow.return_value=(self.c.base+'/server/screening',self.form)
   proxy.return_value.request.return_value=(302,{'location':'/server/result/test'},self.form)
   direct.return_value.request.return_value=(200,{},bad)
   with self.assertRaises(Exception):worker.cycle(self.c,self.gate)
   self.assertEqual(self.c.state(0)['phase'],'invalid_result');self.assertFalse(self.c.completed(0))
if __name__=='__main__':unittest.main()
