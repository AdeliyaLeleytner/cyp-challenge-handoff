import unittest
from unittest.mock import patch
from night.strict_fullfit_runner import run
class Test(unittest.TestCase):
 def test_preparation_node_cannot_launch_training(self):
  with patch('night.strict_fullfit_runner.preflight') as preflight:
   with self.assertRaisesRegex(AssertionError,'Preparation-only'):
    run({'training_enabled':False})
   preflight.assert_not_called()
if __name__=='__main__':unittest.main()
