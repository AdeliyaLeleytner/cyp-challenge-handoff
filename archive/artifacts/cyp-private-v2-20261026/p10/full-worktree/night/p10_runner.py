import os,json,time,hashlib,sys,subprocess,importlib.metadata,copy
from pathlib import Path
import numpy as np,pandas as pd,torch,lightning.pytorch as pl
from chemprop import data,featurizers,nn
from lightning.pytorch.callbacks import ModelCheckpoint,EarlyStopping,Callback
from .p3_core import macro_strae,exact_eval_loader
from .p10_core import ContinuationMAE,ContinuationMPNN,install_parent,prediction_state,tensor_hash,evaluate_stop,predict_raw

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
class Audit(Callback):
 def on_train_start(self,trainer,model):
  assert model.training and model.predictor.output_transform.training and model.bn.training
  assert trainer.global_step==0 and not trainer.lr_scheduler_configs and len(trainer.optimizers)==1 and len(trainer.optimizers[0].state)==0
  assert all(g['lr']==1e-4 and g['weight_decay']==0 for g in trainer.optimizers[0].param_groups)
  print(json.dumps({'event':'optimizer_reset_verified','state_entries':0,'scheduler_count':0,'lr':1e-4}),flush=True)
 def on_train_epoch_start(self,trainer,model):
  assert model.training and model.bn.training and model.predictor.output_transform.training
  self.start=time.time();print(json.dumps({'event':'epoch_batch_rng','continuation_epoch':trainer.current_epoch+1,'CPU_RNG_sha256':hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest()}),flush=True)
 def on_train_epoch_end(self,trainer,model):
  lr=[g['lr'] for g in trainer.optimizers[0].param_groups];assert all(x==1e-4 for x in lr)
  print(json.dumps({'event':'epoch_timing','continuation_epoch':trainer.current_epoch+1,'seconds':time.time()-self.start,'lr':lr,'batches':model.p10_batches,'no_primary_batches':model.p10_no_primary_batches}),flush=True)
 def on_train_batch_start(self,trainer,model,batch,batch_idx):
  if time.time()>float(os.environ['P10_DEADLINE_UNIX'])-900:raise TimeoutError('Recovery margin reached')

def build(mean,scale,primary):
 mp=nn.BondMessagePassing(d_h=2048,depth=4,dropout=.2);ff=nn.RegressionFFN(n_tasks=26,input_dim=2168,hidden_dim=1024,n_layers=2,dropout=.2,criterion=ContinuationMAE(mean,scale,primary),output_transform=nn.UnscaleTransform(mean,scale))
 return ContinuationMPNN(mp,nn.NormAggregation(),ff,batch_norm=True,metrics=[nn.metrics.MAE()])

def direct_metrics(y,p,lo,hi):
 from scipy.stats import spearmanr,kendalltau,pearsonr
 from sklearn.metrics import mean_absolute_error,r2_score
 score,per=macro_strae(y,p,lo,hi);out=[]
 for j in range(4):
  ok=np.isfinite(y[:,j]);a=y[ok,j];b=p[ok,j];out.append({'ST-RAE':per[j],'MAE':float(mean_absolute_error(a,b)),'R2':float(r2_score(a,b)),'Spearman':float(spearmanr(a,b).statistic),'Kendall':float(kendalltau(a,b).statistic),'Pearson':float(pearsonr(a,b).statistic),'RMSE':float(np.sqrt(np.mean((b-a)**2))),'bias':float(np.mean(b-a)),'prediction_SD':float(np.std(b)),'truth_SD':float(np.std(a))})
 return {'per_target':out,'macro':{k:float(np.mean([x[k] for x in out])) for k in out[0]}}

def parent_is_selected(epoch0_score,best_continuation_score):return not(best_continuation_score<epoch0_score)

