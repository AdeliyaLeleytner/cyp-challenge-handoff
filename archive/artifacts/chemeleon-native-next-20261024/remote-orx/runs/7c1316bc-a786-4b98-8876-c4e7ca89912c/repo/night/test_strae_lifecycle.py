"""One synthetic CPU Lightning lifecycle test, never a CYP benchmark experiment."""
import json
import os
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from chemprop import nn
from official_scoring_functions import rae_soft_threshold_absolute_error
from .briford_native import runtime, defaults
from . import strae_trainer


class SyntheticLifecycleTest(unittest.TestCase):
    def test_cpu_fit_checkpoint_reload_and_physical_inference(self):
        self._exercise_lifecycle('scratch')
        foundation = os.environ.get('CYP_TEST_FOUNDATION_CHECKPOINT')
        if foundation:
            path = Path(foundation)
            from .chemeleon_native import CHECKPOINT_SHA
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), CHECKPOINT_SHA)
            with self.subTest(initialization='chemeleon'):
                self._exercise_lifecycle('chemeleon', path)

    def _exercise_lifecycle(self, initialization, foundation_path=None):
        torch.set_num_threads(2)
        core = runtime()
        isoforms = ['cyp3a4', 'cyp2c9', 'cyp2d6', 'cyp1a2']
        primary = [f'{iso}_pic50_direct_inhibition' for iso in isoforms]
        targets = primary + [f'{iso}_log2fc' for iso in isoforms]
        train_smiles = ['C','CC','CCC','CCCC','CO','CCO','CCCO','CN','CCN','CCCN','CC(=O)O','CC(=O)N']
        val_smiles = ['CCOC','CNC','COC','CCCl','CCBr','CCF','c1ccccc1','c1ccncc1']
        query_smiles = ['c1ccoc1','C1CCCCC1','CC(C)O','CC(C)N']

        def frame(smiles, prefix, offset):
            n = len(smiles)
            result = pd.DataFrame({'molecule_name':[f'{prefix}{i}' for i in range(n)], 'smiles':smiles})
            x = np.linspace(3.0+offset, 6.0+offset, n)
            for j,t in enumerate(primary):
                result[t] = x + .15*j
                result[t+'_ci_lower'] = result[t] - .10
                result[t+'_ci_upper'] = result[t] + .15
            for j,t in enumerate(targets[4:]):result[t] = -.3*x + .1*j
            # Missing primary labels, including one auxiliary-only row, are intentional.
            for t in primary:
                result.loc[0,[t,t+'_ci_lower',t+'_ci_upper']] = np.nan
            result.loc[2,[primary[2],primary[2]+'_ci_lower',primary[2]+'_ci_upper']] = np.nan
            return result

        train = frame(train_smiles,'synthetic_train_',0.)
        validation = frame(val_smiles,'synthetic_val_',.2)
        query = pd.DataFrame({'molecule_name':[f'synthetic_query_{i}' for i in range(4)],'smiles':query_smiles})
        hp = defaults()
        hp.update(max_epochs=3, warmup_epochs=1, batch_size=4, criterion_mode='exact_strae_v1')
        if initialization == 'chemeleon':
            hp.update(from_foundation=str(foundation_path), hidden_dim=2048, depth=6)
        self.assertEqual((hp['hidden_dim'],hp['depth'],hp['ffn_hidden_dim'],hp['ffn_num_layers']),
                         (2048,6,300,2) if initialization == 'chemeleon' else (700,5,300,2))
        weights = [1.]*4 + [.3]*4
        spec = core.FoldSpec(hyperparameters=hp,task='regression',model_type='uq_regressor',
            smiles_column='smiles',n_targets=8,target_columns=targets,task_weights=np.array(weights,np.float32),
            num_workers=0,concurrent=True,enable_progress_bar=False,verbose=False)
        train_y = train[targets].to_numpy(np.float32); val_y = validation[targets].to_numpy(np.float32)
        real_trainer = strae_trainer.pl.Trainer
        trainers = []; hook_states = []
        inherited_validation_hook = strae_trainer.ExactSTMPNN.on_validation_model_eval

        def tracked_validation_hook(model):
            inherited_validation_hook(model)
            hook_states.append({'model_training':model.training,
                                'output_transform_training':model.predictor.output_transform.training})

        def cpu_fixture_trainer(**kwargs):
            # These overrides exist only in this test fixture, never in scientific config.
            self.assertEqual(kwargs['accelerator'],'auto')
            self.assertEqual(kwargs['precision'],'16-mixed')
            kwargs.update(accelerator='cpu',precision='32-true')
            trainer = real_trainer(**kwargs)
            trainers.append(trainer)
            return trainer

        with tempfile.TemporaryDirectory(prefix='synthetic-strae-lifecycle-') as temp:
            directory = Path(temp)
            with patch.object(strae_trainer.pl,'Trainer',side_effect=cpu_fixture_trainer), \
                 patch.object(strae_trainer.ExactSTMPNN,'on_validation_model_eval',new=tracked_validation_hook):
                model,val_predictions = strae_trainer.train_exact_strae_fold(core,spec,train,validation,
                    train_y,val_y,fold_idx=0,checkpoint_dir=str(directory/'checkpoints'))
            self.assertEqual(len(trainers),1)
            trainer = trainers[0]
            self.assertEqual(trainer.current_epoch,3)
            self.assertEqual(model.device.type,'cpu')
            self.assertIn('val_primary_strae',trainer.callback_metrics)
            self.assertTrue(np.isfinite(float(trainer.callback_metrics['val_primary_strae'])))
            self.assertGreaterEqual(len(hook_states),4)  # sanity checking plus three epochs
            self.assertTrue(all(not h['model_training'] and h['output_transform_training'] for h in hook_states))
            checkpoint = trainer.checkpoint_callback
            self.assertEqual(checkpoint.monitor,'val_primary_strae')
            self.assertTrue(checkpoint.best_model_path)
            saved = torch.load(checkpoint.best_model_path,map_location='cpu',weights_only=False)
            self.assertIn(int(saved['epoch']),range(3))
            self.assertEqual(len(list((directory/'checkpoints').glob('*.ckpt'))),1)
            history = json.loads((directory/'loss_history.json').read_text())
            self.assertEqual(len(history),3)
            self.assertAlmostEqual(float(checkpoint.best_model_score),min(r['val_primary_strae'] for r in history),places=6)
            self.assertEqual(val_predictions.shape,(len(validation),8))
            self.assertTrue(np.isfinite(val_predictions).all())
            observed_scores=[]
            for j,t in enumerate(primary):
                valid=validation[t].notna().to_numpy()
                observed_scores.append(rae_soft_threshold_absolute_error(
                    validation.loc[valid,t].to_numpy(),val_predictions[valid,j],
                    y_true_lower=validation.loc[valid,t+'_ci_lower'].to_numpy(),
                    y_true_upper=validation.loc[valid,t+'_ci_upper'].to_numpy()))
            self.assertAlmostEqual(float(checkpoint.best_model_score),float(np.mean(observed_scores)),places=6)
            # Load the saved model weights into a fresh, ordinary native MPNN, strict=True.
            scaler = StandardScaler().fit(train_y)
            restored = core.build_mpnn_model(hp,n_targets=8,task_weights=weights,
                output_transform=nn.UnscaleTransform.from_standard_scaler(scaler))
            restored.load_state_dict(saved['state_dict'],strict=True)
            restored.eval()
            original_query = core.predict_chemprop_frame(model,spec,query)
            restored_query = core.predict_chemprop_frame(restored,spec,query)
            self.assertEqual(original_query.shape,(4,8))
            self.assertTrue(np.isfinite(original_query).all())
            np.testing.assert_allclose(restored_query,original_query,rtol=1e-6,atol=1e-6)
            # Explicitly verify output units: raw FFN z transformed once equals inference.
            from chemprop import data
            dps,_=core.create_molecule_datapoints(query.smiles.tolist(),None,None)
            batch=next(iter(data.build_dataloader(data.MoleculeDataset(dps),batch_size=4,shuffle=False,num_workers=0)))
            with torch.no_grad():
                z=restored.predictor.ffn(restored.fingerprint(batch.bmg,batch.V_d,batch.X_d))
                physical=z*torch.tensor(scaler.scale_,dtype=torch.float32)+torch.tensor(scaler.mean_,dtype=torch.float32)
            np.testing.assert_allclose(restored_query,physical.numpy(),rtol=1e-6,atol=1e-6)
            result={'event':'synthetic_cpu_lifecycle_pass','data':'synthetic_only_no_CYP_benchmark',
                'initialization':initialization,'encoder_width':model.message_passing.output_dim,
                'aggregation':type(model.agg).__name__,'ffn':'native300x2','epochs':3,'batch_size':4,
                'trainer_accelerator':'cpu','trainer_precision':'32-true_test_fixture_only',
                'validation_monitor':'val_primary_strae','checkpoint_selected':True,
                'checkpoint_best_epoch':int(saved['epoch']),
                'inherited_validation_hook_called':len(hook_states),
                'inherited_output_transform_training_state_verified':True,
                'best_checkpoint_matches_official_validation_score':True,
                'strict_native_state_reload':True,'finite_physical_query_shape':list(restored_query.shape),
                'gpu_training':False,'scientific_result':False}
            print(json.dumps(result),flush=True)

if __name__=='__main__':unittest.main(verbosity=2)
