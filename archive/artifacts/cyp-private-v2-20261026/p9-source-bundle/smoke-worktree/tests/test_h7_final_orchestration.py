import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np,pandas as pd
from night.admet_full_contract_v1 import ContractError
from night.admet_full_math import placement_constants
from night.final_feature_engine import select_three_expert_oof,final_predict_three,THREE_EXPERT_ORDER
ROOT=Path(__file__).resolve().parents[1]
class Tests(unittest.TestCase):
    def test_fixed_three_experts_train_only_lp_and_eight_refits(self):
        n=15;x=np.arange(n+750,dtype=float);data=pd.DataFrame({'Molecule_Name':['id'+str(i) for i in range(n)],'SMILES':['CC']*n,'request_id':['r'+str(i) for i in range(n)]})
        y=x[:n,None]+np.arange(4);lo=y-.05;hi=y+.05;y[1,2]=np.nan
        folds=[(np.array([i for i in range(n) if i//3!=f]),np.arange(f*3,f*3+3)) for f in range(5)]
        cfg={'portfolio':[{'name':name,'family':'lightgbm','view':view,'grid':[{'num_leaves':7,'max_depth':3},{'num_leaves':15,'max_depth':4}]} for name,view in [('lightgbm__admet','admet'),('lightgbm__adme720','adme_admet')]],'model_seed':42,'threads':1,'blend_modes':['global_three_expert'],'final_selection_mode':'global_three_expert','submission_lane':'native_published_placement'}
        calls=[]
        def no_model(spec,params,train,query,target,X,seed,threads):
            self.assertFalse(set(train)&set(query));self.assertTrue(np.isfinite(target).all());self.assertLess(max(train),n)
            calls.append((spec['name'],train.copy(),query.copy()));offset=np.mean(target-X['signal'][train]);bias=-1 if spec['name']=='lightgbm__admet' else 2
            return X['signal'][query]+offset+bias
        with tempfile.TemporaryDirectory() as temp:
            native=x[:n,None]+np.arange(4)+1
            selected,oof=select_three_expert_oof(cfg,data,y,lo,hi,{'signal':x},folds,native,no_model,temp,placement_constants(ROOT/'vendor/briford_native/cyp_recalibrate.py'))
            self.assertEqual(len(calls),80);self.assertTrue(all(max(c[2])<n for c in calls))
            self.assertEqual(selected['chosen']['expert_order'],THREE_EXPERT_ORDER);w=np.array(selected['chosen']['weights']);self.assertAlmostEqual(w.sum(),1);self.assertTrue((w>=0).all())
            raw=final_predict_three(cfg,selected,data,y,{'signal':x},np.arange(n,n+750),x[n:,None]+np.arange(4)+1,no_model,temp)
            self.assertEqual(raw.shape,(750,4));self.assertEqual(len(calls),88);self.assertTrue(all(min(c[2])>=n for c in calls[-8:]))
            broken=copy.deepcopy(selected);broken['chosen']['expert_order']=THREE_EXPERT_ORDER[::-1]
            with self.assertRaises(ContractError):final_predict_three(cfg,broken,data,y,{'signal':x},np.arange(n,n+750),raw,no_model,temp)
if __name__=='__main__':unittest.main()
