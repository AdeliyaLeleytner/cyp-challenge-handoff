import hashlib,json,tempfile,unittest
from pathlib import Path
import numpy as np
from night.admet_full_contract import validate,ContractError,digest
from night.admet_full_math import blend_weight,primary,placement_constants
from night.admet500_blend import fit_weight
from night.admet_full_models import feature_groups

class Tests(unittest.TestCase):
    def test_unpinned_snapshot_cannot_start(self):
        with self.assertRaisesRegex(ContractError,'must be pinned'):
            validate({'stage':'evaluate','snapshot_manifest':None,'snapshot_manifest_sha256':None})
    def test_non_evaluation_stage_cannot_silently_refit(self):
        with self.assertRaisesRegex(ContractError,'Only evaluation'):
            validate({'stage':'fullfit'})
    def test_chemical_approval_is_required_before_queue_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);dummy=root/'dummy';dummy.write_text('x')
            audit=root/'audit.json';audit.write_text(json.dumps({'training_approved':False}))
            keys=['raw_features','numeric_features','feature_schema','queue','id_map','official_train','official_test','cohorts','chemical_audit','chemeleon']
            for cohort in ('own750','briford529'):
                keys += [cohort+'_native_raw',cohort+'_native_placed']+[cohort+'_'+m+'_oof' for m in ('union18','mtaux8','2d6isoform6','2d6single')]
            files={key:{'path':str(audit if key=='chemical_audit' else dummy),'sha256':digest(audit if key=='chemical_audit' else dummy)} for key in keys}
            manifest={'schema_version':1,'source_mode':'web_default','collection_complete':True,'expected_requests':32421,'expected_official_train':4905,'expected_official_test':750,'files':files}
            path=root/'manifest.json';path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ContractError,'has not approved'):
                validate({'stage':'evaluate','snapshot_manifest':str(path),'snapshot_manifest_sha256':digest(path)})
            audit.write_text(json.dumps({'training_approved':True,'unresolved_identity_errors':0}))
            manifest['files']['chemical_audit']['sha256']=digest(audit);path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ContractError,'outer-purge review'):
                validate({'stage':'evaluate','snapshot_manifest':str(path),'snapshot_manifest_sha256':digest(path)})
    def test_exact_blend_optimizer_matches_old_exhaustive_breakpoints(self):
        for seed in range(15):
            rng=np.random.default_rng(seed);y=rng.normal(5,1,(20,4));lo=y-.2;hi=y+.2;base=y+rng.normal(0,1,y.shape);extra=y+rng.normal(0,1,y.shape)
            w,info=blend_weight(y,base,extra,lo,hi);old,_=fit_weight(y,base,extra,lo,hi)
            self.assertAlmostEqual(primary(y,base+w*(extra-base),lo,hi),primary(y,base+old*(extra-base),lo,hi),places=11)
            self.assertGreaterEqual(w,0);self.assertLessEqual(w,1)
    def test_zero_delta_blend_keeps_native(self):
        y=np.arange(40,dtype=float).reshape(10,4);lo=y-.1;hi=y+.1
        w,_=blend_weight(y,y+.5,y+.5,lo,hi);self.assertEqual(w,0)
    def test_per_target_blend_supported(self):
        y=np.arange(10,dtype=float)[:,None];lo=y-.1;hi=y+.1
        w,_=blend_weight(y,y+3,y,lo,hi);self.assertAlmostEqual(primary(y,(1-w)*(y+3)+w*y,lo,hi),0,places=10)
    def test_feature_groups_are_prespecified_exhaustive_and_disjoint(self):
        root=Path(__file__).resolve().parents[1]
        columns=json.loads((root/'full_snapshot_manifest.template.json').read_text())['feature_columns']
        groups=feature_groups(columns)
        self.assertEqual(len(groups['cyp_only']),13);self.assertEqual(len(groups['non_cyp']),107)
        self.assertFalse(set(groups['cyp_only'])&set(groups['non_cyp']))
        self.assertEqual(set(groups['cyp_only'])|set(groups['non_cyp']),set(range(120)))
        cfg=json.loads((root/'full_feature_config.json').read_text());models={x['name']:x for x in cfg['portfolio']}
        self.assertEqual(models['lightgbm__admet']['grid'],models['lightgbm__cyp_only']['grid'])
        self.assertEqual(models['lightgbm__admet']['grid'],models['lightgbm__non_cyp']['grid'])
    def test_placement_constants_are_explicit_not_reestimated(self):
        values=placement_constants(Path(__file__).resolve().parents[1]/'vendor/briford_native/cyp_recalibrate.py')
        self.assertEqual(values['FLOOR'],1.0);self.assertEqual(values['STRAE_MOMENTS']['CYP2D6'],{'mean':3.57,'sd':.90})

if __name__=='__main__':unittest.main()
