import unittest,tempfile
from pathlib import Path
import numpy as np,pandas as pd
from night.simplex_strae import fit_simplex
from night.admet_full_math import blend_weight,primary
from night.h7_inputs import read_vector
from night.admet_full import TARGETS
class SimplexTests(unittest.TestCase):
 def setUp(self):self.y=np.arange(20,dtype=float).reshape(5,4);self.p=np.stack([self.y+2,self.y-1],axis=-1)
 def test_unique_two_expert_parity(self):
  w,m=fit_simplex(self.y,self.p,self.y,self.y);q,_=blend_weight(self.y,self.p[:,:,0],self.p[:,:,1],self.y,self.y);self.assertAlmostEqual(w[1],q,places=8);self.assertLess(m['training_OOF_ST_RAE'],1e-8);self.assertAlmostEqual(w.sum(),1)
 def test_interval_objective_parity(self):
  lo=self.y-.2;hi=self.y+.1;w,m=fit_simplex(self.y,self.p,lo,hi);q,old=blend_weight(self.y,self.p[:,:,0],self.p[:,:,1],lo,hi);self.assertAlmostEqual(m['training_OOF_ST_RAE'],old['blend_training_OOF_ST_RAE'],places=8)
 def test_three_simplex_bounds(self):
  p=np.concatenate([self.p,(self.y+.3*np.sin(self.y))[:,:,None]],axis=2);w,m=fit_simplex(self.y,p,self.y,self.y);self.assertTrue((w>=0).all() and (w<=1).all());self.assertAlmostEqual(w.sum(),1);self.assertAlmostEqual(primary(self.y,p@w,self.y,self.y),m['training_OOF_ST_RAE'])
 def test_boundary_no_intercept(self):
  p=np.stack([self.y+1,self.y+2,self.y+3],axis=-1);w,m=fit_simplex(self.y,p,self.y,self.y);self.assertAlmostEqual(w[0],1);self.assertGreater(m['training_OOF_ST_RAE'],0)
 def test_tied_experts_valid(self):
  p=np.stack([self.y,self.y,self.y],axis=-1);w,m=fit_simplex(self.y,p,self.y,self.y);self.assertAlmostEqual(w.sum(),1);self.assertEqual(m['training_OOF_ST_RAE'],0)
 def test_missing_labels_ignored(self):
  y=self.y.copy();y[0,0]=np.nan;p=self.p.copy();p[0,0,:]=np.nan;w,m=fit_simplex(y,p,y,y);self.assertEqual(m['observed_per_target'],[4,5,5,5]);self.assertLess(m['training_OOF_ST_RAE'],1e-8)
 def test_bad_observed_prediction(self):
  self.p[0,0,0]=np.nan
  with self.assertRaises(ValueError):fit_simplex(self.y,self.p,self.y,self.y)
 def test_bad_bounds_or_denominator(self):
  with self.assertRaises(ValueError):fit_simplex(self.y,self.p,self.y+1,self.y)
  with self.assertRaises(ValueError):fit_simplex(np.ones((5,4)),self.p,np.ones((5,4)),np.ones((5,4)))
 def test_alignment_and_smiles_fail_closed(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'p.csv';v=pd.DataFrame({'Molecule_Name':['a','b'],'SMILES':['C','N'],**{t:[1.,2.] for t in TARGETS}});v.to_csv(f,index=False);read_vector(f,['a','b'],['C','N'])
   with self.assertRaises(Exception):read_vector(f,['b','a'],['N','C'])
   with self.assertRaises(Exception):read_vector(f,['a','b'],['C','O'])
if __name__=='__main__':unittest.main()
