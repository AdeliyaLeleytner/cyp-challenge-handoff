"""P10: change numerator only; preserve original eighteen-observation denominator."""
import json,hashlib
import numpy as np,torch
from chemprop.nn.metrics import ChempropMetric
from .p3_core import PrimaryCheckpointMPNN,macro_strae

class ContinuationMAE(ChempropMetric):
 def __init__(self,mean,scale,primary_only=False):
  weights=torch.zeros(26);weights[:4 if primary_only else 18]=1
  super().__init__(task_weights=weights);self.register_buffer('mu',torch.tensor(mean,dtype=torch.float32));self.register_buffer('sd',torch.tensor(scale,dtype=torch.float32));self.primary_only=primary_only
 def _calc_unreduced_loss(self,preds,targets,*args):return (preds-targets).abs()
 def update(self,preds,targets,mask,weights,lt_mask=None,gt_mask=None):
  assert torch.all(weights==1)
  original_real=mask.clone();original_real[:,18:]=False;denominator=original_real.sum();assert denominator>0
  loss=(preds-targets).abs();self.total_loss+=(loss*self.task_weights*original_real).sum();self.num_samples+=denominator

class ContinuationMPNN(PrimaryCheckpointMPNN):
 def configure_optimizers(self):return torch.optim.Adam(self.parameters(),lr=1e-4,weight_decay=0)
 def training_step(self,batch,batch_idx=0):
  mask=batch[3].isfinite();self.p10_batches=getattr(self,'p10_batches',0)+1;self.p10_no_primary_batches=getattr(self,'p10_no_primary_batches',0)+int(not bool(mask[:,:4].any()))
  return super().training_step(batch,batch_idx)

def prediction_state(state):return {k:v for k,v in state.items() if not k.startswith(('predictor.criterion.','metrics.'))}
def tensor_hash(state):
 h=hashlib.sha256()
 for k in sorted(state):
  v=state[k].detach().cpu().contiguous();h.update(k.encode());h.update(str(v.dtype).encode());h.update(str(tuple(v.shape)).encode());h.update(v.numpy().tobytes())
 return h.hexdigest()

def install_parent(model,export):
 result=model.load_state_dict(export['prediction_state'],strict=False)
 assert not result.unexpected_keys and all(k.startswith(('predictor.criterion.','metrics.')) for k in result.missing_keys)
 assert tensor_hash(prediction_state(model.state_dict()))==export['prediction_tensor_sha256']
 # Objective buffers were never in the transported prediction state.
 expected=torch.zeros(26);expected[:4 if model.criterion.primary_only else 18]=1
 assert torch.equal(model.criterion.task_weights.reshape(-1).cpu(),expected)
 return export['prediction_tensor_sha256']

def evaluate_stop(model,loader,device):
 """Same scaled-validation convention as the existing direct stopping callable."""
 before=tensor_hash(prediction_state(model.state_dict()));model.on_validation_model_eval();parts=[]
 with torch.inference_mode():
  for batch in loader:
   bmg,vd,xd,target,*_=batch;bmg.to(device);vd=None if vd is None else vd.to(device);xd=None if xd is None else xd.to(device);target=target.to(device)
   z=model.predictor.train_step(model.fingerprint(bmg,vd,xd));mu=model.criterion.mu;sd=model.criterion.sd
   parts.append((target[:,:4].mul(sd[:4]).add(mu[:4]).cpu().numpy(),z[:,:4].mul(sd[:4]).add(mu[:4]).cpu().numpy(),target[:,18:22].cpu().numpy(),target[:,22:26].cpu().numpy()))
 arrays=[np.concatenate([x[j] for x in parts]) for j in range(4)];raw,per=macro_strae(*arrays);assert tensor_hash(prediction_state(model.state_dict()))==before
 model.eval();return {'raw_callable_value':raw,'monitor_float32':float(np.float32(raw)),'per_target':per,'prediction_state_unchanged':True}

def predict_raw(model,loader,device):
 model.eval();out=[]
 with torch.inference_mode():
  for batch in loader:
   bmg,vd,xd,*_=batch;bmg.to(device);vd=None if vd is None else vd.to(device);xd=None if xd is None else xd.to(device);out.append(model(bmg,vd,xd).cpu().numpy())
 return np.concatenate(out)[:,:18]
