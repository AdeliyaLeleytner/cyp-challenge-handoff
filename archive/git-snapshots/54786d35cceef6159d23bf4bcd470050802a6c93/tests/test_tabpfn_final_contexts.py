import copy,unittest,tempfile
from pathlib import Path
import numpy as np
from night.admet_full_contract_v1 import ContractError
from night.tabpfn_final import oof_contexts,query_contexts
from night.external_tabpfn_contract import NAME,SPEC,data_binding

class Tests(unittest.TestCase):
    def selection(self):return {'chosen':{'recipe':NAME,'mode':'standalone'},'recipes':{NAME:{'spec':SPEC,'selected':{'params':{'n_estimators':8}},'external_candidate':True}},'submission_lane':'native_published_placement'}
    def test_twenty_oof_contexts_train_only_masks(self):
        y=np.arange(60,dtype=float).reshape(15,4);y[2,1]=np.nan
        folds=[(np.array([i for i in range(15) if i//3!=f]),np.arange(3*f,3*f+3)) for f in range(5)]
        calls=list(oof_contexts(y,folds));self.assertEqual(len(calls),20)
        for fold,j,train,query in calls:
            self.assertFalse(set(train)&set(query));self.assertTrue(np.isfinite(y[train,j]).all());self.assertLess(max(query),15)
    def test_oof_overlap_or_wrong_fold_count_blocked(self):
        y=np.ones((15,4));folds=[(np.arange(15),np.arange(3*f,3*f+3)) for f in range(5)]
        with self.assertRaisesRegex(ContractError,'boundary'):list(oof_contexts(y,folds))
        with self.assertRaisesRegex(ContractError,'Exactlyfive'):list(oof_contexts(y,folds[:4]))
    def test_four_query_contexts_only_for_selected_tabpfn(self):
        y=np.ones((15,4));y[2,1]=np.nan
        calls=list(query_contexts(y,np.arange(15,765),self.selection()));self.assertEqual(len(calls),4);self.assertNotIn(2,calls[1][1])
        with self.assertRaisesRegex(ContractError,'unless selected'):list(query_contexts(y,np.arange(15,765),{'chosen':{'recipe':None}}))
        with self.assertRaisesRegex(ContractError,'boundary/order'):list(query_contexts(y,np.full(750,15),self.selection()))
    def test_same_content_binding_across_hosts_and_changed_data_rejected_by_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=root/'mac';b=root/'linux';a.mkdir();b.mkdir()
            for r in (a,b):(r/'folds').write_text('same folds');(r/'labels').write_text('same labels')
            x=data_binding({'folds':a/'folds','official_train':a/'labels'},['endpoint']);z=data_binding({'folds':b/'folds','official_train':b/'labels'},['endpoint']);self.assertEqual(x,z)
            (b/'labels').write_text('different labels');self.assertNotEqual(x,data_binding({'folds':b/'folds','official_train':b/'labels'},['endpoint']))
if __name__=='__main__':unittest.main()
