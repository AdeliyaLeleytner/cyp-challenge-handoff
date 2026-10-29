"""Four focused CPU test groups; no training jobs and no network requests."""
from copy import deepcopy
from pathlib import Path
import unittest
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from official_scoring_functions import rae_soft_threshold_absolute_error
from .strae_objective import (interval_distance, fit_statistics, evaluation_statistics,
                              primary_metric, pack_targets, ExactSTObjective)


def sample():
    y = np.array([[0., 1., 10.], [2., np.nan, 12.], [4., 3., np.nan],
                  [6., 7., 9.], [np.nan, np.nan, 11.], [np.nan, 5., 8.]])
    lo, hi = y.copy(), y.copy()
    lo[:, :2] -= .25; hi[:, :2] += .5
    scaler = StandardScaler().fit(y)
    stats = fit_statistics(y, lo, hi, [0,1], [1.,1.,.3], scaler.mean_, scaler.scale_)
    packed = torch.tensor(pack_targets(y,lo,hi,scaler.mean_,scaler.scale_,[0,1]))
    pred = np.nan_to_num(y) + np.array([[.6,-.5,1.],[-.7,.2,-1.],
        [.1,.7,2.],[.8,-.8,1.],[.2,.3,-1.],[.3,.2,.5]])
    pred_z = torch.tensor((pred-scaler.mean_)/scaler.scale_,dtype=torch.float32)
    return y,lo,hi,scaler,stats,packed,pred,pred_z


