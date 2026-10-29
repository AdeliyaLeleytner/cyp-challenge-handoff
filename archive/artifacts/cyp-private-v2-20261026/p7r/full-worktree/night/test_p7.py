import torch,numpy as np
from chemprop import nn,data,featurizers
from night.p3_core import MatchedLoss,PrimaryCheckpointMPNN

def test_feature_pair():
 def make():
  torch.manual_seed(42)
  model=PrimaryCheckpointMPNN(nn.BondMessagePassing(d_h=16,depth=2),nn.MeanAggregation(),nn.RegressionFFN(n_tasks=26,input_dim=136,hidden_dim=8,criterion=MatchedLoss(np.zeros(26),np.ones(26)),output_transform=nn.UnscaleTransform(np.zeros(26),np.ones(26))))
  layer=next(v for v in model.predictor.ffn.modules() if isinstance(v,torch.nn.Linear));layer.weight.data[:,16:]=0
  return model,layer
 a,al=make();b,bl=make();assert all(torch.equal(x,y) for x,y in zip(a.parameters(),b.parameters()))
 ds=data.MoleculeDataset([data.MoleculeDatapoint.from_smi(s,np.ones(26,dtype=np.float32),x_d=np.linspace(-1,1,120).astype(np.float32)*(i+1)) for i,s in enumerate(['CC','CCO','CCN','c1ccccc1'])],featurizers.SimpleMoleculeMolGraphFeaturizer())
 batch=next(iter(data.build_dataloader(ds,batch_size=4,shuffle=False)));g,vd,x,y,w,*_=batch
 a.eval();b.eval();assert torch.equal(a(g,vd,torch.zeros_like(x)),b(g,vd,x))
 b.train();pred=b(g,vd,x);b.criterion(pred,y,y.isfinite(),w).backward();assert bl.weight.grad[:,16:].abs().sum()>0;assert sum(p.grad.abs().sum() for p in b.message_passing.parameters() if p.grad is not None)>0
 print('P7 matching, epoch0 parity, feature/graph gradients: PASS')
if __name__=='__main__':test_feature_pair()