def worker(cfg,cell,fold):
 parent,objective=cell.split('__');assert parent in ['zero','repaired'] and objective in ['all18','primary4'];primary=objective=='primary4';out=Path(cfg['output'])/f'{cell}_f{fold}';out.mkdir(parents=True,exist_ok=False);stage=Path(cfg['stage']);manifest=json.loads((stage/'manifest.json').read_text());assert sha(stage/'manifest.json')==cfg['manifest_sha256']
 for rel in ['common/table.csv','common/manifest.json','features/original.npy','features/repaired.npy','features/rows.csv','features/original-manifest.json']:
  assert sha(stage/rel)==manifest['files'][rel]
 spec=json.loads((stage/'common/manifest.json').read_text());df=pd.read_csv(stage/'common/table.csv',float_precision='round_trip');targets=spec['targets'];f=spec['folds'][fold];pdir=stage/'parents'/f'{parent}_f{fold}';record=next(x for x in manifest['parents'] if x['parent']==parent and x['fold']==fold)
 for name,h in record['files'].items():assert sha(pdir/name)==h
 assert sha(pdir/'model-only.pt')==record['model_only_sha256'];export=torch.load(pdir/'model-only.pt',map_location='cpu',weights_only=False);initial=json.loads((pdir/'initial.json').read_text());transform=json.loads((pdir/'feature_transform.json').read_text());mean=np.array(initial['scaler_mean']);scale=np.array(initial['scaler_scale']);Y=df[targets].to_numpy(float);lo=df[[f'low_{j}' for j in range(4)]].to_numpy(float);hi=df[[f'high_{j}' for j in range(4)]].to_numpy(float);ys=np.c_[(Y-mean[:18])/scale[:18],lo,hi]
 rows=pd.read_csv(stage/'features/rows.csv');assert rows.molecule_name.tolist()==df.molecule_name.tolist() and rows.request_id.tolist()==df.request_id.tolist();fm=json.loads((stage/'features/original-manifest.json').read_text());assert transform['columns']==fm['columns'];raw=np.load(stage/'features'/('original.npy' if parent=='zero' else 'repaired.npy'));X=((np.where(np.isfinite(raw),raw,np.array(transform['median']))-np.array(transform['mean']))/np.array(transform['scale'])).astype(np.float32)
 if parent=='zero':X[:]=0
 assert np.isfinite(X).all();pl.seed_everything(42+fold,workers=True);torch.set_num_threads(4);torch.set_float32_matmul_precision('highest');device=torch.device('cuda:0');model=build(mean,scale,primary);state_hash=install_parent(model,export);assert state_hash==record['prediction_tensor_sha256'];model.to(device);feat=featurizers.SimpleMoleculeMolGraphFeaturizer()
 def ds(indices,labelled=True):return data.MoleculeDataset([data.MoleculeDatapoint.from_smi(df.smiles.iloc[i],ys[i].astype(np.float32) if labelled else None,weight=1.,x_d=X[i]) for i in indices],feat)
 train=ds(f['train']);stop=ds(f['stop']);query=ds(f['test'],False);stoploader=exact_eval_loader(stop);queryloader=exact_eval_loader(query);start=time.time();epoch0=evaluate_stop(model,stoploader,device);basepred=predict_raw(model,queryloader,device);expected=pd.read_csv(pdir/'test_raw.csv',float_precision='round_trip');assert expected.molecule_name.tolist()==df.molecule_name.iloc[f['test']].tolist();exp=expected[targets].to_numpy(float);error=np.abs(basepred-exp);assert np.allclose(basepred[:,:4],exp[:,:4],atol=1e-5,rtol=1e-5);assert (error[:,4:]/scale[4:18]).max()<=1e-5
 fit_roles={role:[i for i in f[role] if np.isfinite(Y[i,:4]).any()] for role in ['train','stop']};fit_ix=[i for role in fit_roles for i in fit_roles[role]];role_names=[role for role in fit_roles for _ in fit_roles[role]];fit_loader=exact_eval_loader(ds(fit_ix,False));epoch0_fitpred=predict_raw(model,fit_loader,device);fit_table=pd.DataFrame(epoch0_fitpred[:,:4],columns=targets[:4]);fit_table.insert(0,'molecule_name',df.molecule_name.iloc[fit_ix].tolist());fit_table['role']=role_names;fit_table.to_csv(out/'epoch0-primary-predictions.csv',index=False,float_format='%.17g')
 assert tensor_hash(prediction_state(model.state_dict()))==state_hash;save(out/'epoch0.json',{'parent':parent,'fold':fold,'parent_prediction_hash':state_hash,'parent_epoch':export['parent_epoch'],'stop':epoch0,'primary_parity_max_abs':float(error[:,:4].max()),'auxiliary_parity_max_training_SD':float((error[:,4:]/scale[4:18]).max()),'no_BN_or_predictive_state_mutation':True,'parent_test_csv_sha256':sha(pdir/'test_raw.csv')})
 save(out/'initial.json',{'cell':cell,'parent':parent,'objective':objective,'fold':fold,'prediction_tensor_sha256':state_hash,'scaler_mean':mean.tolist(),'scaler_scale':scale.tolist(),'feature_transform_sha256':sha(pdir/'feature_transform.json'),'parent_model_only_sha256':sha(pdir/'model-only.pt'),'loss_denominator':'original finite18 target mask, not numerator-active mask','primary_coefficient_unchanged':True,'optimizer':'fresh Adam constant1e-4,weight_decay0,no scheduler','epoch0_eligible':True,'skip_no_primary_batches':False})
 ck=ModelCheckpoint(dirpath=out/'checkpoints',monitor='primary_strae',mode='min',save_top_k=1);early=EarlyStopping(monitor='primary_strae',mode='min',patience=10);early.best_score=torch.tensor(epoch0['monitor_float32']);pl.seed_everything(42+fold,workers=True);model.train();assert model.training and model.predictor.output_transform.training and model.bn.training
 trainer=pl.Trainer(max_epochs=cfg['epochs'],accelerator='gpu',devices=1,precision='32-true',callbacks=[ck,early,Audit()],logger=False,enable_progress_bar=False,num_sanity_val_steps=0,enable_model_summary=False);trainer.fit(model,data.build_dataloader(train,batch_size=128,num_workers=2),stoploader)
 best_score=float(ck.best_model_score);use_parent=parent_is_selected(epoch0['monitor_float32'],best_score);best=torch.load(ck.best_model_path,map_location='cpu',weights_only=False)
 if use_parent:
  install_parent(model,export);pred=exp.copy();selected_epoch=0;selection_score=epoch0['monitor_float32']
 else:
  model.load_state_dict(best['state_dict']);model.to(device);pred=predict_raw(model,queryloader,device);selected_epoch=int(best['epoch'])+1;selection_score=best_score
 assert np.isfinite(pred).all();model.to(device);selected_fitpred=epoch0_fitpred.copy() if use_parent else predict_raw(model,fit_loader,device);fit_table=pd.DataFrame(selected_fitpred[:,:4],columns=targets[:4]);fit_table.insert(0,'molecule_name',df.molecule_name.iloc[fit_ix].tolist());fit_table['role']=role_names;fit_table.to_csv(out/'selected-primary-predictions.csv',index=False,float_format='%.17g')
 fit_diagnostics={}
 for role in fit_roles:
  pos=np.array([j for j,name in enumerate(role_names) if name==role]);idx=np.array(fit_ix)[pos];fit_diagnostics[role]={'epoch0':direct_metrics(Y[idx,:4],epoch0_fitpred[pos,:4],lo[idx],hi[idx]),'selected':direct_metrics(Y[idx,:4],selected_fitpred[pos,:4],lo[idx],hi[idx]),'same_IDs_and_masks':True}
 auxiliary=[];test_ix=np.array(f['test'])
 for j,target in enumerate(targets):
  valid=np.isfinite(Y[test_ix,j]);truth=Y[test_ix,j][valid]
  for label,values in [('epoch0',exp),('selected',pred)]:
   err=values[valid,j]-truth;auxiliary.append({'target':target,'group':'primary' if j<4 else 'auxiliary','model':label,'n':int(valid.sum()),'mae':float(np.abs(err).mean()),'rmse':float(np.sqrt(np.mean(err**2))),'bias':float(err.mean()),'standardized_mae':float(np.abs(err).mean()/scale[j])})
 save(out/'primary-fit-diagnostics.json',fit_diagnostics);pd.DataFrame(auxiliary).to_csv(out/'all18-test-errors.csv',index=False)
 selected_state=prediction_state(model.state_dict());selected_hash=tensor_hash(selected_state);torch.save({'prediction_state':{k:v.detach().cpu() for k,v in selected_state.items()},'prediction_tensor_sha256':selected_hash,'source_parent':record,'selected_continuation_epoch':selected_epoch,'parent_selected':use_parent},out/'selected-model.pt');table=pd.DataFrame(pred,columns=targets);table.insert(0,'molecule_name',df.molecule_name.iloc[f['test']].tolist());table.to_csv(out/'test_raw.csv',index=False,float_format='%.17g')
 t=np.array(f['test']);score,per=macro_strae(Y[t,:4],pred[:,:4],lo[t],hi[t]);from scipy.stats import pearsonr,spearmanr,kendalltau
 from sklearn.metrics import mean_absolute_error,r2_score
 pm=[]
 for j in range(4):
  mask=np.isfinite(Y[t,j]);a=Y[t,j][mask];b=pred[:,j][mask];pm.append({'ST-RAE':per[j],'MAE':float(mean_absolute_error(a,b)),'R2':float(r2_score(a,b)),'Spearman':float(spearmanr(a,b).statistic),'Kendall':float(kendalltau(a,b).statistic),'Pearson':float(pearsonr(a,b).statistic),'RMSE':float(np.sqrt(np.mean((b-a)**2))),'bias':float(np.mean(b-a)),'prediction_SD':float(np.std(b)),'truth_SD':float(np.std(a))})
 metrics={k:float(np.mean([x[k] for x in pm])) for k in pm[0]};save(out/'complete.json',{'status':'complete','cell':cell,'parent':parent,'objective':objective,'fold':fold,'seconds':time.time()-start,'epochs_run':int(trainer.current_epoch),'best_epoch':selected_epoch,'parent_selected':use_parent,'epoch0_stop_score':epoch0['monitor_float32'],'best_continuation_stop_score':best_score,'selected_stop_score':selection_score,'selection_uses_test_outcomes':False,'global_optimizer_steps':int(trainer.global_step),'training_batches':model.p10_batches,'no_primary_batches':model.p10_no_primary_batches,'raw_strae':score,'raw_metrics':metrics,'raw_per_target_metrics':pm,'test_not_selection':True,'initial_sha256':sha(out/'initial.json'),'prediction_sha256':sha(out/'test_raw.csv'),'selected_model_sha256':sha(out/'selected-model.pt'),'selected_prediction_tensor_sha256':selected_hash,'packages':{x:importlib.metadata.version(x) for x in ['torch','chemprop','lightning','numpy','pandas','scikit-learn']}});print(json.dumps({'event':'P10_job_complete','cell':cell,'fold':fold,'parent_selected':use_parent,'selected_epoch':selected_epoch,'seconds':time.time()-start}),flush=True)

