import sys,tempfile,csv,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect import Collector,StopRun
from direct_http import Direct
class Test(unittest.TestCase):
 def test_only_explicit_connect_failure_is_retryable(self):
  for error,code,expected in [('CONNECT tunnel failed, response 502',56,'pending'),('SSL connection timeout',28,'pending'),('Operation timed out after sending request',28,'submitting')]:
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);(root/'input.csv').write_text('SMILES\nCCO\n');c=Collector(root/'input.csv',root/'output',500)
    try:
     c.set_state(0,phase='submitting')
     response=SimpleNamespace(stdout='000\t192.168.0.16\t1.2.3.4',stderr=error,returncode=code)
     with patch('direct_http.subprocess.run',return_value=response):
      with self.assertRaises(StopRun):Direct(c).request(0,c.base+'/server/screeningCal','method=2')
     self.assertEqual(c.state(0)['phase'],expected)
    finally:c.close()
if __name__=='__main__':unittest.main()
