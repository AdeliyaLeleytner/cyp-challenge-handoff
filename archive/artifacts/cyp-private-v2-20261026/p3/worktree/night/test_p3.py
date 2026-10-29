import numpy as np,torch
from night.p3_core import MatchedLoss,ci_weights,macro_strae

def test_loss():
 mu=np.arange(26)*.1;sd=np.ones(26);sd[:4]=[2,3,4,5];mu[18:]=0
 y=torch.full((2,26),float('nan'));y[:,:18]=.5;y[:,18:22]=torch.tensor([1.,1.,1.,1.]);y[:,22:]=2.
 mask=y.isfinite(); clean=y.nan_to_num();p=torch.zeros((2,26),requires_grad=True)
 for interval in [False,True]:
  c=MatchedLoss(mu,sd,interval);v=c(p,clean,mask,torch.ones(2,1));v.backward();assert torch.all(p.grad[:,18:]==0);p.grad.zero_()
  expected=c._calc_unreduced_loss(p,clean,mask)[:,:18].mean();assert torch.allclose(v,expected)
  # Criterion mode must not alter scaling.
  c.eval();assert torch.equal(c._calc_unreduced_loss(p,clean,mask),c.train()._calc_unreduced_loss(p,clean,mask))
 c=MatchedLoss(mu,sd,True);m=mask.clone();m[0,18]=False
 l=c._calc_unreduced_loss(p,clean,m);assert l[0,0]==.5
 # Raw-unit interval distance / train SD and numerical gradient.
 q=torch.full((2,26),-1.,requires_grad=True);loss=c._calc_unreduced_loss(q,clean,mask)[:,:4].sum();loss.backward();assert torch.allclose(q.grad[:,:4],-torch.ones((2,4)))
 eps=1e-3;a=q.detach().clone();b=a.clone();a[0,0]+=eps;b[0,0]-=eps
 delta=(c._calc_unreduced_loss(a,clean,mask)[0,0]-c._calc_unreduced_loss(b,clean,mask)[0,0])/(2*eps);assert abs(delta.item()+1)<1e-3

def test_weights():
 y=np.ones((6,4));l=np.zeros((6,4));h=np.arange(1,7)[:,None]*np.ones((6,4));tr=np.array([0,1,2]);w,meta=ci_weights(y,l,h,tr);h[3:]*=1000;w2,meta2=ci_weights(y,l,h,tr);assert meta==meta2 and np.array_equal(w[tr],w2[tr]);assert np.isclose(w[tr].mean(),1)

def test_metric():
 y=np.tile(np.arange(4)[:,None],(1,4)).astype(float);s,_=macro_strae(y,y,y-.1,y+.1);assert s==0
def test_chemprop_scaling():
 from chemprop import data,featurizers,nn
 from night.p3_core import PrimaryCheckpointMPNN
 mu=np.arange(26)*.1;sd=np.arange(26)*.05+1;mu[18:]=0;sd[18:]=1
 ff=nn.RegressionFFN(n_tasks=26,input_dim=16,hidden_dim=8,criterion=MatchedLoss(mu,sd),output_transform=nn.UnscaleTransform(mu,sd))
 m=PrimaryCheckpointMPNN(nn.BondMessagePassing(d_h=16,depth=2),nn.MeanAggregation(),ff)
 ds=data.MoleculeDataset([data.MoleculeDatapoint.from_smi('CC',np.arange(26).astype(np.float32)),data.MoleculeDatapoint.from_smi('CCO',(np.arange(26)+1).astype(np.float32))],featurizers.SimpleMoleculeMolGraphFeaturizer())
 batch=next(iter(data.build_dataloader(ds,batch_size=2,shuffle=False)));bmg,vd,xd,*_=batch
 m.eval();z=m.fingerprint(bmg,vd,xd);expected=m.predictor.ffn(z)
 assert torch.allclose(m.predictor(z),expected*torch.tensor(sd,dtype=torch.float32)+torch.tensor(mu,dtype=torch.float32))
 m.on_validation_model_eval();assert m.predictor.output_transform.training
 assert torch.allclose(m.predictor.train_step(z),expected)
 m.on_validation_epoch_start();m.validation_step(batch);arr=m._primary_validation[0]
 assert np.allclose(arr[1],expected[:,:4].detach().numpy()*sd[:4]+mu[:4],rtol=1e-5,atol=1e-6)

if __name__=='__main__':
 test_loss();test_weights();test_metric();test_chemprop_scaling();print('P3 numerical invariants: PASS')
