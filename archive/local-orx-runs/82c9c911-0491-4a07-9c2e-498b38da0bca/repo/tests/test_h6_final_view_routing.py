import unittest
from unittest.mock import patch
import numpy as np
from night.admet_full_models import predict
class Tests(unittest.TestCase):
    def test_only_exact_adme_view_enters_lightgbm(self):
        train=np.array([0,1,2]);query=np.array([3,4]);target=np.array([1.,2.,3.])
        X={'adme':np.arange(5*600,dtype=float).reshape(5,600),'adme_admet':np.arange(5*720,dtype=float).reshape(5,720),'admet':np.full((5,120),-999.),'structure':np.full((5,2050),-999.)}
        seen=[]
        class NoModel:
            def __init__(self,**kw):self.kw=kw
            def fit(self,a,y):seen.append((a.copy(),y.copy(),self.kw));return self
            def predict(self,b):seen.append(b.copy());return np.zeros(len(b))
        with patch('night.admet_full_models.LGBMRegressor',NoModel):
            for view,width in [('adme',600),('adme_admet',720)]:
                predict({'family':'lightgbm','view':view},{'num_leaves':7,'max_depth':3},train,query,target,X,42,2)
                np.testing.assert_array_equal(seen[-2][0],X[view][train]);np.testing.assert_array_equal(seen[-1],X[view][query]);self.assertEqual(seen[-1].shape[1],width)
                self.assertEqual(seen[-2][2]['n_estimators'],220)
if __name__=='__main__':unittest.main()
