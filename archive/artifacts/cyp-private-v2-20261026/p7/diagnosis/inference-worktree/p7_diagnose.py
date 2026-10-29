"""Frozen P7 checkpoint inference; no optimizer construction or fitting."""
from pathlib import Path
import json,hashlib,time,sys,importlib.metadata,gc
import numpy as np,pandas as pd,torch
from chemprop import data,featurizers,nn
from night.p3_core import MatchedLoss,PrimaryCheckpointMPNN,exact_eval_loader

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def make_model(initial):
 mu=initial['scaler_mean'];sd=initial['scaler_scale'];mp=nn.BondMessagePassing(d_h=2048,depth=4,dropout=.2);ff=nn.RegressionFFN(n_tasks=26,input_dim=2168,hidden_dim=1024,n_layers=2,dropout=.2,criterion=MatchedLoss(mu,sd,False),output_transform=nn.UnscaleTransform(mu,sd));return PrimaryCheckpointMPNN(mp,nn.NormAggregation(),ff,batch_norm=True,metrics=[nn.metrics.MAE()],warmup_epochs=2,init_lr=1e-4,max_lr=1e-3,final_lr=1e-4)
def load_model(cfg,cell,fold):
 r=Path(cfg['results'])/f'{cell}_f{fold}';ini=json.loads((r/'initial.json').read_text());ckpt=next((r/'checkpoints').glob('*.ckpt'));t=time.perf_counter();state=torch.load(ckpt,map_location='cpu',weights_only=False);model=make_model(ini);model.load_state_dict(state['state_dict'],strict=True);model.eval();model.requires_grad_(False)
 first=next(p for p in model.predictor.ffn.modules() if isinstance(p,torch.nn.Linear));assert first.in_features==2168
 cb=[]
 for name,v in state.get('callbacks',{}).items():
  row={'callback':str(name)}
  for key in ['best_model_score','current_score','best_score','wait_count','stopped_epoch']:
   if key in v:
    z=v[key];row[key]=float(z) if isinstance(z,torch.Tensor) else z
  cb.append(row)
 meta={'cell':cell,'fold':fold,'checkpoint_epoch':int(state['epoch']),'load_seconds':time.perf_counter()-t,'callbacks':cb,'graph_input_weight_frobenius':float(first.weight[:,:2048].norm()),'descriptor_input_weight_frobenius':float(first.weight[:,2048:].norm()),'graph_bn_gamma_rms':float(model.bn.weight.square().mean().sqrt()),'graph_bn_beta_rms':float(model.bn.bias.square().mean().sqrt()),'optimizer_steps_in_diagnostic':0}
 del state;gc.collect();return model,ini,meta

def features(cfg,cell,fold,raw):
 tr=json.loads((Path(cfg['results'])/f'{cell}_f{fold}'/'feature_transform.json').read_text());assert tr['columns']==cfg['columns'];z=(np.where(np.isfinite(raw),raw,np.array(tr['median']))-np.array(tr['mean']))/np.array(tr['scale']);z=z.astype(np.float32);assert np.isfinite(z).all()
 return np.zeros_like(z) if cell=='zero' else z

def predict(model,df,ix,X,variants,blocks,batch=128):
 start=time.perf_counter();ds=data.MoleculeDataset([data.MoleculeDatapoint.from_smi(df.smiles.iloc[i]) for i in ix],featurizers.SimpleMoleculeMolGraphFeaturizer());loader=exact_eval_loader(ds,batch_size=batch,num_workers=0);prep=time.perf_counter()-start;values={k:[] for k in variants};components=[];offset=0;forward=time.perf_counter()
 first=next(p for p in model.predictor.ffn.modules() if isinstance(p,torch.nn.Linear))
 with torch.inference_mode():
  for b in loader:
   graph=model.fingerprint(b[0],b[1],None);n=len(graph);xx=torch.tensor(X[np.asarray(ix[offset:offset+n])]);offset+=n
   ug=graph@first.weight[:,:2048].T;uf=xx@first.weight[:,2048:].T
   components.extend(zip(graph.norm(dim=1).tolist(),xx.norm(dim=1).tolist(),ug.norm(dim=1).tolist(),uf.norm(dim=1).tolist()))
   for kind in variants:
    cur=xx.clone()
    if kind!='baseline':cur[:,blocks[kind]['indices']]=0
    pred=model.predictor(torch.cat([graph,cur],dim=1));values[kind].append(pred[:,:18].cpu().numpy())
 assert offset==len(ix) and all(p.grad is None for p in model.parameters())
 return {k:np.concatenate(v) for k,v in values.items()},{'featurization_seconds':prep,'forward_seconds':time.perf_counter()-forward,'rows':len(ix)},np.asarray(components)

