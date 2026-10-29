"""Synthetic orchestration checks; predictor callback performs no model fit/inference."""
import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
import pandas as pd
from night.admet_full_contract_v1 import ContractError
from night.final_feature_contract import check_configuration,validate_full_goal,validate
from night.final_feature_engine import TARGETS,align_prediction,native_vectors,select_training_oof,final_predict,export_submission,validate_export
from night.final_feature_folds import validate_folds
ROOT=Path(__file__).resolve().parents[1]

class Tests(unittest.TestCase):
    def synthetic(self):
        n,q=15,6;x=np.arange(n+q,dtype=float)/2
        data=pd.DataFrame({'Molecule_Name':['train'+str(i) for i in range(n)],'SMILES':['C'*(i+1) for i in range(n)]})
        y=x[:n,None]+np.arange(4)[None,:];lo=y-.05;hi=y+.05;y[1,2]=np.nan
        native=x[:n,None]+np.arange(4)[None,:]+1
        folds=[]
        for f in range(5):
            val=np.arange(f*3,(f+1)*3);train=np.array([i for i in range(n) if i not in val]);folds.append((train,val))
        cfg={'portfolio':[{'name':'toy','family':'kernel','view':'admet','grid':[{'alpha':1.0}]}],'model_seed':42,'threads':1,'blend_modes':['global','per_target'],'submission_lane':'raw'}
        calls=[]
        def predictor(spec,params,train,query,target,X,seed,threads):
            self.assertFalse(set(train)&set(query));self.assertTrue(all(i<n for i in train));self.assertTrue(np.isfinite(target).all())
            offset=np.mean(target-X['admet'][train,0]);calls.append({'train':train.tolist(),'query':query.tolist(),'target':target.tolist()})
            return X['admet'][query,0]+offset
        return cfg,data,y,lo,hi,{'admet':x[:,None]},folds,native,predictor,calls
    def test_ids_are_aligned_not_positionally_joined(self):
        official=pd.DataFrame({'Molecule_Name':['a','b','c'],'SMILES':['C','CC','CCC']});frame=official.copy()
        for j,t in enumerate(TARGETS):frame[t]=np.arange(3)+j
        values=align_prediction(frame.iloc[[2,0,1]],official);np.testing.assert_array_equal(values[:,0],[0,1,2])
    def test_duplicate_missing_or_graph_swapped_predictions_rejected(self):
        official=pd.DataFrame({'Molecule_Name':['a','b'],'SMILES':['C','CC']});frame=official.copy()
        for t in TARGETS:frame[t]=[1.,2.]
        with self.assertRaises(ContractError):align_prediction(pd.concat([frame.iloc[:1],frame.iloc[:1]]),official)
        with self.assertRaises(ContractError):align_prediction(frame.iloc[:1],official)
        frame['SMILES']=['CC','C']
        with self.assertRaisesRegex(ContractError,'SMILES'):align_prediction(frame,official)
    def test_selection_then_final_refit_boundaries_and_all_metrics(self):
        cfg,data,y,lo,hi,X,folds,native,predict,calls=self.synthetic()
        with tempfile.TemporaryDirectory() as tmp:
            selection,oof=select_training_oof(cfg,data,y,lo,hi,X,folds,native,predict,tmp)
            self.assertEqual(selection['chosen']['name'],'toy');self.assertEqual(len(calls),20)
            self.assertTrue(all(max(c['query'])<len(data) for c in calls))
            self.assertEqual(set(selection['chosen']['training_OOF']['macro']),{'ST_RAE','MAE','R2','Spearman','Kendall'})
            result=final_predict(cfg,selection,data,y,X,np.arange(15,21),np.ones((6,4)),predict,tmp)
            self.assertEqual(result.shape,(6,4));self.assertEqual(len(calls),24)
            self.assertTrue(all(min(c['query'])>=15 for c in calls[-4:]));self.assertNotIn(1,calls[-2]['train'])
    def test_validated_pair_does_not_reselect_standalone_family(self):
        cfg,data,y,lo,hi,X,folds,native,predict,calls=self.synthetic();cfg.update(final_selection_mode='validated_global_pair',blend_modes=['global'])
        with tempfile.TemporaryDirectory() as tmp:
            selection,oof=select_training_oof(cfg,data,y,lo,hi,X,folds,native,predict,tmp)
            self.assertEqual(selection['chosen']['name'],'toy__native_blend_global');self.assertEqual(selection['chosen']['mode'],'global')
    def test_lane_cannot_change_after_selection(self):
        cfg,data,y,lo,hi,X,folds,native,predict,calls=self.synthetic()
        with tempfile.TemporaryDirectory() as tmp:
            selection,oof=select_training_oof(cfg,data,y,lo,hi,X,folds,native,predict,tmp)
            cfg['submission_lane']='native_published_placement'
            with self.assertRaisesRegex(ContractError,'lane changed'):final_predict(cfg,selection,data,y,X,np.arange(15,21),np.ones((6,4)),predict,tmp)
            self.assertEqual(len(calls),20)
    def test_selection_file_cannot_change_before_test_prediction(self):
        cfg,data,y,lo,hi,X,folds,native,predict,calls=self.synthetic()
        with tempfile.TemporaryDirectory() as tmp:
            selection,_=select_training_oof(cfg,data,y,lo,hi,X,folds,native,predict,tmp)
            p=Path(tmp)/'full-data-selection.json';p.write_text(p.read_text()+' ')
            with self.assertRaisesRegex(ContractError,'lock changed'):final_predict(cfg,selection,data,y,X,np.arange(15,21),np.ones((6,4)),predict,tmp)
    def test_leaked_fold_indices_rejected_before_prediction(self):
        cfg,data,y,lo,hi,X,folds,native,predict,calls=self.synthetic();folds[0]=(np.arange(15),folds[0][1])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ContractError,'leakage'):select_training_oof(cfg,data,y,lo,hi,X,folds,native,predict,tmp)
            self.assertEqual(calls,[])
    def test_official_output_750_roundtrip_and_validator(self):
        blind=pd.DataFrame({'Molecule_Name':['blind'+str(i) for i in range(750)],'SMILES':['CC']*750})
        values=np.arange(750)[:,None]/100+np.arange(4)[None,:]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'submission.csv';receipt=export_submission(path,blind,values);self.assertEqual(receipt['rows'],750)
            from vendor.final_activity_validation import validate_activity_submission
            ok,errors=validate_activity_submission(path,set(blind.Molecule_Name));self.assertTrue(ok,errors)
            frame=pd.read_csv(path);self.assertEqual(list(frame.columns),['SMILES','Molecule_Name']+TARGETS)
            with self.assertRaisesRegex(ContractError,'order'):validate_export(frame.iloc[::-1],blind)
    def test_nonfinite_and_flat_output_blocked(self):
        blind=pd.DataFrame({'Molecule_Name':['a','b','c'],'SMILES':['C','CC','CCC']})
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ContractError,'Near-constant'):export_submission(Path(tmp)/'x.csv',blind,np.ones((3,4)))
            vals=np.arange(12,dtype=float).reshape(3,4);vals[0,0]=np.nan
            with self.assertRaisesRegex(ContractError,'Nonfinite'):export_submission(Path(tmp)/'x.csv',blind,vals)
    def test_partial_official_complete_snapshot_cannot_unlock_finalfit(self):
        approval={'approved_for_finalfit':True,'terminal_count':18460,'audited_requests':18460,'pending_count':13961,'official_eligible_rows':5655}
        with self.assertRaisesRegex(ContractError,'Partial acquisition'):validate_full_goal(approval,{}, {})
    def test_terminal_failure_allowed_only_with_full_official_eligibility_and_pins(self):
        keys=['raw_features','numeric_features','queue','id_map','official_train','official_test','feature_schema','full_outcome_audit','outcome_ledger','feature_eligible_ids','data_disposition','output_disposition','reviewed_exceptions','service_rejections','feature_exclusions'];feature={k:{'sha256':k} for k in keys};final={k:{'sha256':k} for k in ('folds','strict_pairs')}
        approval={'approved_for_finalfit':True,'terminal_count':32421,'audited_requests':32421,'pending_count':0,'successful_numeric_count':32420,'service_failed_count':1,'official_eligible_rows':5655,'input_sha256':{k:k for k in keys+['folds','strict_pairs']}}
        validate_full_goal(approval,feature,final)
        approval['official_eligible_rows']=5654
        with self.assertRaisesRegex(ContractError,'5655'):validate_full_goal(approval,feature,final)
    def test_no_silent_tabpfn_substitution(self):
        cfg=json.loads((ROOT/'final_feature_config.json').read_text());cfg['portfolio']=[{'name':'tabpfn35__admet120','family':'tabpfn35','view':'admet','grid':[{'n_estimators':8}]}]
        with self.assertRaisesRegex(ContractError,'Unsupported family'):check_configuration(cfg)
    def test_null_inputs_fail_closed(self):
        cfg=json.loads((ROOT/'final_feature_config.json').read_text())
        with self.assertRaisesRegex(ContractError,'must be pinned'):validate(cfg)
    def test_native_component_oof_reconstruction_and_coverage(self):
        official=pd.DataFrame({'Molecule_Name':['a','b','c'],'SMILES':['C','CC','CCC']})
        for t in TARGETS:official[t]=[4.,5.,6.]
        blind=pd.DataFrame({'Molecule_Name':['q0','q1','q2'],'SMILES':['N','NN','NNN']})
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths={}
            for member,offset in [('union18',1),('mtaux8',3),('2d6isoform6',5),('2d6single',7)]:
                component=pd.DataFrame({'molecule_name':official.Molecule_Name})
                for j,t in enumerate(TARGETS):
                    if member in ('union18','mtaux8') or j==2:component[t.lower()+'_pred']=np.arange(3)+offset
                paths[member+'_oof']=root/(member+'.csv');component.iloc[::-1].to_csv(paths[member+'_oof'],index=False)
            for name,ids in [('native_official_oof',official),('native_blind_raw',blind),('native_blind_placed',blind)]:
                frame=ids[['Molecule_Name','SMILES']].copy()
                for j,t in enumerate(TARGETS):frame[t]=np.arange(3)+(4 if j==2 else 2)
                paths[name]=root/(name+'.csv');frame.iloc[::-1].to_csv(paths[name],index=False)
            oof,raw,placed=native_vectors(paths,official,blind)
            np.testing.assert_array_equal(oof[:,2],[4,5,6]);np.testing.assert_array_equal(oof[:,0],[2,3,4])
            bad=pd.read_csv(paths['2d6single_oof']);bad.loc[0,TARGETS[2].lower()+'_pred']=99;bad.to_csv(paths['2d6single_oof'],index=False)
            with self.assertRaisesRegex(ContractError,'disagrees'):native_vectors(paths,official,blind)
    def test_query_start_receipt_is_separate_from_immutable_selection_lock(self):
        cfg,data,y,lo,hi,X,folds,native,predict,calls=self.synthetic()
        with tempfile.TemporaryDirectory() as tmp:
            selection,_=select_training_oof(cfg,data,y,lo,hi,X,folds,native,predict,tmp)
            lock=Path(tmp)/'selection-lock.json';before=lock.read_bytes()
            final_predict(cfg,selection,data,y,X,np.arange(15,21),np.ones((6,4)),predict,tmp)
            self.assertEqual(lock.read_bytes(),before)
            self.assertTrue(json.loads((Path(tmp)/'final-query-started.json').read_text())['final_query_inference_started'])
    def test_parent_overlap_in_full_folds_rejected(self):
        data=pd.DataFrame({'Molecule_Name':[str(i) for i in range(10)],'SMILES':['C','C','CC','CCC','CCCC','CCCCC','CCCCCC','CCCCCCC','CCCCCCCC','CCCCCCCCC']})
        folds=[]
        for f in range(5):
            val=[str(f),str(f+5)];folds.append({'train_ids':[n for n in data.Molecule_Name if n not in val],'val_ids':val})
        with self.assertRaisesRegex(ContractError,'Parent overlap'):validate_folds({'folds':folds},data,['request'+str(i) for i in range(10)],{})

if __name__=='__main__':unittest.main()
