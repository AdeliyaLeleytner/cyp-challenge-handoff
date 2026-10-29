"""Frozen empirical condition routing with fixed task-mass normalization."""
import numpy as np,torch,json
from chemprop.nn.metrics import ChempropMetric
from .p3_core import PrimaryCheckpointMPNN,macro_strae

class FrozenMaps(torch.nn.Module):
 def __init__(self,maps):
  super().__init__();self.entries=[]
  for j,entry in enumerate(maps):
   m=entry['map'];self.entries.append(m)
   for key in ['knots','coefficients']:self.register_buffer(f'{key}_{j}',torch.tensor(m[key],dtype=torch.float32))
   self.register_buffer(f'stats_{j}',torch.tensor([m['x_mean'],m['x_scale'],m['y_mean'],m['y_scale'],m['fit_min'],m['fit_max']],dtype=torch.float32))
 def forward(self,raw,j):
  xm,xs,ym,ys,_,_=getattr(self,f'stats_{j}');z=(raw-xm)/xs;knots=getattr(self,f'knots_{j}');coef=getattr(self,f'coefficients_{j}')
  X=torch.stack([torch.ones_like(z),z]+[torch.relu(z-k) for k in knots],dim=-1)
  return ym+ys*(X@coef)

class ConditionLoss(ChempropMetric):
 def __init__(self,mean,scale,maps,arm,screen_indices):
  super().__init__(task_weights=torch.cat([torch.ones(22),torch.zeros(8)]));assert arm in ['A','B','C','D']
  self.register_buffer('mu',torch.tensor(mean,dtype=torch.float32));self.register_buffer('sd',torch.tensor(scale,dtype=torch.float32));self.maps=FrozenMaps(maps);self.arm=arm;self.screen_indices=list(screen_indices)
 def effective_standardized(self,preds):
  columns=list(preds.unbind(1))
  if self.arm in ['C','D']:
   for j,screen in enumerate(self.screen_indices):
    potency=18+j if self.arm=='C' else j
    raw=preds[:,potency]*self.sd[potency]+self.mu[potency]
    columns[screen]=(self.maps(raw,j)-self.mu[screen])/self.sd[screen]
  return torch.stack(columns,1)
 def _calc_unreduced_loss(self,preds,targets,*args):return (self.effective_standardized(preds)-targets).abs()
 def update(self,preds,targets,mask,weights,lt_mask=None,gt_mask=None):
  assert torch.all(weights==1), 'P8c row weighting must remain uniform'
  active_mask=mask.clone();active_mask[:,22:]=False
  if self.arm=='A':active_mask[:,18:22]=False
  loss=self._calc_unreduced_loss(preds,targets);self.total_loss+=(loss*self.task_weights*active_mask).sum();self.num_samples+=preds.shape[0]*22
 def raw_effective(self,raw):
  columns=list(raw.unbind(1))
  if self.arm in ['C','D']:
   for j,screen in enumerate(self.screen_indices):columns[screen]=self.maps(raw[:,18+j if self.arm=='C' else j],j)
  return torch.stack(columns,1)

class ConditionMPNN(PrimaryCheckpointMPNN):
 def validation_step(self,batch,batch_idx=0):
  bmg,Vd,Xd,targets,weights,*_=batch
  with torch.no_grad():
   z=self.predictor.train_step(self.fingerprint(bmg,Vd,Xd));mu=self.criterion.mu;sd=self.criterion.sd
   self._primary_validation.append((targets[:,:4].mul(sd[:4]).add(mu[:4]).cpu().numpy(),z[:,:4].mul(sd[:4]).add(mu[:4]).cpu().numpy(),targets[:,22:26].cpu().numpy(),targets[:,26:30].cpu().numpy()))

 def on_validation_epoch_end(self):
  arrays=[np.concatenate([r[j] for r in self._primary_validation]) for j in range(4)];value,per=macro_strae(*arrays);self.log('primary_strae',value,prog_bar=False,batch_size=len(arrays[0]));print(json.dumps({'event':'checkpoint_metric','epoch':int(self.current_epoch),'primary_strae':value,'per_target':per}),flush=True);self._primary_validation=[]
