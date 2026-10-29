import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np,joblib
from night.admet_full_contract_v1 import ContractError
from night.admet_full_models import predict
from night.locked_h6_final import check_locked_config
from night.final_feature_engine import select_training_oof
ROOT=Path(__file__).resolve().parents[1]

class FakeHead:
    fit_calls=0
    def __init__(self,**kw):self.params=kw
    def fit(self,a,y):type(self).fit_calls+=1;self.offset=float(np.mean(y));return self
    def predict(self,a):return a[:,0]+self.offset

class Tests(unittest.TestCase):
    def test_serialization_reload_reuses_model_without_refit(self):
        FakeHead.fit_calls=0;raw=np.arange(757*720,dtype=float).reshape(757,720);raw[7,0]=np.nan
        train=np.arange(7);query=np.arange(7,757);target=np.arange(7,dtype=float)
        spec={'name':'lightgbm__adme720','family':'lightgbm','view':'adme_admet','grid':[{'num_leaves':7,'max_depth':3}]};params={'num_leaves':7,'max_depth':3}
        with tempfile.TemporaryDirectory() as temp,patch('night.admet_full_models.LGBMRegressor',FakeHead):
            artifact={'directory':temp,'target':'CYP1A2','feature_order':['f'+str(i) for i in range(720)],'context':{'synthetic':True}}
            first=predict(spec,params,train,query,target,{'adme_admet':raw},42,2,artifact=artifact)
            second=predict(spec,params,train,query,target,{'adme_admet':raw},42,2,artifact=artifact)
            np.testing.assert_array_equal(first,second);self.assertEqual(FakeHead.fit_calls,1)
            saved=joblib.load(Path(temp)/'head.joblib');self.assertIsNone(saved['preprocessing']['scaler']);self.assertEqual(saved['preprocessing']['imputer'].statistics_[0],np.median(raw[train,0]))
            receipt=json.loads((Path(temp)/'receipt.json').read_text());self.assertTrue(receipt['reload_exact']);self.assertEqual(receipt['additional_refits_for_verification'],0);self.assertEqual(receipt['query_rows'],750)
            altered={**artifact,'feature_order':artifact['feature_order'][::-1]}
            with self.assertRaisesRegex(ContractError,'context/hash'):predict(spec,params,train,query,target,{'adme_admet':raw},42,2,artifact=altered)
            self.assertEqual(FakeHead.fit_calls,1)
    def test_locked_recipe_rejects_other_family_mode_or_gpu_runtime(self):
        cfg=json.loads((ROOT/'final_feature_config.json').read_text());check_locked_config(cfg)
        bad=copy.deepcopy(cfg);bad['blend_modes']=['global']
        with self.assertRaises(ContractError):check_locked_config(bad)
        bad=copy.deepcopy(cfg);bad['portfolio'][0]['name']='lightgbm__admet'
        with self.assertRaises(ContractError):check_locked_config(bad)
        bad=copy.deepcopy(cfg);bad['required_runtime']['torch']='2.8.0+cu128'
        with self.assertRaisesRegex(ContractError,'CPU runtime'):check_locked_config(bad)
    def test_per_target_decision_is_retained_even_at_boundary(self):
        import pandas as pd
        n=15;x=np.arange(n,dtype=float);data=pd.DataFrame({'Molecule_Name':['m'+str(i) for i in range(n)],'SMILES':['CC']*n});y=x[:,None]+np.arange(4);lo=y;hi=y
        cfg={'portfolio':[{'name':'lightgbm__adme720','family':'lightgbm','view':'adme_admet','grid':[{'num_leaves':7,'max_depth':3}]}],'final_selection_mode':'validated_per_target_pair','blend_modes':['per_target'],'model_seed':42,'threads':1,'submission_lane':'native_published_placement'}
        folds=[(np.array([i for i in range(n) if i//3!=f]),np.arange(3*f,3*f+3)) for f in range(5)]
        def no_model(spec,params,tr,va,target,X,seed,threads):return X['x'][va]+np.mean(target-X['x'][tr])+3
        with tempfile.TemporaryDirectory() as temp:
            selected,_=select_training_oof(cfg,data,y,lo,hi,{'x':x},folds,y,no_model,temp)
            self.assertEqual(selected['chosen']['mode'],'per_target');self.assertEqual(selected['chosen']['name'],'lightgbm__adme720__native_blend_per_target');np.testing.assert_array_equal(selected['chosen']['weight'],np.zeros(4))
if __name__=='__main__':unittest.main()
