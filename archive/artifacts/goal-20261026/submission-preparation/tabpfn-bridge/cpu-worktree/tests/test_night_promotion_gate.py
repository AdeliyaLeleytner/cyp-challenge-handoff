"""Synthetic artifact-only gate tests: no scientific training or GPU inference."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from night.promotion_gate import evaluate_gate, main, _digest, COHORTS, SEEDS, REFERENCE_MEMBERS
from night.reference import CANONICAL


class PromotionGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.ids = [f'mol{i}' for i in range(1136)]
        self.truth = pd.DataFrame({'Molecule_Name':self.ids})
        for j, target in enumerate(CANONICAL):
            self.truth[target] = 5+j*.2+np.sin(np.arange(1136)/11.)
            self.truth[target+'_conf_low'] = self.truth[target]-.05
            self.truth[target+'_conf_high'] = self.truth[target]+.05
        self.truth.to_csv(self.root/'truth.csv',index=False)
        self.frozen = {'own750':self.ids[:750], 'briford529':self.ids[607:]}
        cohorts = {'cohorts':{name:{'test_ids':ids,'train_ids':[i for i in self.ids if i not in set(ids)]}
                               for name,ids in self.frozen.items()}}
        self.write_json('cohorts.json',cohorts)
        self.manifest = {'schema_version':1, 'truth':self.asset('truth.csv'),'cohorts':self.asset('cohorts.json')}
        for role, name in [('candidate','candidate_v1'),('reference','briford_reference')]:
            model = {'name':name,'predictions':{}}
            if role=='reference': model['recipe_members']=list(REFERENCE_MEMBERS)
            for cohort in COHORTS:
                model['predictions'][cohort]={}
                for seed in SEEDS:
                    stem=f'{role}-{cohort}-{seed}'
                    self.write_json(stem+'-status.json',{'run_id':stem,'status':'done'})
                    pred=self.truth.set_index('Molecule_Name').loc[self.frozen[cohort],CANONICAL].reset_index()
                    pred[CANONICAL]+=.15 if role=='candidate' else .4
                    pred.to_csv(self.root/(stem+'.csv'),index=False)
                    provenance={'status':'completed','model_name':name,'cohort':cohort,'seed':int(seed),
                        'prediction_sha256':_digest(self.root/(stem+'.csv')),
                        'source_runs':[{'run_id':stem,'status':'done','evidence':self.asset(stem+'-status.json')}]}
                    if role=='reference':provenance['recipe_members']=list(REFERENCE_MEMBERS)
                    self.write_json(stem+'-provenance.json',provenance)
                    model['predictions'][cohort][seed]={**self.asset(stem+'.csv'),'run_status':'completed',
                        'provenance':self.asset(stem+'-provenance.json')}
            self.manifest[role]=model

    def tearDown(self):
        self.tmp.cleanup()

    def write_json(self,name,value):
        (self.root/name).write_text(json.dumps(value))

    def asset(self,name):
        return {'path':name,'sha256':_digest(self.root/name)}

    def run_gate(self):
        return evaluate_gate(self.manifest,base_dir=self.root,n_bootstrap=2)

    def update_prediction(self,role,cohort,seed,change):
        entry=self.manifest[role]['predictions'][cohort][seed]
        path=self.root/entry['path']; frame=pd.read_csv(path)
        frame=change(frame);frame.to_csv(path,index=False);entry['sha256']=_digest(path)
        pp=self.root/entry['provenance']['path'];prov=json.loads(pp.read_text())
        prov['prediction_sha256']=entry['sha256'];pp.write_text(json.dumps(prov))
        entry['provenance']['sha256']=_digest(pp)

    def test_pass_requires_and_reports_both_estimands_all_targets(self):
        result=self.run_gate()
        self.assertEqual(result['status'],'pass')
        self.assertEqual(len(result['score_table']),4)
        self.assertEqual(result['qualifications']['holdout_overlap']['shared_molecules'],143)
        self.assertEqual(set(result['averaged_prediction_scores']),set(COHORTS))
        self.assertEqual(result['targets'],CANONICAL)
        self.assertFalse(result['automatic_submission'])
        json.dumps(result,allow_nan=False)

    def test_permuted_prediction_order_is_aligned_by_id(self):
        self.update_prediction('candidate','own750','42',lambda x:x.iloc[::-1])
        self.assertEqual(self.run_gate()['status'],'pass')

    def test_single_seed_or_one_cohort_cannot_pass(self):
        original=copy.deepcopy(self.manifest)
        del self.manifest['candidate']['predictions']['own750']['142']
        self.assertIn('both matched seeds',str(self.run_gate()['reasons']))
        self.manifest=original;del self.manifest['reference']['predictions']['briford529']
        self.assertIn('exactly own750',str(self.run_gate()['reasons']))

    def test_specialist_missing_target_cannot_pass(self):
        self.update_prediction('candidate','own750','42',lambda x:x[['Molecule_Name',CANONICAL[2]]])
        self.assertIn('four canonical',str(self.run_gate()['reasons']))

    def test_nonfinite_duplicate_and_wrong_ids_cannot_pass(self):
        self.update_prediction('candidate','own750','42',lambda x:x.assign(**{CANONICAL[0]:np.nan}))
        self.assertIn('finite',str(self.run_gate()['reasons']))
        self.update_prediction('candidate','own750','42',lambda x:x.assign(Molecule_Name='duplicate'))
        self.assertIn('duplicate',str(self.run_gate()['reasons']))
        self.update_prediction('candidate','own750','42',lambda x:x.assign(Molecule_Name=['wrong_id']+self.frozen['own750'][1:]))
        self.assertIn('ID set differs',str(self.run_gate()['reasons']))

    def test_hash_status_and_reference_recipe_proof(self):
        entry=self.manifest['candidate']['predictions']['own750']['42']
        entry['sha256']='0'*64
        self.assertIn('SHA-256 mismatch',str(self.run_gate()['reasons']))
        entry['sha256']=_digest(self.root/entry['path'])
        pp=self.root/entry['provenance']['path'];prov=json.loads(pp.read_text())
        sp=self.root/prov['source_runs'][0]['evidence']['path']
        sp.write_text(json.dumps({'run_id':prov['source_runs'][0]['run_id'],'status':'running'}))
        prov['source_runs'][0]['evidence']['sha256']=_digest(sp)
        pp.write_text(json.dumps(prov));entry['provenance']['sha256']=_digest(pp)
        self.assertIn('status=done',str(self.run_gate()['reasons']))
        self.manifest['reference']['recipe_members']=['union18']
        # Candidate is restored to a terminal-success source first.
        sp.write_text(json.dumps({'run_id':prov['source_runs'][0]['run_id'],'status':'done'}))
        prov['source_runs'][0]['evidence']['sha256']=_digest(sp)
        pp.write_text(json.dumps(prov));entry['provenance']['sha256']=_digest(pp)
        self.assertIn('four historical',str(self.run_gate()['reasons']))

    def test_mean_paired_seed_gain_cannot_hide_worse_deployed_ensemble(self):
        for cohort in COHORTS:
            for seed in SEEDS:
                offset=.4 if seed=='42' else -.4
                def set_offset(frame, offset=offset):
                    frame[CANONICAL]=self.truth.set_index('Molecule_Name').loc[frame.Molecule_Name,CANONICAL].to_numpy()+offset
                    return frame
                self.update_prediction('reference',cohort,seed,set_offset)
        result=self.run_gate()
        self.assertFalse(result['passed'])
        self.assertTrue(all(x['delta_candidate_minus_reference']<0 for x in result['comparisons'].values()))
        self.assertTrue(all(x['delta_candidate_minus_reference']>0 for x in result['averaged_prediction_scores'].values()))
        self.assertIn('averaged-prediction delta',str(result['reasons']))

    def test_tie_or_one_cohort_loss_is_blocked(self):
        for seed in SEEDS:
            def reference_values(frame):
                frame[CANONICAL]=self.truth.set_index('Molecule_Name').loc[frame.Molecule_Name,CANONICAL].to_numpy()+.4
                return frame
            self.update_prediction('candidate','briford529',seed,reference_values)
        result=self.run_gate()
        self.assertFalse(result['passed']);self.assertIn('briford529',str(result['reasons']))

    def test_cli_pending_manifest_and_frozen_certificate(self):
        output=self.root/'blocked.json'
        code=main(['--manifest',str(self.root/'not_ready.json'),'--output',str(output),'--n-bootstrap','2'])
        self.assertEqual(code,2);self.assertFalse(json.loads(output.read_text())['passed'])
        self.assertIn('qualifications',json.loads(output.read_text()))
        self.assertIn('evidence_hashes',json.loads(output.read_text()))
        with self.assertRaises(FileExistsError):
            main(['--manifest',str(self.root/'not_ready.json'),'--output',str(output)])


if __name__=='__main__':
    unittest.main()
