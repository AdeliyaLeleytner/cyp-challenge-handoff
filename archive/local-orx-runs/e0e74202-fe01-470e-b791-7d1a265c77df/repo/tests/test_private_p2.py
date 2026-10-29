import unittest
import numpy as np,pandas as pd
from night.private_p2 import T,SEED_T,OBS,projections,select_queries
class Tests(unittest.TestCase):
 def data(self):
  d=pd.DataFrame({'Molecule_Name':['a','b','c','d','e','f'],'SMILES':['CCO','CCC','CCN','CCCO','CCCC','CCCN']})
  for j,t in enumerate(T):d[t]=np.arange(6.)+j
  return d
 def test_query_values_do_not_enter_inputs(self):
  d=self.data();r=np.array(['seed_pool']*3+['query_candidate_pool']*3);a,b=projections(d,r);d.loc[3:,T]=987654;a2,b2=projections(d,r);pd.testing.assert_frame_equal(a,a2);pd.testing.assert_frame_equal(b,b2);self.assertEqual(set(a),{'Molecule_Name','SMILES',*SEED_T});self.assertTrue(set(T).isdisjoint(b))
 def test_only_three_seed_targets_and_disjoint_queries(self):
  a,b=projections(self.data(),np.array(['seed_pool']*3+['query_candidate_pool']*3));s,e,q=select_queries(a,b,1,2);self.assertEqual({x['seed_target'] for x in s},set(SEED_T));self.assertFalse(set(q)&set(a.Molecule_Name));self.assertLessEqual(len(q),3)
 def test_numeric_query_column_is_rejected(self):
  a,b=projections(self.data(),np.array(['seed_pool']*3+['query_candidate_pool']*3));b[T[0]]=1
  with self.assertRaises(ValueError):select_queries(a,b,1,2)
if __name__=='__main__':unittest.main()
