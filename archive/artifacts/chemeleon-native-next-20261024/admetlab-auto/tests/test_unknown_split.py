import sys,csv,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import continuous_shifter as worker
from collect import Collector,save,read,sha
class Tests(unittest.TestCase):
 def case(self,n=200,status=0,result_url=None,uploaded=100,reissues=2):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name);source=root/'input.csv'
  with source.open('w',newline='') as f:
   w=csv.writer(f);w.writerow(['SMILES']);w.writerows([['C'*i] for i in range(1,n+1)])
  c=Collector(source,root/'run',500);self.addCleanup(c.close)
  c.set_state(0,phase='submitting',unknown_reissues=reissues,result_url=result_url)
  save(c.folder(0)/'http-1.json',{'method':'POST','http_status':status,'uploaded_bytes':str(uploaded),'curl_exit':28})
  settings=root/'worker-settings.json';save(settings,{'allow_unknown_batch_split':True,'minimum_unknown_split_size':50,'max_unknown_reissues_per_batch':2,'batch_size':n})
  before=sha(source)
  with patch.object(worker,'ROOT',root),patch.object(worker,'SETTINGS',settings):ok=worker.split_unknown_batch(c)
  self.assertEqual(sha(source),before)
  return ok,c.state(0),read(settings),read(root/'uncertain-submissions.json',{})
 def test_split_preserves_unknown_and_inputs(self):
  for n,target in [(200,100),(100,50)]:
   ok,state,settings,registry=self.case(n)
   self.assertTrue(ok);self.assertEqual(state['original_outcome'],'unknown');self.assertFalse(state['not_submitted']);self.assertEqual(settings['batch_size'],target);self.assertEqual(len(registry['submissions'][0]['request_ids']),n)
 def test_known_result_is_not_split(self):self.assertFalse(self.case(result_url='https://admetlab3.scbdd.com/server/result/saved')[0])
 def test_explicit_rejection_and_preorigin_are_not_unknown_split(self):
  self.assertFalse(self.case(status=429)[0]);self.assertFalse(self.case(uploaded=0)[0])
 def test_minimum_and_reissue_cap(self):
  self.assertFalse(self.case(n=50)[0]);self.assertFalse(self.case(reissues=1)[0])
if __name__=='__main__':unittest.main()
