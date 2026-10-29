from pathlib import Path
import sys,json,hashlib,numpy as np,torch
P=Path(__file__).resolve().parents[2];O=Path(__file__).resolve().parent;W=P/'p8c/worktree';sys.path.insert(0,str(W));from night.p8c_core import ConditionLoss,FrozenMaps
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();maps=json.loads((P/'p8c/stage/selected_maps.json').read_text());eps=['cyp1a2','cyp2c9','cyp2d6','cyp3a4'];screens=[7,5,6,4];mu=np.linspace(-2,3,30);sd=np.linspace(.5,2,30);max_error=0.;rows=[]
for fold in range(5):
 entries=[next(m for m in maps if m['outer_fold']==fold and m['target']==e) for e in eps]
 for arm in ['A','B','C','D']:
  loss=ConditionLoss(mu,sd,entries,arm,screens);z=torch.zeros((11,30),requires_grad=True)
  with torch.no_grad():
   for j in range(4):
    z[:,j]=torch.linspace(3.2,7.4,11);z[:,18+j]=torch.linspace(2.7,6.9,11)
  effective=loss.effective_standardized(z);expected=z.detach().numpy().copy();raw=z.detach().numpy()*sd+mu
  if arm in ['C','D']:
   for j,s in enumerate(screens):
    m=entries[j]['map'];p=18+j if arm=='C' else j;zz=(raw[:,p]-m['x_mean'])/m['x_scale'];X=np.column_stack([np.ones(len(zz)),zz]+[np.maximum(zz-k,0) for k in m['knots']]);g=m['y_mean']+m['y_scale']*(X@np.array(m['coefficients']));expected[:,s]=(g-mu[s])/sd[s]
  error=float(np.max(np.abs(effective.detach().numpy()-expected)));max_error=max(max_error,error);assert np.allclose(effective.detach().numpy(),expected,rtol=1e-5,atol=1e-5)
  raw_effective=loss.raw_effective(torch.tensor(raw,dtype=torch.float32)).detach().numpy();assert np.allclose(raw_effective,effective.detach().numpy()*sd+mu,rtol=1e-5,atol=1e-5)
  # Only one screen observation: gradient must flow through exactly its intended potency or free screen head.
  for j,s in enumerate(screens):
   zz=torch.tensor(z.detach().numpy(),requires_grad=True);mask=torch.zeros_like(zz,dtype=torch.bool);mask[:,s]=True;target=torch.full_like(zz,100.);criterion=ConditionLoss(mu,sd,entries,arm,screens);v=criterion(zz,target,mask,torch.ones(11));v.backward();nonzero=torch.where(zz.grad.abs().sum(0)>0)[0].tolist();expectedcol=18+j if arm=='C' else j if arm=='D' else s;assert nonzero==[expectedcol],(arm,j,nonzero);manual=float((criterion.effective_standardized(zz).detach()[:,s]-100).abs().sum()/(11*22));assert np.isclose(float(v),manual,rtol=1e-6)
  # Missing real labels/carriers never renormalize the primary coefficient; A active supervision stays masked.
  zz=torch.zeros((2,30),requires_grad=True);target=torch.ones_like(zz);mask=torch.zeros_like(zz,dtype=torch.bool);mask[:,0]=True;mask[:,18:22]=True;mask[:,22:]=True;criterion=ConditionLoss(mu,sd,entries,arm,screens);v=criterion(zz,target,mask,torch.ones(2));v.backward();expectedloss=1/22 if arm=='A' else 5/22;assert np.isclose(float(v),expectedloss,rtol=1e-6);assert np.allclose(zz.grad[:,0].numpy(),-1/(2*22));assert torch.all(zz.grad[:,22:]==0);assert bool(torch.all(zz.grad[:,18:22]==0))==(arm=='A');assert not list(criterion.maps.parameters())
  rows.append({'fold':fold,'arm':arm,'max_formula_error':error,'routing_gradients_correct':True,'screen_counted_once':True,'fixed_Bx22_denominator':True,'A_active_mask_correct':True})
res={'status':'PASS','scientific_fits_performed':0,'type':'forward/autograd arithmetic checks, no optimizer or training','checks':rows,'max_float32_numpy_formula_error':max_error,'source_sha256':sha(W/'night/p8c_core.py'),'selected_maps_sha256':sha(P/'p8c/stage/selected_maps.json'),'runner_review_pending':True};(O/'ROUTING_CERTIFICATE.json').write_text(json.dumps(res,indent=2)+'\n');print({k:v for k,v in res.items() if k!='checks'})