class ExactSTTests(unittest.TestCase):
    def test_1_geometry_and_piecewise_gradients(self):
        p = torch.tensor([-.5,.25,.5,1.,1.5],requires_grad=True)
        loss = interval_distance(p,torch.zeros_like(p),torch.ones_like(p))
        torch.testing.assert_close(loss,torch.tensor([.5,0.,0.,0.,.5]))
        loss.sum().backward()
        torch.testing.assert_close(p.grad,torch.tensor([-1.,0.,0.,0.,1.]))
        y = torch.tensor([-.2,1.,5.])
        q = torch.tensor([-1.,1.,7.])
        torch.testing.assert_close(interval_distance(q,y,y),(q-y).abs())

    def test_2_official_metric_scaler_and_aux_budget(self):
        y,lo,hi,scaler,stats,packed,pred,z = sample()
        total,primary,aux = ExactSTObjective(stats)(z,packed)
        official = np.mean([rae_soft_threshold_absolute_error(y[np.isfinite(y[:,j]),j],
            pred[np.isfinite(y[:,j]),j],y_true_lower=lo[np.isfinite(y[:,j]),j],
            y_true_upper=hi[np.isfinite(y[:,j]),j]) for j in [0,1]])
        self.assertAlmostEqual(float(primary),float(official),places=6)
        self.assertAlmostEqual(primary_metric(pred,y,lo,hi,[0,1])['macro_ST_RAE'],float(official),places=12)
        mask = np.isfinite(y[:,2]); expected_aux=.15*np.mean(np.abs((pred[mask,2]-y[mask,2])/scaler.scale_[2]))
        self.assertAlmostEqual(float(aux),expected_aux,places=6)
        self.assertAlmostEqual(float(total),float(primary+aux),places=6)
        np.testing.assert_allclose(packed.numpy()[:,3:6],(lo-scaler.mean_)/scaler.scale_,rtol=1e-6,atol=1e-6,equal_nan=True)
        # Change only primary standardization. Physical-unit primary loss is invariant.
        mean2=scaler.mean_.copy();scale2=scaler.scale_.copy();mean2[:2]+=[17.,-8.];scale2[:2]*=[3.,.5]
        stats2=fit_statistics(y,lo,hi,[0,1],[1.,1.,.3],mean2,scale2)
        packed2=torch.tensor(pack_targets(y,lo,hi,mean2,scale2,[0,1]))
        z2=torch.tensor((pred-mean2)/scale2,dtype=torch.float32)
        self.assertAlmostEqual(float(ExactSTObjective(stats2)(z2,packed2)[1]),float(primary),places=6)
        # Nominal author head budgets for the four requested components.
        for nprimary,naux,budget in [(4,14,1.05),(4,4,.3),(1,5,1.5),(1,0,0.)]:
            yt=np.tile(np.arange(4.)[:,None],(1,nprimary+naux));lt=yt-.1;ut=yt+.1
            ss=fit_statistics(yt,lt,ut,list(range(nprimary)),[1.]*nprimary+[.3]*naux,np.zeros(yt.shape[1]),np.ones(yt.shape[1]))
            self.assertAlmostEqual(ss['auxiliary_total_nominal_budget'],budget)

    def test_3_partition_and_gradient_invariance_aux_only_batch(self):
        y,lo,hi,scaler,stats,packed,pred,z = sample(); objective=ExactSTObjective(stats)
        full_z=z.clone().requires_grad_();full=objective(full_z,packed)[0];full.backward()
        split_z=z.clone().requires_grad_();parts=[[0,2],[4],[1,3,5]]
        split=sum(objective(split_z[ix],packed[ix])[0]*len(ix)/len(y) for ix in parts)
        split.backward()
        torch.testing.assert_close(split,full,rtol=1e-6,atol=1e-6)
        torch.testing.assert_close(split_z.grad,full_z.grad,rtol=1e-6,atol=1e-6)
        total,primary,aux=objective(z[[4]],packed[[4]])
        self.assertEqual(float(primary),0.);self.assertGreater(float(aux),0.);self.assertEqual(float(total),float(aux))
        corrupted_missing=packed[[4]].clone();corrupted_missing[:,3:5]=float('inf');corrupted_missing[:,6:8]=-float('inf')
        self.assertEqual(float(objective(z[[4]],corrupted_missing)[0]),float(aux))
        self.assertEqual(objective(z.half(),packed.half())[0].dtype,torch.float32)
        with self.assertRaises(ValueError):objective(z,packed,torch.full((len(z),),2.))

    def test_4_frozen_statistics_guards_and_native_adapter_layout(self):
        y,lo,hi,scaler,stats,packed,pred,z = sample(); original=deepcopy(stats)
        metric=primary_metric(pred,y,lo,hi,[0,1])
        shuffled=np.concatenate([pred[:1],pred[1:4],pred[4:]],axis=0)
        self.assertEqual(metric,primary_metric(shuffled,y,lo,hi,[0,1]))
        evaluation_statistics(y*3,lo*3,hi*3,[0,1])
        self.assertEqual(stats,original)
        with self.assertRaisesRegex(ValueError,'undefined ST-RAE'):
            evaluation_statistics(np.array([[1.],[2.]]),np.array([[-100.],[-100.]]),np.array([[100.],[100.]]),[0])
        invalid=lo.copy();invalid[0,0]=np.nan
        with self.assertRaisesRegex(ValueError,'bounds'):evaluation_statistics(y,invalid,hi,[0,1])
        invalid=lo.copy();invalid[0,0]=hi[0,0]+1
        with self.assertRaisesRegex(ValueError,'bounds'):evaluation_statistics(y,invalid,hi,[0,1])
        # Forward/backward and checkpoint-state compatibility without Trainer.fit.
        from .briford_native import runtime,defaults
        from .strae_trainer import ExactSTMPNN
        from chemprop import data,nn
        core=runtime();hp=defaults();hp.update(hidden_dim=32,depth=2,ffn_hidden_dim=16,ffn_num_layers=2)
        yy=np.array([[0.,1.,10.],[2.,3.,12.],[4.,7.,9.]])
        ll=yy-.1;uu=yy+.1;sc=StandardScaler().fit(yy)
        st=fit_statistics(yy,ll,uu,[0,1],[1.,1.,.3],sc.mean_,sc.scale_)
        data_packed=pack_targets(yy,ll,uu,sc.mean_,sc.scale_,[0,1])
        dps,_=core.create_molecule_datapoints(['CC','CCC','CCO'],data_packed,None)
        batch=next(iter(data.build_dataloader(data.MoleculeDataset(dps),batch_size=3,shuffle=False,num_workers=0)))
        native=core.build_mpnn_model(hp,n_targets=3,output_transform=nn.UnscaleTransform.from_standard_scaler(sc),task_weights=[1.,1.,.3])
        native.eval(); before=native(batch.bmg,batch.V_d,batch.X_d).detach().clone();before_keys=set(native.state_dict())
        native.__class__=ExactSTMPNN;native.attach_objective(ExactSTObjective(st),(yy,ll,uu,[0,1]))
        torch.testing.assert_close(native(batch.bmg,batch.V_d,batch.X_d),before)
        self.assertEqual(set(native.state_dict()),before_keys)
        native.train();native.log=lambda *args,**kwargs:None
        loss=native.training_step(batch,0);loss.backward()
        self.assertTrue(torch.isfinite(loss));self.assertTrue(all(torch.isfinite(p.grad).all() for p in native.parameters() if p.grad is not None))
        restored=core.build_mpnn_model(hp,n_targets=3,output_transform=nn.UnscaleTransform.from_standard_scaler(sc),task_weights=[1.,1.,.3])
        restored.load_state_dict(native.state_dict(),strict=True)
        native.eval();restored.eval()
        torch.testing.assert_close(native(batch.bmg,batch.V_d,batch.X_d),restored(batch.bmg,batch.V_d,batch.X_d))
        # Exercise full-epoch metric hooks without launching a Trainer or doing an optimizer step.
        from types import SimpleNamespace
        captured={}
        native._trainer=SimpleNamespace(sanity_checking=False,current_epoch=0)
        native.log=lambda name,value,**kwargs:captured.__setitem__(name,float(value))
        native.on_validation_epoch_start();native.validation_step(batch,0);native.on_validation_epoch_end()
        expected=primary_metric(native(batch.bmg,batch.V_d,batch.X_d).detach().numpy(),yy,ll,uu,[0,1])['macro_ST_RAE']
        self.assertAlmostEqual(captured['val_primary_strae'],expected,places=6)
        native._trainer=None


if __name__=='__main__':unittest.main(verbosity=2)
