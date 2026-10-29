"""Matched interval-vs-MAE objective and train-fitted CI weighting."""
import json
import numpy as np
import torch
from chemprop.nn.metrics import ChempropMetric
from chemprop import models


def ci_weights(y, low, high, train):
    observed=np.isfinite(y)&np.isfinite(low)&np.isfinite(high)
    sigma=np.maximum((high-low)/3.92,.02)
    raw=np.where(observed,1/sigma**2,np.nan)
    counts=observed.sum(1); raw=np.nansum(raw,axis=1)/np.maximum(counts,1);raw[counts==0]=np.nan
    med=float(np.nanmedian(raw[train])); filled=np.where(np.isfinite(raw),raw,med)
    mean=float(filled[train].mean()); cap=float(np.quantile(filled[train]/mean,.99))
    clipped=np.minimum(filled/mean,cap); norm=float(clipped[train].mean())
    return clipped/norm,{'median':med,'initial_mean':mean,'normalized_cap99':cap,'post_cap_train_mean':norm,'proxy':'mean inverse squared CIwidth/3.92 with sigma floor0.02; not demonstrated experimental variance'}


class MatchedLoss(ChempropMetric):
    def __init__(self, mean, scale, interval=False, n_real=18):
        super().__init__(task_weights=torch.cat([torch.ones(n_real),torch.zeros(8)]))
        self.register_buffer('mu',torch.tensor(mean,dtype=torch.float32));self.register_buffer('sd',torch.tensor(scale,dtype=torch.float32));self.interval=interval;self.n_real=n_real
    def _calc_unreduced_loss(self,preds,targets,mask,*args):
        values=(preds-targets).abs(); columns=list(values.unbind(1))
        if self.interval:
            for j in range(4):
                raw=preds[:,j]*self.sd[j]+self.mu[j]
                lo=targets[:,self.n_real+j];hi=targets[:,self.n_real+4+j]
                valid=mask[:,self.n_real+j]&mask[:,self.n_real+4+j]
                columns[j]=torch.where(valid,(torch.relu(lo-raw)+torch.relu(raw-hi))/self.sd[j],columns[j])
        return torch.stack(columns,1)
    def update(self,preds,targets,mask,weights,lt_mask=None,gt_mask=None):
        loss=self._calc_unreduced_loss(preds,targets,mask); realmask=mask.clone();realmask[:,self.n_real:]=False
        self.total_loss+=(loss*weights.view(-1,1)*self.task_weights*realmask).sum()
        self.num_samples+=realmask.sum()


def macro_strae(y,p,lo,hi):
    scores=[]
    for j in range(4):
        m=np.isfinite(y[:,j]); yy=y[m,j]; pp=p[m,j]
        l=np.where(np.isfinite(lo[m,j]),lo[m,j],yy);h=np.where(np.isfinite(hi[m,j]),hi[m,j],yy)
        den=np.maximum(l-yy.mean(),0)+np.maximum(yy.mean()-h,0)
        assert len(yy)>0 and den.sum()>0
        scores.append(float((np.maximum(l-pp,0)+np.maximum(pp-h,0)).sum()/den.sum()))
    return float(np.mean(scores)),scores


class PrimaryCheckpointMPNN(models.MPNN):
    """Checkpoint selection always raw primary ST-RAE, never weighted train loss."""
    def on_validation_epoch_start(self):self._primary_validation=[]
    def validation_step(self,batch,batch_idx=0):
        bmg,Vd,Xd,targets,weights,*_=batch
        with torch.no_grad():
            z=self.predictor.train_step(self.fingerprint(bmg,Vd,Xd))
            mu=self.criterion.mu;sd=self.criterion.sd
            self._primary_validation.append((targets[:,:4].mul(sd[:4]).add(mu[:4]).cpu().numpy(),z[:,:4].mul(sd[:4]).add(mu[:4]).cpu().numpy(),targets[:,18:22].cpu().numpy(),targets[:,22:26].cpu().numpy()))
    def on_validation_epoch_end(self):
        arrays=[np.concatenate([r[j] for r in self._primary_validation]) for j in range(4)]
        value,per=macro_strae(*arrays);self.log('primary_strae',value,prog_bar=False,batch_size=len(arrays[0]));print(json.dumps({'event':'checkpoint_metric','epoch':int(self.current_epoch),'primary_strae':value,'per_target':per}),flush=True);self._primary_validation=[]


def exact_eval_loader(dataset,batch_size=128,num_workers=2):
    from torch.utils.data import DataLoader
    from chemprop.data.collate import collate_batch
    return DataLoader(dataset,batch_size=batch_size,shuffle=False,num_workers=num_workers,collate_fn=collate_batch,drop_last=False)