def saved_oof(cfg,df,folds,targets,out):
 records=[];count=[]
 for fold,f in enumerate(folds):
  ix=np.array(f['test']);truth=df[targets].to_numpy(float)[ix];tr=np.array(f['train']);training=df[targets].to_numpy(float)[tr]
  for j,t in enumerate(targets):count.append({'fold':fold,'target':t,'group':'primary' if j<4 else 'auxiliary','train_observed':int(np.isfinite(training[:,j]).sum())})
  for cell in ['zero','fusion']:
   r=Path(cfg['results'])/f'{cell}_f{fold}';p=pd.read_csv(r/'test_raw.csv',float_precision='round_trip');assert p.molecule_name.tolist()==df.molecule_name.iloc[ix].tolist();pred=p[targets].to_numpy(float);ini=json.loads((r/'initial.json').read_text());sd=np.asarray(ini['scaler_scale'])[:18]
   for j,t in enumerate(targets):
    m=np.isfinite(truth[:,j]);a=truth[m,j];v=pred[m,j];e=v-a;records.append({'fold':fold,'cell':cell,'target':t,'group':'primary' if j<4 else 'auxiliary','n':len(a),'mae':float(abs(e).mean()),'rmse':float(np.sqrt((e*e).mean())),'bias':float(e.mean()),'prediction_sd':float(v.std()),'truth_sd':float(a.std()),'standardized_mae':float(abs(e).mean()/sd[j]),'sum_abs_error':float(abs(e).sum()),'sum_sq_error':float((e*e).sum()),'sum_error':float(e.sum()),'sum_standardized_abs_error':float(abs(e).sum()/sd[j])})
 pd.DataFrame(records).to_csv(out/'saved-oof-all18-byfold.csv',index=False);pd.DataFrame(count).to_csv(out/'training-label-counts.csv',index=False);v=pd.DataFrame(records);rows=[]
 for (cell,target),g in v.groupby(['cell','target']):
  n=int(g.n.sum());rows.append({'cell':cell,'target':target,'group':g.group.iloc[0],'n':n,'mae':float(g.sum_abs_error.sum()/n),'rmse':float(np.sqrt(g.sum_sq_error.sum()/n)),'bias':float(g.sum_error.sum()/n),'standardized_mae':float(g.sum_standardized_abs_error.sum()/n)})
 pd.DataFrame(rows).to_csv(out/'saved-oof-all18-pooled.csv',index=False)

def main():
 cfg=json.loads(Path('p7d_config.json').read_text());assert cfg['stage']=='canary';out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4);torch.set_float32_matmul_precision('highest');start=time.time()
 for p,h in cfg['input_hashes'].items():assert sha(p)==h,p
 df=pd.read_csv(cfg['table'],float_precision='round_trip');m=json.loads(Path(cfg['folds']).read_text());fm=json.loads(Path(cfg['feature_manifest']).read_text());assert fm['columns']==cfg['columns'];row=pd.read_csv(cfg['feature_rows']);assert row.molecule_name.tolist()==df.molecule_name.tolist() and row.request_id.tolist()==df.request_id.tolist();raw=np.load(cfg['feature_matrix']);blocks=json.loads(Path(cfg['blocks']).read_text())['blocks']
 y=df[m['targets'][:4]].to_numpy(float);ix=[i for i in m['folds'][0]['test'] if np.isfinite(y[i]).any()][:32];assert [df.molecule_name.iloc[i] for i in ix]==cfg['canary_ids'];save(out/'canary-ids.json',cfg['canary_ids']);saved_oof(cfg,df,m['folds'],m['targets'],out);summary=[]
 for cell in ['zero','fusion']:
  model,ini,meta=load_model(cfg,cell,0);X=features(cfg,cell,0,raw);pred,timing,comp=predict(model,df,ix,X,['baseline'],blocks,batch=32);expected=pd.read_csv(Path(cfg['results'])/f'{cell}_f0/test_raw.csv',float_precision='round_trip').set_index('molecule_name').loc[cfg['canary_ids'],m['targets']].to_numpy();a=pred['baseline'];err=np.abs(a-expected);assert np.allclose(a,expected,atol=cfg['atol'],rtol=cfg['rtol']),{'cell':cell,'max_abs':float(err.max())}
  warm,timing2,comp2=predict(model,df,ix,X,['baseline'],blocks,batch=32);assert np.allclose(a,warm['baseline'],atol=cfg['atol'],rtol=cfg['rtol']);pd.DataFrame(a,columns=m['targets']).assign(molecule_name=cfg['canary_ids']).to_csv(out/f'{cell}-canary.csv',index=False)
  pd.DataFrame(comp,columns=['graph_l2','descriptor_l2','graph_firstlinear_contribution_l2','descriptor_firstlinear_contribution_l2']).to_csv(out/f'{cell}-canary-components.csv',index=False)
  meta.update(parity_pass=True,max_abs_error=float(err.max()),primary_max_abs_error=float(err[:,:4].max()),cold_timing=timing,warm_timing=timing2);summary.append(meta);del model;gc.collect()
 roles=sum(sum(np.isfinite(y[np.asarray(f[role])]).any(1)) for f in m['folds'] for role in ['train','stop','test'])*2;speed=max((x['warm_timing']['forward_seconds']+x['warm_timing']['featurization_seconds'])/32 for x in summary);receipt={'status':'PASS','stage':'32-rowcanary_and_savedOOFdiagnostics','summary':summary,'estimated_full_graph_rows':int(roles),'estimated_CPU_seconds_baseline_only':float(roles*speed),'extra_head_interventions_not_in_estimate':True,'runtime':{n:importlib.metadata.version(n) for n in ['torch','chemprop','lightning','numpy','pandas','scikit-learn']},'training_runtime_difference':'TrainingTorch2.6CUDA12.4; thislocalCPUdiagnostic uses runtimebelow and must pass numericalcanary','fits':0,'optimizer_steps':0,'seconds':time.time()-start,'source_sha256':sha(__file__),'config_sha256':sha('p7d_config.json')};save(out/'complete.json',receipt);print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