def main():
 cfg=json.loads(Path('p10_config.json').read_text())
 if '--worker' in sys.argv:worker(cfg,sys.argv[-2],int(sys.argv[-1]));return
 out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=True);save(out/'run_started.json',{'unix':time.time(),'config':cfg});jobs=[(c,f) for f in cfg['folds'] for c in cfg['cells']];running={}
 while jobs or running:
  for gpu in cfg['gpus']:
   if gpu not in running and jobs:
    c,f=jobs.pop(0);log=open(out/f'{c}_f{f}.log','w');env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu));p=subprocess.Popen([sys.executable,'-u','-m','night.p10_runner','--worker',c,str(f)],stdout=log,stderr=subprocess.STDOUT,env=env);running[gpu]=(p,log,c,f)
  for gpu,(p,log,c,f) in list(running.items()):
   if p.poll() is not None:
    log.close();del running[gpu]
    if p.returncode:
     for q,*_ in running.values():q.terminate()
     raise RuntimeError(f'{c} fold{f} failed')
  time.sleep(2)
 records=[json.loads(p.read_text()) for p in sorted(out.glob('*_f*/complete.json'))];save(out/'complete.json',{'status':'complete','jobs':len(records),'smoke':cfg['smoke']});print(json.dumps({'event':'P10_final_summary','results':records}),flush=True)
if __name__=='__main__':main()
