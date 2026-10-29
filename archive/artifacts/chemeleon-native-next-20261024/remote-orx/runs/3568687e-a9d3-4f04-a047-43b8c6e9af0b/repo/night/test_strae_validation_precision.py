"""Focused CPU autocast and nonfinite-diagnostic regression test; no Trainer.fit."""
from pathlib import Path
from types import SimpleNamespace
import json,tempfile,unittest
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from chemprop import data,nn
from .briford_native import runtime,defaults
from .strae_objective import ExactSTObjective,fit_statistics,pack_targets
from .strae_trainer import ExactSTMPNN


class ValidationPrecisionTest(unittest.TestCase):
    def test_fp32_inside_outer_autocast_and_strict_nonfinite_report(self):
        torch.set_num_threads(2)
        core=runtime();hp=defaults();hp.update(hidden_dim=32,depth=2,ffn_hidden_dim=16)
        y=np.array([[3.,4.,-1.],[4.,5.,-2.],[6.,7.,-3.]])
        lo=y-.1;hi=y+.2;sc=StandardScaler().fit(y)
        statistics=fit_statistics(y,lo,hi,[0,1],[1.,1.,.3],sc.mean_,sc.scale_)
        packed=pack_targets(y,lo,hi,sc.mean_,sc.scale_,[0,1])
        dps,_=core.create_molecule_datapoints(['CC','CCC','CCO'],packed,None)
        batch=next(iter(data.build_dataloader(data.MoleculeDataset(dps),batch_size=3,shuffle=False,num_workers=0)))
        model=core.build_mpnn_model(hp,n_targets=3,output_transform=nn.UnscaleTransform.from_standard_scaler(sc),task_weights=[1.,1.,.3])
        model.eval();expected=model(batch.bmg,None,None).detach().numpy()
        model.__class__=ExactSTMPNN
        with tempfile.TemporaryDirectory(prefix='fp32-val-diagnostic-') as temporary:
            model.attach_objective(ExactSTObjective(statistics),(y,lo,hi,[0,1]),
                validation_target_names=['CYP_A','CYP_B','aux'],validation_row_ids=['r0','r1','r2'],
                diagnostics_dir=temporary,diagnostic_context={'training_precision':'bf16-mixed'})
            model._trainer=SimpleNamespace(sanity_checking=False,current_epoch=3,global_step=23)
            model.on_validation_model_eval()
            original=model._scaled_prediction;observed=[]
            def tracked(batch):
                prediction=original(batch)
                observed.append((torch.is_autocast_enabled('cpu'),prediction.dtype))
                return prediction
            model._scaled_prediction=tracked
            model.on_validation_epoch_start()
            with torch.autocast(device_type='cpu',dtype=torch.bfloat16):
                self.assertTrue(torch.is_autocast_enabled('cpu'))
                model.validation_step(batch,0)
            self.assertEqual(observed,[(False,torch.float32)])
            np.testing.assert_allclose(model._validation_predictions[0],expected,rtol=1e-6,atol=1e-6)
            self.assertEqual(model._validation_predictions[0].dtype,np.float32)
            predictions=model._validation_predictions[0]
            predictions[1,1]=np.nan;predictions[2,0]=np.inf
            # Simulate the consequential case: parameters finite, BN buffer poisoned.
            model.bn.running_mean[0]=float('nan')
            with self.assertRaisesRegex(FloatingPointError,'explicit FP32 validation'):
                model.on_validation_epoch_end()
            files=list(Path(temporary).glob('validation_nonfinite_*.json'));self.assertEqual(len(files),1)
            report=json.loads(files[0].read_text(),parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))
            self.assertEqual(report['prediction_shape'],[3,3]);self.assertEqual(report['nonfinite_count'],2)
            self.assertEqual(report['validation_row_indices'],[1,2]);self.assertEqual(report['molecule_names'],['r1','r2'])
            self.assertEqual(report['per_head'][0]['positive_inf_count'],1);self.assertEqual(report['per_head'][1]['nan_count'],1)
            self.assertTrue(report['all_parameters_finite']);self.assertFalse(report['all_buffers_finite'])
            self.assertIn('bn.running_mean',report['nonfinite_state_dict_keys'])
            self.assertFalse(report['state_dict_finite_flags']['bn.running_mean'])
            self.assertTrue(np.isnan(predictions[1,1]));self.assertTrue(np.isposinf(predictions[2,0]))
            model._trainer=None

if __name__=='__main__':unittest.main(verbosity=2)
