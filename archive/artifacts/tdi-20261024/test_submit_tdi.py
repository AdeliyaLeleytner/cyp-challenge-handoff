"""Hermetic deployment tests. All transports are fake; no network or training."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('submit_tdi',HERE/'submit_tdi.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
API=json.loads((HERE/'sources/submission-preflight/live-api-info.json').read_text())


class FakeTransport:
    def __init__(self,mode='accept',info=None):self.mode=mode;self.calls=[];self.info=info or API
    def api_info(self):return self.info
    def submit_once(self,args,path):
        self.calls.append((args,Path(path).read_bytes()))
        if self.mode=='raise':raise TimeoutError('Never log fake sensitive exception text')
        if self.mode=='unknown':return {'unexpected':'shape'}
        if self.mode=='reject':return 'Error: synthetic rejection'
        return "Submission received from 'AdeliyaLL-CYP' for the Classification Prediction track. Your predictions are being processed."


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.campaign=Path(self.temp.name);self.root=self.campaign/'candidate';self.root.mkdir()
        self.csv=self.root/'submission_tdi.csv';self.csv.write_text('SMILES,Molecule_Name,CYP2D6_is_TDI,CYP3A4_is_TDI\nC,A,True,False\n')
        sig=m._transport_namespace()['_schema_signature'](API)
        self.contract={'api_signature':sig,'space_revision':m.SPACE_REVISION}
        self.verified={'provenance':{'model_tag':'TDI synthetic test artifact; do not submit','gradio_client_version':'2.7.2'},
            'comparisons':{'own750':{'delta_vs_best':.1},'briford529':{'delta_vs_best':.1}},
            'policy_sha256':{},'validation':{'test_fixture':True},'evidence':[], 'submission_path':str(self.csv)}
    def tearDown(self):self.temp.cleanup()
    def prepared(self):
        # Transport tests isolate deployment machinery, not fake a completed ML run.
        with patch.object(m,'_verify_candidate',return_value=self.verified),patch.object(m,'check_live_contract',return_value=self.contract):
            return m.prepare(self.root,self.campaign)
    def send(self,prepared,transport):
        with patch.object(m,'check_live_contract',return_value=self.contract):return m.send(prepared,self.campaign,transport)
    def test_accept_once_and_classification_track(self):
        p=self.prepared();fake=FakeTransport();receipt=self.send(p,fake)
        self.assertEqual(receipt['status'],'accepted_pending');self.assertEqual(len(fake.calls),1)
        attempt=m.read_json(Path(p['ledger_dir'])/'attempts'/p['csv_sha256']/'attempt.json')
        self.assertEqual(attempt['track'],'classification')
        args=fake.calls[0][0];self.assertEqual(args['track_select'],'Classification Prediction')
        self.assertEqual(args['username'],'AdeliyaLL');self.assertEqual(args['user_alias'],'AdeliyaLL-CYP')
        self.assertTrue(args['anon_checkbox']);self.assertFalse(args['paper_checkbox']);self.assertFalse(args['open_code_checkbox'])
        with self.assertRaises(RuntimeError):self.send(p,fake)
        self.assertEqual(len(fake.calls),1)
    def test_unknown_response_never_retried(self):
        p=self.prepared();fake=FakeTransport('unknown');receipt=self.send(p,fake)
        self.assertEqual(receipt['status'],'unknown');self.assertFalse(receipt['retry_permitted'])
        with self.assertRaises(RuntimeError):self.send(p,fake)
        self.assertEqual(len(fake.calls),1)
    def test_timeout_is_unknown_and_no_exception_text(self):
        p=self.prepared();fake=FakeTransport('raise');receipt=self.send(p,fake)
        self.assertEqual(receipt['status'],'unknown');self.assertEqual(receipt['exception_type'],'TimeoutError')
        self.assertNotIn('sensitive',json.dumps(receipt))
        with self.assertRaises(RuntimeError):self.send(p,fake)
    def test_rejection_is_recorded_no_automatic_retry(self):
        p=self.prepared();fake=FakeTransport('reject');receipt=self.send(p,fake)
        self.assertEqual(receipt['status'],'rejected');self.assertEqual(len(fake.calls),1)
        with self.assertRaises(RuntimeError):self.send(p,fake)
    def test_csv_mutation_rejected_before_transport(self):
        p=self.prepared();(Path(p['intent_dir'])/'submission.csv').write_text('changed')
        fake=FakeTransport()
        with self.assertRaises(RuntimeError):self.send(p,fake)
        self.assertEqual(fake.calls,[])
    def test_evidence_mutation_rejected(self):
        self.verified['evidence']=[{'path':str(self.csv),'sha256':m.sha(self.csv)}]
        p=self.prepared();self.csv.write_text('changed');fake=FakeTransport()
        with self.assertRaises(ValueError):self.send(p,fake)
        self.assertEqual(fake.calls,[])
    def test_api_order_drift_rejected_before_dispatch(self):
        p=self.prepared();api=json.loads(json.dumps(API));params=api['named_endpoints']['/submit_predictions']['parameters'];params[0],params[1]=params[1],params[0]
        fake=FakeTransport(info=api)
        with self.assertRaises(ValueError):self.send(p,fake)
        self.assertEqual(fake.calls,[])
    def test_actual_argument_order(self):
        namespace=m._transport_namespace();klass=namespace['GradioTransport'];transport=object.__new__(klass)
        called=[]
        class Client:
            def predict(self,*args,**kwargs):called.append((args,kwargs));return 'fake'
        transport.client=Client();transport.handle_file=lambda x:('file',x)
        args={key:key for key in m.PARAMETERS[:-1]};transport.submit_once(args,self.csv)
        self.assertEqual(list(called[0][0][:-1]),m.PARAMETERS[:-1]);self.assertEqual(called[0][0][-1],('file',str(self.csv)))
        self.assertEqual(called[0][1],{'api_name':'/submit_predictions'})
    def test_mixed_track_ledger_rejected(self):
        p=self.prepared();ledger=Path(p['ledger_dir']);(ledger/'track.json').write_text(json.dumps({'track':'regression','username':'AdeliyaLL'}))
        fake=FakeTransport()
        with self.assertRaises(ValueError):self.send(p,fake)
        self.assertEqual(fake.calls,[])
    def test_uncertain_other_file_blocks_new_attempt(self):
        p=self.prepared();fake=FakeTransport('unknown');self.send(p,fake)
        self.csv.write_text(self.csv.read_text()+'CC,B,False,True\n');p2=self.prepared()
        with self.assertRaises(RuntimeError):self.send(p2,fake)
        self.assertEqual(len(fake.calls),1)
    def test_missing_provenance_fails_clearly(self):
        with self.assertRaisesRegex(ValueError,'deployment-provenance.json'):
            m._verify_candidate(self.root,self.campaign)
    def test_gate_requires_best_reference_both_holdouts(self):
        def s(v):return {'macro_mcc':v}
        scores={c:{'soft_candidate':s(.4),'native_reference':s(.3),'native_seed42':s(.31),'hauser_native':s(.35)} for c in ('own750','briford529')}
        self.assertEqual(m.check_best_reference_gate(scores)['own750']['best_reference'],'hauser_native')
        scores['briford529']['hauser_native']=s(.41)
        with self.assertRaisesRegex(ValueError,'best reference hauser_native'):m.check_best_reference_gate(scores)
        del scores['briford529']['hauser_native']
        with self.assertRaisesRegex(ValueError,'missing required hauser_native'):m.check_best_reference_gate(scores)
    def test_gate_strict_positive_not_equal(self):
        scores={c:{n:{'macro_mcc':.3} for n in ('soft_candidate','native_reference','hauser_native')} for c in ('own750','briford529')}
        with self.assertRaises(ValueError):m.check_best_reference_gate(scores)
    def test_submission_schema_and_mapping(self):
        validator=HERE/'sources/submission-preflight/tdi_validation.py';test=self.root/'test.csv'
        frame=pd.DataFrame({'SMILES':['C']*750,'Molecule_Name':[f'M{i}' for i in range(750)]});frame.to_csv(test,index=False)
        mapping=sorted(frame[['Molecule_Name','SMILES']].values.tolist());digest=m.hashlib.sha256(json.dumps(mapping,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        frame[m.TARGETS[0]]=np.arange(750)%2==0;frame[m.TARGETS[1]]=np.arange(750)%3==0;frame.to_csv(self.csv,index=False)
        with patch.object(m,'OFFICIAL_TEST_MAPPING_SHA256',digest):
            report,pred=m._check_csv(self.csv,test,validator,m.Evidence());self.assertTrue(report['official_validator_passed'])
            frame[m.TARGETS[0]]=False;frame.to_csv(self.csv,index=False)
            with self.assertRaisesRegex(ValueError,'both predicted classes'):m._check_csv(self.csv,test,validator,m.Evidence())
            frame[m.TARGETS[0]]=np.arange(750)%2==0;frame.loc[0,'SMILES']='CC';frame.to_csv(self.csv,index=False)
            with self.assertRaisesRegex(ValueError,'IDs/SMILES'):m._check_csv(self.csv,test,validator,m.Evidence())
    def test_policy_cannot_claim_outer_selection(self):
        policy={'target_order':list(m.TARGETS),'outer_labels_used':True,'models':['a']}
        with self.assertRaisesRegex(ValueError,'outer-label'):m._apply_policy({'a':np.zeros((3,2))},policy)
    def test_score_masks_missing_labels_and_rejects_forged_macro(self):
        y=np.array([[0,1],[1,np.nan],[np.nan,0]],float);p=np.array([[0,1],[1,1],[0,0]],bool)
        actual=m._score(y,p,['a','b','c']);self.assertEqual(actual['macro_mcc'],1.)
        reported={'defined':True,'macro_mcc':.9,'evaluation_input':{'ids':['a','b','c']}}
        with self.assertRaisesRegex(ValueError,'macro MCC'):m._check_reported(actual,reported)

    def test_six_member_endpoint_policy_supported(self):
        names=[f'm{i}' for i in range(6)]
        values={n:np.full((4,2),.8 if i%2 else .2) for i,n in enumerate(names)}
        policy={'target_order':list(m.TARGETS),'outer_labels_used':False,'models':names,
            'weights':{t:{n:(1. if i==j else 0.) for i,n in enumerate(names)} for j,t in enumerate(m.TARGETS)},
            'thresholds':dict.fromkeys(m.TARGETS,.5),'comparison':'>='}
        out=m._apply_policy(values,policy)
        self.assertFalse(out[:,0].any());self.assertTrue(out[:,1].all())
    def test_hauser_composite_provenance_without_fake_seed_files(self):
        prep=self.campaign/'prepared';prep.mkdir();(prep/'metadata.json').write_text('{}')
        path=self.root/'hauser_native/own750';path.mkdir(parents=True)
        ids=['a','b'];qids=['c','d'];prob=np.array([[.2,.8],[.8,.2]])
        for filename,rows in [('oof_ids.csv',ids),('query_ids.csv',qids)]:
            pd.DataFrame({'Molecule_Name':rows}).to_csv(path/filename,index=False)
        meta={'query_labels_used':False,'prepared_manifest_sha256':m.sha(prep/'metadata.json'),
              'partition_seeds':[0,1,2],'repeats':3,'folds_per_repeat':5}
        (path/'metadata.json').write_text(json.dumps(meta))
        (path/'nativepolicy.json').write_text(json.dumps({'query_labels_used':False,'thresholds':dict.fromkeys(m.TARGETS,.5)}))
        for name,array in [('oof_proba',prob),('query_proba',prob),('query_hard',prob>=.5),('thresholds',np.array([.5,.5]))]:np.save(path/(name+'.npy'),array)
        complete={'status':'complete','cohort':'own750','files':{x.name:m.sha(x) for x in path.iterdir()}}
        (path/'complete.json').write_text(json.dumps(complete))
        out=m._hauser_predictions(self.root,prep,'own750',ids,qids,m.Evidence())
        self.assertTrue(np.array_equal(out['query_bag'],prob))
        with self.assertRaisesRegex(ValueError,'OOF IDs'):
            m._hauser_predictions(self.root,prep,'own750',list(reversed(ids)),qids,m.Evidence())

    def test_joint_gnn_fivefold_checkpoint_and_alignment_proof(self):
        prep=self.campaign/'gnnprep';prep.mkdir();(prep/'cohorts/own750').mkdir(parents=True)
        train=pd.DataFrame({'Molecule_Name':[f'A{i}' for i in range(12)],'SMILES':['C']*12})
        train.to_csv(prep/'train.csv',index=False);train.iloc[:2].to_csv(prep/'test.csv',index=False)
        dev=np.arange(10,dtype=np.int64);query=np.array([10,11],dtype=np.int64);folds=np.arange(10)%5
        np.save(prep/'cohorts/own750/folds_seed42.npy',folds)
        path=self.root/'results/own750/seed42/gnn';path.mkdir(parents=True)
        train.iloc[dev].to_csv(path/'oof_ids.csv',index=False);train.iloc[query].to_csv(path/'query_ids.csv',index=False)
        digest='a'*64
        signature={'cohort':'own750','seed':42,'foundation_sha256':'c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651',
            'implementation_sha256':digest,'recipe':{'targets':list(m.TARGETS),'max_epochs':50},'packages':{'chemprop':'2.2.1'},
            'train_csv_sha256':m.sha(prep/'train.csv'),'test_csv_sha256':m.sha(prep/'test.csv')}
        for key,arr in [('dev_indices',dev),('query_indices',query),('folds',folds)]:signature[key+'_sha256']=m.hashlib.sha256(arr.tobytes()).hexdigest()
        (path/'recipe.json').write_text(json.dumps(signature));records=[];oof=np.empty((10,2),dtype=np.float32);qs=[]
        for fold in range(5):
            folder=path/f'fold{fold}';(folder/'checkpoint').mkdir(parents=True)
            (folder/'checkpoint/best.ckpt').write_bytes(b'fixture_not_a_model')
            valid=np.flatnonzero(folds==fold);v=np.full((len(valid),2),.1*(fold+1),dtype=np.float32);q=np.full((2,2),.1*(fold+1),dtype=np.float32)
            np.savez(folder/'predictions.npz',valid_positions=valid,valid_proba=v,query_proba=q);oof[valid]=v;qs.append(q)
            record={'signature':signature,'fold':fold,'fit_seed':42+fold,'best_epoch':8,'best_val_loss':.4,
                'best_checkpoint_loaded_for_predictions':True,'identity_overlap':{'parent_key':0,'canonical_parent':0},
                'best_checkpoint':'checkpoint/best.ckpt','output_sha256':{'predictions.npz':m.sha(folder/'predictions.npz'),'checkpoint/best.ckpt':m.sha(folder/'checkpoint/best.ckpt')}}
            (folder/'complete.json').write_text(json.dumps(record));records.append(record)
        bag=np.mean(np.stack(qs),axis=0);np.save(path/'oof_proba.npy',oof);np.save(path/'query_proba.npy',bag)
        np.savez(path/'predictions.npz',oof=oof,hard_oof=oof>=.5,query_bag=bag,query_full=bag,query_full_hard=bag>=.5,dev_indices=dev,query_indices=query)
        done={'status':'complete','outer_labels_used_for_selection':False,'query_full_is_fold_bag_alias':True,
              'signature':signature,'folds':records,'output_sha256':{str(x.relative_to(path)):m.sha(x) for x in path.rglob('*') if x.is_file()},
              'prediction_sha256':m.sha(path/'predictions.npz')}
        (path/'complete.json').write_text(json.dumps(done))
        result=m._gnn_component(self.root,prep,'own750',42,dev,query,m.Evidence(),digest)
        self.assertTrue(np.array_equal(result['oof'],oof));self.assertTrue(np.array_equal(result['query_full'],bag))
        with self.assertRaisesRegex(ValueError,'implementation differs'):
            m._gnn_component(self.root,prep,'own750',42,dev,query,m.Evidence(),'b'*64)
        done['query_full_is_fold_bag_alias']=False;(path/'complete.json').write_text(json.dumps(done))
        with self.assertRaisesRegex(ValueError,'fivefold bag alias'):
            m._gnn_component(self.root,prep,'own750',42,dev,query,m.Evidence(),digest)

    def test_failed_assay_stage_cannot_prepare(self):
        summary={'qualified_on_both_holdouts':False}
        (self.root/'summary.json').write_text(json.dumps(summary))
        (self.root/'complete.json').write_text(json.dumps({'status':'complete','summary_sha256':m.sha(self.root/'summary.json')}))
        with self.assertRaisesRegex(ValueError,'E5 did not qualify on both holdouts'):
            m._verify_assay_layout(self.root,self.campaign,self.campaign/'missingprep',self.campaign/'missingbase',{},
                                  {'native_regression_sources':{}},m.Evidence(),{'assay_stack.py':{'a'*64}})
    def test_assay_thresholds_use_native_grid_first_tie(self):
        threshold,mcc=m._threshold_one(np.array([0,1,0,1]),np.array([.1,.9,.2,.8]))
        self.assertEqual(mcc,1.);self.assertTrue(np.isclose(threshold,.225))
        with self.assertRaises(ValueError):m._threshold_one(np.array([0,1]),np.array([np.nan,.2]))


if __name__=='__main__':unittest.main()
