import sys,tempfile,json,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import continuous_shifter as worker
from collect import save,read
class Test(unittest.TestCase):
 def test_only_full_validated_size_promotes_and_cap_is_preserved(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);settings=root/'settings.json'
   save(settings,{'batch_size':100,'auto_increase':True,'ramp':[100,200,400,500]})
   with patch.object(worker,'ROOT',root),patch.object(worker,'SETTINGS',settings):
    self.assertEqual(worker.promote_after_success(50),100)
    self.assertEqual(worker.promote_after_success(100),200)
    self.assertEqual(worker.promote_after_success(200),400)
    self.assertEqual(worker.promote_after_success(400),500)
    self.assertEqual(worker.promote_after_success(500),500)
    self.assertEqual(read(settings)['batch_size'],500)
if __name__=='__main__':unittest.main()
