"""Lightweight invariance/contract checks; no real scientific model is trained."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd

from night.features import build_features, pairwise_tanimoto
from night.tabular import run_trial, predict_saved_trial, PRIMARY, _tfm


class FakeRegressor:
    def __init__(self, **kwargs): self.params=kwargs
    def fit(self,X,y):
        assert np.isfinite(X).all() and np.isfinite(y).all()
        self.mean=float(np.mean(y));self.n=len(y);return self
    def predict(self,X):return self.mean+np.asarray(X)[:,0]*0.001


class FakeKernelRidge:
    def __init__(self,**kwargs):self.params=kwargs
    def fit(self,K,y):self.dual_coef_=np.arange(1,len(y)+1,dtype=float)/len(y);return self
    def predict(self,K):return K@self.dual_coef_


class FakeCatBoost(FakeRegressor):
    def save_model(self,path):Path(path).write_text(json.dumps({'mean':self.mean,'n':self.n}))
    def load_model(self,path):self.__dict__.update(json.loads(Path(path).read_text()))


class FeaturesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.mol=pd.DataFrame({'Molecule_Name':['a','b','c'],'SMILES':['CCO','CCCCCC','c1ccccc1O']})
    def tearDown(self):self.tmp.cleanup()
    def test_raw_families_alignment_and_counts(self):
        for family in ['morgan_bits','morgan_counts','feature_morgan_bits','feature_morgan_counts','atom_pair','atom_pair_counts','torsion','torsion_counts','rdkit_path','rdkit2d']:
            X,names,m=build_features(self.mol,family,self.root,{'n_bits':128,'radius':3})
            perm=[2,0,1];Y,columns,_=build_features(self.mol.iloc[perm],family,self.root,{'n_bits':128,'radius':3})
            np.testing.assert_equal(Y,X[perm]);self.assertEqual(names,columns);self.assertEqual(m['ids'],['a','b','c'])
            self.assertEqual(X.shape[0],3)
        counts,_,_=build_features(self.mol,'morgan_counts',self.root,{'n_bits':128})
        self.assertGreater(counts.max(),1)
    def test_stereochemistry_is_explicit(self):
        df=pd.DataFrame({'Molecule_Name':['l','d'],'SMILES':['C[C@H](N)C(=O)O','C[C@@H](N)C(=O)O']})
        a,_,_=build_features(df,'morgan_bits',self.root,{'include_chirality':False})
        b,_,_=build_features(df,'morgan_bits',self.root,{'include_chirality':True})
        np.testing.assert_equal(a[0],a[1]);self.assertFalse(np.array_equal(b[0],b[1]))
    def test_invalid_is_not_dropped(self):
        df=pd.DataFrame({'Molecule_Name':['ok','bad'],'SMILES':['CCO','not_a_smiles']})
        with self.assertRaisesRegex(ValueError,'Invalid SMILES'):build_features(df,'morgan_bits',self.root,{})
        X,_,m=build_features(df,'morgan_bits',self.root,{'invalid_policy':'nan'})
        self.assertEqual(len(X),2);self.assertTrue(np.isnan(X[1]).all());self.assertEqual(m['invalid_ids'],['bad'])
    def test_cache_is_label_free_and_order_sensitive(self):
        X,_,a=build_features(self.mol,'morgan_bits',self.root,{'cache':True})
        changed=self.mol.copy();changed[PRIMARY[0]]=[100,200,300]
        Y,_,b=build_features(changed,'morgan_bits',self.root,{'cache':True})
        self.assertFalse(a['cache_hit']);self.assertTrue(b['cache_hit']);np.testing.assert_equal(X,Y)
        _,_,c=build_features(changed.iloc[::-1],'morgan_bits',self.root,{'cache':True})
        self.assertNotEqual(a['cache_key'],c['cache_key'])
    def test_precomputed_id_gather_hash_and_missing(self):
        p=self.root/'x.npy';i=self.root/'ids.csv';np.save(p,np.array([[10,20],[30,40],[50,60]],np.float32));pd.DataFrame({'Molecule_Name':['b','c','a']}).to_csv(i,index=False)
        rec={'matrix_path':'x.npy','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'ids_path':'ids.csv','ids_sha256':hashlib.sha256(i.read_bytes()).hexdigest()}
        (self.root/'feature_manifest.json').write_text(json.dumps({'features':{'test':rec}}))
        X,_,_=build_features(self.mol,'precomputed',self.root,{'asset_key':'test'})
        np.testing.assert_equal(X,[[50,60],[10,20],[30,40]])
        with self.assertRaisesRegex(ValueError,'absent'):build_features(pd.DataFrame({'Molecule_Name':['missing']}),'precomputed',self.root,{'asset_key':'test'})
        with p.open('ab') as f:f.write(b'corrupt')
        with self.assertRaisesRegex(ValueError,'SHA-256'):build_features(self.mol,'precomputed',self.root,{'asset_key':'test'})
    def test_tanimoto_distinguishes_counts_and_handles_zero(self):
        X=np.array([[2,0],[0,0],[1,1]],float);Y=np.array([[1,0],[0,0],[1,1]],float)
        dot=pairwise_tanimoto(X,Y,'tdp');mm=pairwise_tanimoto(X,Y,'tmm')
        self.assertAlmostEqual(dot[0,0],2/3);self.assertAlmostEqual(mm[0,0],.5)
        self.assertEqual(dot[1,1],1);self.assertEqual(dot[1,0],0)
        np.testing.assert_allclose(pairwise_tanimoto(Y,Y,'tdp'),pairwise_tanimoto(Y,Y,'tmm'))
        with self.assertRaises(ValueError):pairwise_tanimoto(-X,Y)


class TrialTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.train=pd.DataFrame({'Molecule_Name':['a','b','c','d'],'SMILES':['C','CC','CCC','CCCC'],PRIMARY[0]:[1,np.nan,3,5],PRIMARY[1]:[np.nan,2,4,6]})
        self.query=pd.DataFrame({'Molecule_Name':['e','f'],'SMILES':['CCO','CCN'],PRIMARY[0]:[9999,-9999]})
        matrix=np.array([[0,1,np.nan],[2,2,np.nan],[4,np.nan,np.nan],[6,4,np.nan],[1000,1000,9],[-1000,-1000,8]],np.float32)
        np.save(self.root/'matrix.npy',matrix);pd.DataFrame({'Molecule_Name':['a','b','c','d','e','f']}).to_csv(self.root/'ids.csv',index=False)
        self.record={'matrix_path':'matrix.npy','sha256':hashlib.sha256((self.root/'matrix.npy').read_bytes()).hexdigest(),'ids_path':'ids.csv','ids_sha256':hashlib.sha256((self.root/'ids.csv').read_bytes()).hexdigest(),'nonfinite_policy':'nan'}
        self.cfg={'model':'extratrees','features':[{'family':'precomputed','asset':self.record}],'targets':PRIMARY[:2],'preprocessing':{'scale':True},'model_params':{'n_estimators':3},'seed':42}
    def tearDown(self):self.tmp.cleanup()
    def test_train_only_transform_masks_query_labels_and_restore(self):
        out=self.root/'trial'
        with patch('night.tabular.ExtraTreesRegressor',FakeRegressor):
            p=run_trial(self.cfg,self.train,self.query,self.root,out,validation_df=self.query)
        pipe=joblib.load(out/'transform.joblib')
        np.testing.assert_allclose(pipe.named_steps['imputer'].statistics_,[3,2,0])
        self.assertEqual(list(p.columns),['Molecule_Name']+PRIMARY[:2])
        meta=json.loads((out/'trial.json').read_text());self.assertFalse(meta['validation_used'])
        self.assertEqual(meta['targets_metadata'][PRIMARY[0]]['n_labels'],3)
        self.assertEqual(meta['targets_metadata'][PRIMARY[1]]['n_labels'],3)
        restored=predict_saved_trial(out,self.query.drop(columns=[PRIMARY[0]]),self.root)
        np.testing.assert_allclose(p.iloc[:,1:],restored.iloc[:,1:])
        altered=self.query.copy();altered[PRIMARY[0]]=[-1e12,1e12]
        with patch('night.tabular.ExtraTreesRegressor',FakeRegressor):p2=run_trial(self.cfg,self.train,altered,self.root,self.root/'trial2')
        np.testing.assert_allclose(p.iloc[:,1:],p2.iloc[:,1:])
    def test_pca_train_only_and_requested_targets(self):
        cfg={**self.cfg,'targets':['CYP1A2'],'preprocessing':{'pca_components':2,'scale':True}}
        with patch('night.tabular.ExtraTreesRegressor',FakeRegressor):p=run_trial(cfg,self.train,self.query,self.root,self.root/'pca')
        meta=json.loads((self.root/'pca/trial.json').read_text());self.assertEqual(meta['preprocessing']['pca_effective'],2)
        self.assertEqual(list(p.columns),['Molecule_Name',PRIMARY[0]])
    def test_overlap_and_all_missing_target_rejected(self):
        with self.assertRaisesRegex(ValueError,'overlap'):run_trial(self.cfg,self.train,self.train.iloc[:1],self.root,self.root/'bad')
        train=self.train.copy();train[PRIMARY[0]]=np.nan
        with self.assertRaisesRegex(ValueError,'no observed'):run_trial(self.cfg,train,self.query,self.root,self.root/'bad2')
    def test_kernel_dual_restore_and_no_scaled_tanimoto(self):
        cfg={'model':'krr','features':[{'family':'morgan_counts','n_bits':64}],'targets':[PRIMARY[0]],'model_params':{'kernel':'tanimoto','alpha':.1,'center_target':True}}
        with patch('night.tabular.KernelRidge',FakeKernelRidge):p=run_trial(cfg,self.train,self.query,self.root,self.root/'krr')
        restored=predict_saved_trial(self.root/'krr',self.query,self.root);np.testing.assert_allclose(p.iloc[:,1:],restored.iloc[:,1:])
        cfg['preprocessing']={'scale':True}
        with self.assertRaisesRegex(ValueError,'cannot use'):run_trial(cfg,self.train,self.query,self.root,self.root/'badkrr')
    def test_tfm_pinning_and_context_restore_without_download(self):
        asset=self.root/'fake.ckpt';asset.write_bytes(b'synthetic-fake-model')
        cfg={**self.cfg,'model':'tabicl','model_asset':{'path':'fake.ckpt','sha256':hashlib.sha256(asset.read_bytes()).hexdigest()},'preprocessing':{'pca_components':2},'model_params':{'n_estimators':8}}
        version=importlib.metadata.version
        def versions(p):return 'synthetic-test' if p=='tabicl' else version(p)
        fake=types.SimpleNamespace(TabICLRegressor=FakeRegressor)
        with patch.dict(sys.modules,{'tabicl':fake}),patch('night.tabular.importlib.metadata.version',side_effect=versions),patch('night.tabular._release_tfm'):
            p=run_trial(cfg,self.train,self.query,self.root,self.root/'tfm')
            restored=predict_saved_trial(self.root/'tfm',self.query,self.root)
            m,_=_tfm(cfg,'tabicl',self.root);self.assertFalse(m.params['allow_auto_download'])
        np.testing.assert_allclose(p.iloc[:,1:],restored.iloc[:,1:])
        bad={**cfg,'model_asset':{'path':'fake.ckpt','sha256':'0'*64}}
        with self.assertRaisesRegex(ValueError,'SHA-256'):_tfm(bad,'tabicl',self.root)
    def test_catboost_storage_contract_without_optional_install(self):
        cfg={**self.cfg,'model':'catboost','model_params':{'loss_function':'MAE','iterations':2}}
        with patch.dict(sys.modules,{'catboost':types.SimpleNamespace(CatBoostRegressor=FakeCatBoost)}):
            p=run_trial(cfg,self.train,self.query,self.root,self.root/'cat')
            restored=predict_saved_trial(self.root/'cat',self.query,self.root)
        np.testing.assert_allclose(p.iloc[:,1:],restored.iloc[:,1:])


if __name__=='__main__':unittest.main()
