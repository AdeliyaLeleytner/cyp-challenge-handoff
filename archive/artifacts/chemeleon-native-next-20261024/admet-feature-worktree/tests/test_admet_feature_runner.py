"""Mock-export and CPU-forward integration; no API requests, optimizer steps or GPU use."""
from contextlib import redirect_stdout
import csv,hashlib,io,json
from pathlib import Path
import subprocess,sys,tempfile,unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from night import briford_native as native
from night import gpu_slots
from night.admet_feature_contract import CacheNotReady,verify_ready
from night import admet_feature_runner as runner


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2)+'\n')


def fixture(root):
    assets=root/'assets';assets.mkdir();cache=root/'cache';cache.mkdir()
    ids=[f'm{i}' for i in range(10)]+['qa','qb','qc','qd']
    smiles=['C'*(i+1) for i in range(10)]+['CCO','CCN','CCCl','CCBr']
    requests=[hashlib.sha256(s.encode()).hexdigest() for s in smiles]
    mapping=pd.DataFrame({'Molecule_Name':ids,'SMILES':smiles,'source':['mock']*14,'priority':[0]*14,
            'request_smiles':smiles,'request_id':requests})
    mapping.to_csv(assets/'admetlab-id-map.csv',index=False)
    queue=pd.DataFrame({'request_id':requests,'SMILES':smiles,'priority':[0]*14});queue.to_csv(assets/'admetlab-queue.csv',index=False)
    columns=['ADMETLAB::physicochemical::MW','ADMETLAB::metabolism::CYP2D6-inh','ADMETLAB::csv_extra::Other_assay_interference']
    table=queue.copy();table['service_smiles']=smiles;table['taskid']=['mock']*14
    table[columns[0]]=np.arange(14)+20.;table[columns[1]]=np.arange(14)/14.;table[columns[2]]=np.nan
    table.to_csv(cache/'features.csv',index=False)
    schema={'endpoint_schema':[{'category':'physicochemical','name':'MW'},{'category':'metabolism','name':'CYP2D6-inh'},
            {'category':'csv_extra','name':'Other_assay_interference'}],'feature_columns':columns,'schema_note':'mock numeric endpoint cache','source_mode':'web_default','backend':'documented_web_batch','api_probe_vectors_used':False}
    save(cache/'feature-schema.json',schema)
    queue.iloc[:0].to_csv(cache/'missing-or-pending.csv',index=False)
    qsha=native.sha(assets/'admetlab-queue.csv');msha=native.sha(assets/'admetlab-id-map.csv')
    save(cache/'id-map-provenance.json',{'sha256':msha,'path':str(assets/'admetlab-id-map.csv')})
    save(cache/'status.json',{'status':'complete','queue_size':14,'successes':14,'remaining':0,'queue_sha256':qsha,'source_mode':'web_default','backend':'documented_web_batch','api_probe_vectors_used':False})
    save(cache/'complete.json',{'status':'complete','queue_sha256':qsha,'rows':14,'features_sha256':native.sha(cache/'features.csv'),'no_endpoint_filtering':True,'source_mode':'web_default','backend':'documented_web_batch','api_probe_vectors_used':False})
    controls={};target_counts={'union18':18,'mtaux8':8,'2d6isoform6':6,'2d6single':1}
    for ci,cohort in enumerate(['own750','briford529']):
        source=assets/'frozen_holdouts'/cohort;prep=source/'prepared';prep.mkdir(parents=True)
        query=mapping.iloc[10+2*ci:12+2*ci][['Molecule_Name','SMILES']];query.to_csv(source/'query.csv',index=False)
        truth=query.copy()
        for low in native.PRIMARY:
            col=low.split('_')[0].upper()+'_pIC50_direct_inhibition';truth[col]=[4.2,4.9];truth[col+'_conf_low']=[4.1,4.8];truth[col+'_conf_high']=[4.3,5.]
        truth.to_csv(source/'truth.csv',index=False)
        audit={};models={}
        for member in native.MODELS:
            targets=(native.PRIMARY+[f'mock_aux_{j}' for j in range(target_counts[member]-4)]) if member in ['union18','mtaux8'] else ['cyp2d6_pic50_direct_inhibition']+[f'mock_aux_{j}' for j in range(target_counts[member]-1)]
            frame=mapping.iloc[:10][['Molecule_Name','SMILES']].rename(columns={'Molecule_Name':'molecule_name','SMILES':'smiles'}).copy()
            for j,t in enumerate(targets):frame[t]=4.+np.arange(10)/10.+j/100.
            frame.to_csv(prep/f'{member}.csv',index=False,float_format='%.17g')
            hp=native.defaults();hp['task_weights']=[1.]*len(targets);hp['butina_cutoff']=None
            folds=[{'validation':[2*f,2*f+1],'train':[i for i in range(10) if i not in [2*f,2*f+1]]} for f in range(5)]
            spec={'model_name':native.MODELS[member],'targets':targets,'hyperparameters':hp,'rows':10,
                  'data_sha256':native.sha(prep/f'{member}.csv'),'folds':folds}
            save(prep/f'{member}.json',spec);models[member]=spec
            audit[member]={'remaining_held_id_parent_or_connectivity_overlap':0}
        save(source/'exclusion-audit.json',audit)
        save(prep/'manifest.json',{'source_sha256':native.sources(),'outer_exclusion_audit':audit,'models':models})
        controls[cohort]={v:{'n_molecules':2,'macro_ST_RAE':.5} for v in ['raw','native_published_placement']}
    save(assets/'control-scores.json',controls)
    # Only the worker test needs validator-path existence; collector is unchanged/native.
    (assets/'activity_validation.py').write_text('# mock placeholder; collector not run in CPU forward tests\n')
    cfg={'recipe_id':'scratch_mae_admetlab_all','initialization':'scratch','assets':str(assets),'feature_cache_dir':str(cache),
         'output_dir':str(root/'results'),'cohorts':['own750','briford529'],'expected_holdout_rows':{'own750':2,'briford529':2},'gpus':[0],
         'queue_sha256':qsha,'id_map_sha256':msha,'expected_endpoint_identities':['physicochemical::MW','metabolism::CYP2D6-inh'],
         'expected_csv_extra_names':['Other_assay_interference'],'source_mode':'web_default','backend':'documented_web_batch','api_probe_vectors_used':False,
         'forbidden_legacy_api_feature_columns':['ADMETLAB::csv_extra::cl-int','ADMETLAB::csv_extra::LM-mouse','ADMETLAB::csv_extra::LM-rat']}
    return cfg


