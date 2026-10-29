import sys,tempfile,json,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import curl_queue as q
from collect import save,StopRun

class FakeCollector:
 def __init__(self,root):self.root=root;self.batches=[[{}]];self.s={'phase':'pending'};self.done=False
 def completed(self,i):return self.done
 def state(self,i):return dict(self.s)
 def folder(self,i):return self.root/'batch'
 def set_state(self,i,**changes):self.s.update(changes)
 def emit(self,*args,**kwargs):pass

class Tests(unittest.TestCase):
 def run_case(self,mode,outcome,due=True):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name);c=FakeCollector(root)
  schedule={'status':'active','next_allowed_at':q.iso(time.time()+(-1 if due else 600)),'consecutive_429':0}
  save(root/'curl-control.json',{'mode':mode,'trial_batch':1})
  def process(i):
   if outcome=='429':c.set_state(i,phase='rate_limited',retry_not_before=None);raise StopRun('HTTP429')
   c.done=True;c.set_state(i,phase='complete')
  with patch.object(q,'ROOT',root),patch.object(q,'initialize',return_value=schedule),patch.object(q,'check_route',return_value={}),patch.object(q,'guard_uncached_batch',return_value=None),patch.object(q,'merge_all',return_value={'rows':500}),patch.object(q,'RecordedDirect') as transport:
   transport.return_value.process.side_effect=process
   result=q.run_once(c)
   if not due:transport.assert_not_called()
  return result,q.read(root/'curl-control.json'),q.read(root/'schedule.json')
 def test_no_network_before_cooldown(self):
  result,_,_=self.run_case('awaiting_trial','success',False);self.assertEqual(result['status'],'waiting')
 def test_failed_trial_cannot_enable_bulk(self):
  result,control,schedule=self.run_case('awaiting_trial','429')
  self.assertEqual(result['status'],'trial_failed');self.assertEqual(control['mode'],'trial_failed');self.assertEqual(schedule['status'],'needs_attention')
 def test_429_after_success_preserves_retry_mode_and_waits(self):
  result,control,schedule=self.run_case('curl_only','429')
  self.assertEqual(result['status'],'rate_limited');self.assertEqual(control['mode'],'curl_only')
  self.assertGreater(q.timestamp(schedule['next_allowed_at'])-time.time(),1190)
 def test_successful_trial_records_success_and_cooldown(self):
  result,control,schedule=self.run_case('awaiting_trial','success')
  self.assertIn(result['status'],('batch_complete','complete'));self.assertIn('trial_success_at',control)
  self.assertGreater(q.timestamp(schedule['next_allowed_at'])-time.time(),590)
if __name__=='__main__':unittest.main()
