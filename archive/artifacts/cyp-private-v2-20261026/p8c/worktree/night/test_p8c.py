import json,hashlib
from pathlib import Path
import numpy as np,torch
from chemprop import data,featurizers,nn
from .p8c_core import ConditionLoss,ConditionMPNN
from .p3_core import exact_eval_loader

SC=[7,5,6,4]
def maps():return [{'map':{'x_mean':4+j*.1,'x_scale':2.,'y_mean':-1.,'y_scale':3.,'fit_min':0.,'fit_max':10.,'knots':[-1.,0.,1.],'coefficients':[.2,1.,.1,-.2,.3]}} for j in range(4)]
def stats():
 mu=np.linspace(-2,6,30);sd=np.linspace(.5,2,30);mu[22:]=0;sd[22:]=1;return mu,sd

def test_routes_and_mass():
 mu,sd=stats();y=torch.ones((2,30));mask=torch.ones_like(y,dtype=torch.bool);w=torch.ones(2,1);grads={}
 for arm in ['A','B','C','D']:
  p=torch.full((2,30),.3,requires_grad=True);c=ConditionLoss(mu,sd,maps(),arm,SC);v=c(p,y,mask,w);v.backward();grads[arm]=p.grad.detach().clone();assert torch.all(p.grad[:,22:]==0)
  expected=(c.effective_standardized(p)-y).abs()[:,:22]
  if arm=='A':expected=expected.clone();expected[:,18:22]=0
  assert torch.allclose(v,expected.sum()/44)
 assert torch.equal(grads['A'][:,:4],grads['B'][:,:4]);assert torch.all(grads['A'][:,18:22]==0)
 # Missing unrelated endpoints cannot amplify remaining direct gradients.
 p=torch.full((2,30),.3,requires_grad=True);m=mask.clone();m[:,4:22]=False;c=ConditionLoss(mu,sd,maps(),'B',SC);c(p,y,m,w).backward();assert torch.equal(p.grad[:,:4],grads['B'][:,:4])
 for arm in ['C','D']:
  p=torch.full((2,30),.3,requires_grad=True);m=torch.zeros_like(mask);m[:,SC[0]]=True;c=ConditionLoss(mu,sd,maps(),arm,SC);c(p,y,m,w).backward();ix=18 if arm=='C' else 0;assert p.grad[:,ix].abs().sum()>0;other=p.grad.clone();other[:,ix]=0;assert torch.all(other==0)
 # Same physical potency must have the same g output despite differing head scales.
 raw=torch.tensor([5.2,5.5]);p=torch.zeros((2,30));p[:,0]=(raw-float(mu[0]))/float(sd[0]);p[:,18]=(raw-float(mu[18]))/float(sd[18]);c=ConditionLoss(mu,sd,maps(),'C',SC);d=ConditionLoss(mu,sd,maps(),'D',SC);assert torch.allclose(c.effective_standardized(p)[:,SC[0]],d.effective_standardized(p)[:,SC[0]],atol=2e-6)

def test_initialization_and_validation():
 mu,sd=stats();hashes=[]
 points=[data.MoleculeDatapoint.from_smi(s,np.r_[np.arange(22),np.zeros(4),np.ones(4)].astype(np.float32)) for s in ['CC','CCO']];ds=data.MoleculeDataset(points,featurizers.SimpleMoleculeMolGraphFeaturizer());batch=next(iter(exact_eval_loader(ds,num_workers=0)))
 for arm in ['A','B','C','D']:
  torch.manual_seed(42);criterion=ConditionLoss(mu,sd,maps(),arm,SC);model=ConditionMPNN(nn.BondMessagePassing(d_h=16,depth=2),nn.MeanAggregation(),nn.RegressionFFN(n_tasks=30,input_dim=16,hidden_dim=8,criterion=criterion,output_transform=nn.UnscaleTransform(mu,sd)))
  h=hashlib.sha256()
  for name,p in model.named_parameters():h.update(name.encode());h.update(p.detach().numpy().tobytes())
  hashes.append(h.hexdigest());model.eval();model.on_validation_model_eval();model.on_validation_epoch_start();model.validation_step(batch);assert np.array_equal(model._primary_validation[0][2],np.zeros((2,4))) and np.array_equal(model._primary_validation[0][3],np.ones((2,4)))
 assert len(set(hashes))==1
if __name__=='__main__':
 test_routes_and_mass();test_initialization_and_validation();print(json.dumps({'P8c_numerical_tests':'PASS','checks':['fixed22denominator','A/Bprimarygradientmass','noobservedmaskrenormalization','singleC/Droutegradient','zero_unused_screen_and_boundgradients','rawunits_sameg','initialparameterparity','boundoffsets_and_validationpath'],'fits':0}))
