import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import continuous_shifter as worker
from collect import Collector,save
class Test(unittest.TestCase):
 def test_explicit_opt_in_bounded_and_result_url_never_reposts(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'input.csv').write_text('SMILES\nCCO\n');settings=root/'settings.json'
   save(settings,{'allow_unknown_response_reissue':True,'max_unknown_reissues_per_batch':2})
   c=Collector(root/'input.csv',root/'run',500)
   try:
    save(c.folder(0)/'http-001.json',{'method':'POST','http_status':0,'uploaded_bytes':'12','curl_exit':56})
    with patch.object(worker,'SETTINGS',settings):
     for expected in [1,2]:
      c.set_state(0,phase='submitting')
      self.assertTrue(worker.reissue_lost_inference_response(c));self.assertEqual(c.state(0)['unknown_reissues'],expected)
     c.set_state(0,phase='submitting');self.assertFalse(worker.reissue_lost_inference_response(c))
     c.set_state(0,phase='submitting',unknown_reissues=0,result_url='https://admetlab3.scbdd.com/server/result/known');self.assertFalse(worker.reissue_lost_inference_response(c))
     c.set_state(0,phase='submitting',result_url=None)
     save(settings,{'allow_unknown_response_reissue':False});self.assertFalse(worker.reissue_lost_inference_response(c))
   finally:c.close()
if __name__=='__main__':unittest.main()
