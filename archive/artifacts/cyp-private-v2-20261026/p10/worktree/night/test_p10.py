import torch,numpy as np
from chemprop import nn
from .p10_core import ContinuationMAE,ContinuationMPNN,install_parent,prediction_state,tensor_hash

def test_denominator_and_gradients():
 p=torch.tensor(np.linspace(.2,1.2,52).reshape(2,26),dtype=torch.float32,requires_grad=True);y=torch.zeros_like(p);mask=torch.ones_like(p,dtype=torch.bool);mask[0,1]=False;weights=torch.ones(2,1);grad=[]
 for primary in [False,True]:
  loss=ContinuationMAE(np.zeros(26),np.ones(26),primary);v=loss(p,y,mask,weights);v.backward();grad.append(p.grad.clone());expected=(p[:,:4] if primary else p[:,:18]);m=mask[:,:4] if primary else mask[:,:18];assert torch.allclose(v,(expected.abs()*m).sum()/mask[:,:18].sum());assert torch.all(p.grad[:,18:]==0);p.grad.zero_()
 assert torch.equal(grad[0][:,:4],grad[1][:,:4]) and torch.all(grad[1][:,4:]==0)
 mask[:,:4]=False;loss=ContinuationMAE(np.zeros(26),np.ones(26),True);v=loss(p,y,mask,weights);assert v.item()==0 and v.requires_grad;v.backward();assert torch.all(p.grad==0)
 # No skipped update: Adam momentum can move a parameter on a subsequent zero-gradient step.
 x=torch.nn.Parameter(torch.tensor([1.]));opt=torch.optim.Adam([x],lr=1e-4);x.sum().backward();opt.step();opt.zero_grad();before=x.detach().clone();(x.sum()*0).backward();opt.step();assert not torch.equal(x,before)

def model(primary):
 return ContinuationMPNN(nn.BondMessagePassing(d_h=16,depth=2),nn.MeanAggregation(),nn.RegressionFFN(n_tasks=26,input_dim=16,hidden_dim=8,criterion=ContinuationMAE(np.zeros(26),np.ones(26),primary),output_transform=nn.UnscaleTransform(np.zeros(26),np.ones(26))),batch_norm=True)
def test_parent_and_optimizer():
 a=model(False);state=prediction_state(a.state_dict());export={'prediction_state':state,'prediction_tensor_sha256':tensor_hash(state)};b=model(True);install_parent(b,export);assert b.criterion.task_weights.reshape(-1)[4:18].sum()==0;opt=b.configure_optimizers();assert isinstance(opt,torch.optim.Adam) and len(opt.state)==0 and len(opt.param_groups)==1 and opt.param_groups[0]['lr']==1e-4 and opt.param_groups[0]['weight_decay']==0

def test_epoch0_eval_state():
 from chemprop import data,featurizers
 from .p10_core import evaluate_stop
 from .p3_core import exact_eval_loader
 m=model(False)
 with torch.no_grad():m.bn.running_mean.fill_(.4);m.bn.running_var.fill_(1.7);m.bn.num_batches_tracked.fill_(9)
 pts=[]
 for i,s in enumerate(['CC','CCO','CCN','c1ccccc1']):
  y=np.full(18,float(i),dtype=np.float32);pts.append(data.MoleculeDatapoint.from_smi(s,np.r_[y,np.full(4,i-.1),np.full(4,i+.1)].astype(np.float32)))
 ds=data.MoleculeDataset(pts,featurizers.SimpleMoleculeMolGraphFeaturizer());h=tensor_hash(prediction_state(m.state_dict()));v=evaluate_stop(m,exact_eval_loader(ds,batch_size=2,num_workers=0),torch.device('cpu'));assert np.isfinite(v['monitor_float32']) and h==tensor_hash(prediction_state(m.state_dict()))

def test_epoch0_to_train_mode():
 m=model(False);m.eval();assert not m.bn.training and not m.predictor.output_transform.training
 m.train();assert m.training and m.bn.training and m.predictor.output_transform.training
 # Training loss must see standardized predictions, never raw-unit unscaling.
 t=nn.UnscaleTransform(np.full(26,7.),np.full(26,2.));x=torch.ones(2,26)
 t.eval();assert torch.allclose(t(x),torch.full_like(x,9.))
 t.train();assert torch.equal(t(x),x)
 assert all(child.training for child in m.modules())

def test_parent_eligibility():
 from .p10_runner import parent_is_selected
 assert parent_is_selected(.5,.5) and parent_is_selected(.5,.6) and not parent_is_selected(.5,.4)

if __name__=='__main__':
 test_denominator_and_gradients();test_parent_and_optimizer();test_epoch0_eval_state();test_epoch0_to_train_mode();test_parent_eligibility();print('P10 numerical/epoch0/optimizer tests: PASS')
