import unittest
import numpy as np
from night.private_p1 import transform
class Tests(unittest.TestCase):
 def setUp(self):self.b=np.array([[1,2],[1,3],[3,4],[5,8]],float);self.c=np.array([[2,9],[3,5],[3,1],[9,6]],float)
 def test_anchor_identity(self):
  for op in ['identity','moment','quantile']:self.assertTrue(np.array_equal(transform(self.b,self.b,op),self.b))
 def test_moments(self):
  z=transform(self.c,self.b,'moment');np.testing.assert_allclose(z.mean(0),self.b.mean(0));np.testing.assert_allclose(z.std(0,ddof=1),self.b.std(0,ddof=1))
 def test_ties_and_rank(self):
  z=transform(self.c,self.b,'quantile');self.assertEqual(z[1,0],z[2,0])
  for j in range(2):self.assertTrue((np.diff(z[np.argsort(self.c[:,j]),j])>=0).all())
 def test_quantile_marginal_without_candidate_ties(self):
  c=np.array([[3,9],[2,5],[4,1],[9,6]],float);z=transform(c,self.b,'quantile');np.testing.assert_array_equal(np.sort(z,axis=0),np.sort(self.b,axis=0))
 def test_invalid(self):
  for c in [np.ones_like(self.b),np.full_like(self.b,np.nan),self.b[:2]]:
   with self.assertRaises(ValueError):transform(c,self.b,'moment')
if __name__=='__main__':unittest.main()
