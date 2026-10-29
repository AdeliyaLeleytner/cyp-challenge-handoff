import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from night.admet_full_contract import validate,ContractError,digest
from night.tabpfn_admet import feature_groups,preprocess,validate_native_approval
from night.admet_full_math import blend_weight,primary
from night.tabpfn_metrics import scores
ROOT=Path(__file__).resolve().parents[1]
class Tests(unittest.TestCase):
    def test_no_snapshot_blocks_before_model_import(self):
        cfg=json.loads((ROOT/'tabpfn_admet_config.json').read_text());cfg['snapshot_manifest']=None;cfg['snapshot_manifest_sha256']=None
        with self.assertRaisesRegex(ContractError,'must be pinned'):validate(cfg)
    def test_exact120_columns_excludes_experimental(self):
        columns=json.loads((ROOT/'full_snapshot_manifest.template.json').read_text())['feature_columns']
        self.assertEqual(sum(map(len,feature_groups(columns).values())),120)
        with self.assertRaisesRegex(ContractError,'Experimental'):feature_groups(['CYP1A2_pIC50_direct_inhibition_conf_low']+columns[1:])
    def test_transform_statistics_depend_only_on_train(self):
        a=np.array([[1.,np.nan],[3.,4.],[5.,8.]]);b=np.array([[1000.,-1000.]])
        aa,bb,imp,sc=preprocess(a,b);aa2,bb2,imp2,sc2=preprocess(a,b*100)
        np.testing.assert_array_equal(aa,aa2);np.testing.assert_array_equal(imp.statistics_,[3.,6.]);np.testing.assert_array_equal(sc.mean_,[3.,6.]);np.testing.assert_array_equal(sc.mean_,sc2.mean_)
        self.assertGreater(abs(bb2[0,0]),abs(bb[0,0]))
    def test_missing_corrected_native_approval_is_blocked(self):
        with self.assertRaisesRegex(ContractError,'must be pinned'):validate_native_approval({}, {})
    def test_corrected_approval_pins_all12_vectors_and_cohorts(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'approval.json'
            keys=[c+'_'+kind for c in ('own750','briford529') for kind in ('native_raw','native_placed','union18_oof','mtaux8_oof','2d6isoform6_oof','2d6single_oof')]
            manifest={'files':{k:{'sha256':k} for k in keys}};manifest['files']['cohorts']={'sha256':'cohort'}
            approved={'experiment_id':'corrected','approved':True,'cohorts_sha256':'cohort','prediction_sha256':{k:k for k in keys}}
            p.write_text(json.dumps(approved));cfg={'corrected_native_approval':str(p),'corrected_native_approval_sha256':digest(p),'required_native_experiment':'corrected'}
            validate_native_approval(cfg,manifest)
            changed=copy.deepcopy(manifest);changed['files'][keys[0]]['sha256']='old'
            with self.assertRaisesRegex(ContractError,'not bound'):validate_native_approval(cfg,changed)
    def test_blend_fit_uses_training_arrays(self):
        y=np.arange(40,dtype=float).reshape(10,4);lo=y-.1;hi=y+.1;base=y+2;extra=y-.5
        w,_=blend_weight(y,base,extra,lo,hi)
        self.assertAlmostEqual(primary(y,base+w*(extra-base),lo,hi),0,places=9)
        for j in range(4):
            wt,_=blend_weight(y[:,j:j+1],base[:,j:j+1],extra[:,j:j+1],lo[:,j:j+1],hi[:,j:j+1]);self.assertGreaterEqual(wt,0);self.assertLessEqual(wt,1)
    def test_all5_metrics_are_retained(self):
        y=np.arange(40,dtype=float).reshape(10,4);result=scores(y,y+.5,y-.1,y+.1)
        self.assertEqual(set(result['macro']),{'ST_RAE','MAE','R2','Spearman','Kendall'});self.assertEqual(len(result['per_cyp']),4)
    def test_single_fixed_setting(self):
        cfg=json.loads((ROOT/'tabpfn_admet_config.json').read_text())
        self.assertEqual(len(cfg['portfolio']),1);self.assertEqual(cfg['portfolio'][0]['grid'],[{'n_estimators':8}]);self.assertEqual(cfg['runtime']['torch'],'2.8.0+cu128');self.assertEqual(cfg['runtime']['tabpfn'],'9.2.0')
if __name__=='__main__':unittest.main()
