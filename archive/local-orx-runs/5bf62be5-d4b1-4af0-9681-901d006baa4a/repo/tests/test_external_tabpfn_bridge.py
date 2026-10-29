"""Synthetic artifact/provenance checks; no TabPFN or other learner is loaded."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import numpy as np
import pandas as pd
from night.admet_full_contract_v1 import ContractError,digest
from night.external_tabpfn_contract import SPEC,NAME,TARGETS,RUNTIME,fixed_model_contract,write_json,load_oof,load_query,check_selected_tabpfn,validate_query_request,create_query_request,load_selection_bundle
from night.final_feature_engine import select_training_oof,final_predict

class Tests(unittest.TestCase):
    def artifact(self,root,phase='oof'):
        count=4905 if phase=='oof' else 750
        official=pd.DataFrame({'Molecule_Name':['id'+str(i) for i in range(count)],'SMILES':['CC']*count,'request_id':['req'+str(i) for i in range(count)]})
        pred=official.copy()
        for j,t in enumerate(TARGETS):pred[t]=np.arange(count)/100+j
        csv=root/'predictions.csv';pred.iloc[::-1].to_csv(csv,index=False,float_format='%.17g')
        model=fixed_model_contract('a'*64,'b'*64);binding={'files':{'folds':'folds123','official_train':'official123'},'feature_columns':['ADMETLAB::'+str(i) for i in range(120)]}
        receipt={'status':'complete','phase':phase,'producer_experiment_id':'producer','endpoint_calls':20 if phase=='oof' else 4,'data_binding':binding,'model_contract':model,'folds_sha256':'folds123','blind_predictions_generated':phase=='query','runtime':{'packages':RUNTIME},'predictions_sha256':digest(csv),'query_request_sha256':'request-sha','selection_sha256':'selection-sha'}
        rp=root/'receipt.json';write_json(rp,receipt)
        manifest={'schema_version':1,'producer_experiment_id':'producer','producer_commit':'c'*40,'producer_orx_run_id':'run123','files':{'receipt':{'path':str(rp),'sha256':digest(rp)},'predictions':{'path':str(csv),'sha256':digest(csv)}}}
        mp=root/'manifest.json';write_json(mp,manifest)
        return official,model,binding,receipt,manifest,mp
    def mutate_receipt(self,root,receipt,manifest):
        write_json(root/'receipt.json',receipt);manifest['files']['receipt']['sha256']=digest(root/'receipt.json');write_json(root/'manifest.json',manifest)
    def test_complete_oof_is_id_aligned(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data,model,binding,r,m,p=self.artifact(root)
            result=load_oof(p,digest(p),binding,model,data)
            self.assertEqual(result['oof'].shape,(4905,4));np.testing.assert_allclose(result['oof'][:,0],np.arange(4905)/100)
    def test_h5_candidate_retains_exact_selected_view(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data,old,binding,r,m,p=self.artifact(root)
            model=json.loads((Path(__file__).resolve().parents[1]/'h5_selector_config.template.json').read_text())['expected_tabpfn_model_contract']
            r['model_contract']=model;self.mutate_receipt(root,r,m)
            result=load_oof(p,digest(p),binding,model,data)
            self.assertEqual(result['spec']['view'],'adme_admet');self.assertEqual(result['spec']['name'],'tabpfn35__adme600_admet120')
            with self.assertRaisesRegex(ContractError,'provenance mismatch'):load_oof(p,digest(p),binding,old,data)
    def test_oof_fold_mismatch_rejected_even_if_file_hashes_match(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data,model,binding,r,m,p=self.artifact(root);r['folds_sha256']='other-folds';self.mutate_receipt(root,r,m)
            with self.assertRaisesRegex(ContractError,'folds differ'):load_oof(p,digest(p),binding,model,data)
    def test_oof_data_or_runtime_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data,model,binding,r,m,p=self.artifact(root);different=copy.deepcopy(binding);different['files']['official_train']='different-labels'
            with self.assertRaisesRegex(ContractError,'binding mismatch'):load_oof(p,digest(p),different,model,data)
            r['runtime']={'packages':{**RUNTIME,'torch':'2.6.0'}};self.mutate_receipt(root,r,m)
            with self.assertRaisesRegex(ContractError,'runtime'):load_oof(p,digest(p),binding,model,data)
    def test_oof_forbids_premature_blind_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data,model,binding,r,m,p=self.artifact(root);r['blind_predictions_generated']=True;self.mutate_receipt(root,r,m)
            with self.assertRaisesRegex(ContractError,'must not perform blind'):load_oof(p,digest(p),binding,model,data)
    def test_missing_producer_or_changed_checkpoint_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data,model,binding,r,m,p=self.artifact(root);m['producer_orx_run_id']=None;write_json(p,m)
            with self.assertRaisesRegex(ContractError,'actual ORX'):load_oof(p,digest(p),binding,model,data)
            m['producer_orx_run_id']='run123';r['model_contract']=copy.deepcopy(model);r['model_contract']['checkpoint_sha256']='wrong';self.mutate_receipt(root,r,m)
            with self.assertRaisesRegex(ContractError,'provenance mismatch'):load_oof(p,digest(p),binding,model,data)
    def test_query_result_bound_to_selected_request(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);blind,model,binding,r,m,p=self.artifact(root,'query');request={'selection_sha256':'selection-sha'}
            values,prov=load_query(p,digest(p),request,'request-sha',binding,model,blind);self.assertEqual(values.shape,(750,4))
            with self.assertRaisesRegex(ContractError,'locked selection'):load_query(p,digest(p),request,'another-request',binding,model,blind)
    def test_cpu_selection_can_choose_external_without_running_it(self):
        n=15;x=np.arange(n,dtype=float);data=pd.DataFrame({'Molecule_Name':['id'+str(i) for i in range(n)],'SMILES':['CC']*n,'request_id':['req'+str(i) for i in range(n)]})
        y=x[:,None]+np.arange(4);lo=y-.05;hi=y+.05
        folds=[(np.array([i for i in range(n) if i//3!=f]),np.arange(3*f,3*f+3)) for f in range(5)]
        cfg={'portfolio':[{'name':'cpu','family':'kernel','view':'admet','grid':[{'alpha':1}]}],'model_seed':42,'threads':1,'blend_modes':['global','per_target'],'submission_lane':'native_published_placement'}
        calls=[]
        def predict(spec,params,tr,va,target,X,seed,threads):
            self.assertEqual(spec['name'],'cpu');calls.append((tr,va));return X['signal'][va]+np.mean(target-X['signal'][tr])+2
        external={'spec':SPEC,'params':{'n_estimators':8},'oof':y.copy(),'provenance':{'predictions_sha256':'oof-sha'}}
        with tempfile.TemporaryDirectory() as temp:
            selection,oof=select_training_oof(cfg,data,y,lo,hi,{'signal':x},folds,y+1,predict,temp,external_candidates=[external])
            self.assertEqual(len(calls),20);self.assertEqual(selection['chosen']['recipe'],NAME)
            request=create_query_request(temp,selection,{'files':{'folds':'same'}},fixed_model_contract('a'*64,'b'*64));self.assertEqual(request['expected_endpoint_calls'],4)
            with self.assertRaisesRegex(ContractError,'separate-runtime'):final_predict(cfg,selection,data,y,{'signal':np.arange(n+750)},np.arange(n,n+750),np.ones((750,4)),predict,temp)
            self.assertEqual(len(calls),20)
    def test_selection_bundle_reconstructs_locked_blend(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);official,model,binding,r,m,mp=self.artifact(root)
            tab=np.arange(4905)[:,None]/100+np.arange(4);native=tab+1;selected=native+.25*(tab-native)
            original_cfg={'submission_lane':'native_published_placement','model_seed':42};write_json(root/'producer-config.json',original_cfg)
            source=root/'external_tabpfn_oof.csv';source.write_bytes((root/'predictions.csv').read_bytes())
            provenance={'predictions_sha256':digest(source)}
            selection={'chosen':{'recipe':NAME,'name':NAME+'__native_blend_global','mode':'global','weight':.25},'recipes':{NAME:{'spec':SPEC,'selected':{'params':{'n_estimators':8}},'external_candidate':True,'external_provenance':provenance}},'submission_lane':'native_published_placement','configuration_sha256':hashlib.sha256(json.dumps(original_cfg,sort_keys=True).encode()).hexdigest()}
            frame=official.copy()
            for j,t in enumerate(TARGETS):frame[t]=selected[:,j]
            frame.to_csv(root/'selected__training_OOF.csv',index=False,float_format='%.17g')
            names={'selection':'full-data-selection.json','selection_lock':'selection-lock.json','selected_oof':'selected__training_OOF.csv','query_request':'tabpfn-query-request.json','producer_config':'producer-config.json','external_oof':'external_tabpfn_oof.csv'}
            def repin():
                write_json(root/'full-data-selection.json',selection)
                write_json(root/'selection-lock.json',{'selection_sha256':digest(root/'full-data-selection.json'),'selected_oof_sha256':digest(root/'selected__training_OOF.csv'),'submission_lane':'native_published_placement'})
                create_query_request(root,selection,binding,model)
                bundle={'schema_version':1,'kind':'selection','producer_commit':'c'*40,'producer_orx_run_id':'run','files':{k:{'path':str(root/v),'sha256':digest(root/v)} for k,v in names.items()}}
                write_json(root/'bundle.json',bundle)
            repin();result=load_selection_bundle(root/'bundle.json',digest(root/'bundle.json'),binding,model,official,native)
            np.testing.assert_allclose(result[1],selected,atol=1e-12)
            selection['chosen']['weight']=.75;repin()
            with self.assertRaisesRegex(ContractError,'does not match locked'):load_selection_bundle(root/'bundle.json',digest(root/'bundle.json'),binding,model,official,native)
    def test_losing_or_changed_recipe_cannot_request_query(self):
        with self.assertRaisesRegex(ContractError,'unless selected'):check_selected_tabpfn({'chosen':{'recipe':None,'mode':'native'}})
        model=fixed_model_contract('a'*64,'b'*64);provenance={'predictions_sha256':'oof-sha'}
        selection={'chosen':{'recipe':NAME,'name':NAME,'mode':'standalone'},'recipes':{NAME:{'spec':SPEC,'selected':{'params':{'n_estimators':8}},'external_candidate':True,'external_provenance':provenance}},'submission_lane':'native_published_placement'}
        request={'submission_lane':'native_published_placement','status':'awaiting_separate_runtime_query','expected_endpoint_calls':4,'expected_query_rows':750,'selection_sha256':'selected','selection_lock_sha256':'lock','data_binding':{'folds':'f'},'model_contract':model,'selected_option':NAME,'oof_provenance':provenance}
        validate_query_request(request,selection,'selected',{'selection_sha256':'selected'},'lock',{'folds':'f'},model)
        with self.assertRaisesRegex(ContractError,'selection hash'):validate_query_request(request,selection,'other',{'selection_sha256':'selected'},'lock',{'folds':'f'},model)
if __name__=='__main__':unittest.main()
