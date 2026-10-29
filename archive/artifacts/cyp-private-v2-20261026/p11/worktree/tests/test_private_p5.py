import unittest
import numpy as np
from night.private_p5 import mix,fixed_map,T
class Tests(unittest.TestCase):
 def test_absent_is_exact_base(self):
  b=np.arange(20.).reshape(5,4);f=b+3;np.testing.assert_array_equal(mix(b,f,[.2,.4,.6,.8],False),b)
 def test_weight_endpoints(self):
  b=np.arange(20.).reshape(5,4);f=b+3;np.testing.assert_array_equal(mix(b,f,[0]*4,True),b);np.testing.assert_array_equal(mix(b,f,[1]*4,True),f)
 def test_fixed_reference_mean_not_candidate_mean(self):
  b=np.arange(20.).reshape(5,4);cal={t.split('_')[0]:{'scale':2.,'offset':1.} for t in T};z=fixed_map(b+3,b.mean(0),cal);expected=np.maximum(b.mean(0)+2*(b+3-b.mean(0))+1,1);np.testing.assert_array_equal(z,expected)
 def test_invalid_weights(self):
  with self.assertRaises(ValueError):mix(np.ones((3,4)),np.ones((3,4)),[2]*4,True)
if __name__=='__main__':unittest.main()