class ReadyGate(unittest.TestCase):
    def test_partial_or_missing_manifests_fail_before_prepare(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cfg=fixture(root);cache=Path(cfg['feature_cache_dir'])
            (cache/'complete.json').unlink()
            with self.assertRaisesRegex(CacheNotReady,'complete file missing'):runner.prepare(cfg)
            self.assertFalse(Path(cfg['output_dir']).exists())
            save(root/'config.json',cfg)
            proc=subprocess.run([sys.executable,'-m','night.admet_feature_contract','--config',str(root/'config.json')],capture_output=True,text=True)
            self.assertEqual(proc.returncode,2);self.assertIn('admet_feature_cache_not_ready',proc.stdout)
            self.assertNotIn('Traceback',proc.stderr)

    def test_hash_coverage_schema_and_pending_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=fixture(Path(tmp));cache=Path(cfg['feature_cache_dir'])
            self.assertEqual(verify_ready(cfg)['feature_count'],3)
            initial={f:f.read_bytes() for f in cache.iterdir() if f.is_file()}
            cases=[('status.json',lambda x:{**x,'status':'running'}),
                   ('complete.json',lambda x:{**x,'features_sha256':'wrong'}),
                   ('status.json',lambda x:{**x,'successes':13}),
                   ('feature-schema.json',lambda x:{**x,'endpoint_schema':x['endpoint_schema'][:1]}),
                   ('id-map-provenance.json',lambda x:{'sha256':'wrong'}),
                   ('status.json',lambda x:{**x,'source_mode':'api_feature_true'}),
                   ('complete.json',lambda x:{**x,'api_probe_vectors_used':True}),
                   ('feature-schema.json',lambda x:{**x,'backend':'mixed'}),
                   ('feature-schema.json',lambda x:{**x,'feature_columns':x['feature_columns']+['ADMETLAB::csv_extra::cl-int']})]
            for name,mutation in cases:
                with self.subTest(name=name):
                    path=cache/name;save(path,mutation(json.loads(path.read_text())))
                    with self.assertRaises(CacheNotReady):verify_ready(cfg)
                    path.write_bytes(initial[path])
            with (cache/'missing-or-pending.csv').open('a') as stream:stream.write('pending,CCO,0\n')
            with self.assertRaisesRegex(CacheNotReady,'pending'):verify_ready(cfg)

    def test_preserves_frozen_data_and_guards_changed_recipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=fixture(Path(tmp));configs=runner.prepare(cfg)
            for sub in configs:
                root=Path(sub['prepared_dir']).parent;cohort=root.name;source=Path(cfg['assets'])/'frozen_holdouts'/cohort/'prepared'
                for member in native.MODELS:
                    old=json.loads((source/f'{member}.json').read_text());new=json.loads((root/'prepared'/f'{member}.json').read_text())
                    self.assertEqual(old['hyperparameters'],new['hyperparameters']);self.assertEqual(old['folds'],new['folds'])
                    self.assertEqual((source/f'{member}.csv').read_bytes(),(root/'prepared'/f'{member}.csv').read_bytes())
                    self.assertEqual(new['admet_features']['descriptor_count_with_missing_flags'],6)
                    cache=runner.feature_cache(new)
                    self.assertEqual(cache.provenance['service_regime']['source_mode'],'web_default')
                    bad=json.loads(json.dumps(new));bad['admet_features']['source_mode']='api_feature_true'
                    with self.assertRaisesRegex(ValueError,'web_default'):runner.feature_cache(bad)
            # Idempotent preparation is allowed only for the exact same recipe/cache.
            runner.prepare(cfg)
            cfg2={**cfg,'recipe_id':'changed'}
            with self.assertRaisesRegex(ValueError,'another feature recipe'):runner.prepare(cfg2)
            with self.assertRaises(CacheNotReady):runner.prepare({**cfg,'initialization':'chemeleon'})

    def test_worker_descriptor_inference_and_completion_path_without_training(self):
        import torch
        from chemprop import nn
        from sklearn.preprocessing import StandardScaler
        with tempfile.TemporaryDirectory() as tmp:
            cfg=fixture(Path(tmp));sub=runner.prepare(cfg)[0];folder=Path(sub['output_dir'])/'union18/fold0';folder.mkdir(parents=True)
            job={'member':'union18','fold':0,'prepared_dir':sub['prepared_dir'],'output_dir':str(folder),'official_test':sub['official_test']}
            save(folder/'job.json',job);core=native.runtime();seen={}
            def forward_only(spec,tr,va,yt,yv,**kwargs):
                self.assertTrue(spec.use_extra_features);self.assertEqual(spec.n_extra_descriptors,6)
                raw_train=kwargs['train_extra'];raw_val=kwargs['val_extra_raw']
                self.assertTrue(np.isfinite(raw_train).all());self.assertTrue(np.isfinite(raw_val).all())
                xs=StandardScaler().fit(raw_train);ys=StandardScaler().fit(yt)
                model=core.build_mpnn_model(spec.hyperparameters,n_targets=spec.n_targets,task_weights=spec.task_weights,
                    n_extra_descriptors=spec.n_extra_descriptors,x_d_transform=nn.ScaleTransform.from_standard_scaler(xs),
                    output_transform=nn.UnscaleTransform.from_standard_scaler(ys))
                model.eval();seen['model']=model
                preds=core.predict_chemprop_frame(model,spec,va,extra=raw_val)
                ckpt=Path(kwargs['checkpoint_dir']);ckpt.mkdir(parents=True)
                torch.save({'epoch':0,'state_dict':model.state_dict(),'hyper_parameters':model.hparams},ckpt/'mock-forward-only.ckpt')
                return model,preds
            core.train_chemprop_fold=forward_only
            with patch.object(native,'runtime',return_value=core),patch('torch.cuda.is_available',return_value=True):
                runner.worker(folder/'job.json')
            result=json.loads((folder/'complete.json').read_text());self.assertEqual(result['job_identity'],native.job_identity(job))
            for rel,digest in result['files'].items():self.assertEqual(native.sha(folder/rel),digest)
            meta=json.loads((folder/'metadata.json').read_text())
            self.assertEqual(meta['initialization'],'scratch');self.assertEqual(meta['actual_ffn_input_dim'],706)
            self.assertEqual(meta['feature_initialization']['mode'],'paired_fresh_head')
            self.assertEqual(meta['external_teacher_training_membership'],'unknown')
            audit=json.loads((folder/'admet-feature-audit.json').read_text())
            self.assertEqual(audit['partitions']['train']['rows'],8);self.assertEqual(audit['partitions']['validation']['rows'],2)
            self.assertEqual(len(pd.read_csv(folder/'test.csv')),2)

    def test_gpu_slot_exclusion_across_processes_without_gpu(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(gpu_slots,'ROOT',Path(tmp)):
            handle=gpu_slots.acquire(3);self.assertIsNotNone(handle)
            code='from pathlib import Path;import sys;from night import gpu_slots;gpu_slots.ROOT=Path(sys.argv[1]);h=gpu_slots.acquire(3);print("busy" if h is None else "free");h is not None and gpu_slots.release(h)'
            held=subprocess.run([sys.executable,'-c',code,tmp],capture_output=True,text=True,check=True)
            self.assertEqual(held.stdout.strip(),'busy');gpu_slots.release(handle)
            released=subprocess.run([sys.executable,'-c',code,tmp],capture_output=True,text=True,check=True)
            self.assertEqual(released.stdout.strip(),'free')

if __name__=='__main__':unittest.main()
