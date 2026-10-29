import os,json,time,hashlib,subprocess,sys,importlib.metadata
from pathlib import Path
import numpy as np,pandas as pd,torch,lightning.pytorch as pl
from sklearn.preprocessing import StandardScaler
from chemprop import data,featurizers,nn
from lightning.pytorch.callbacks import ModelCheckpoint,EarlyStopping,Callback
from .p3_core import macro_strae,exact_eval_loader
from .p8c_core import ConditionLoss,ConditionMPNN

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
class Timing(Callback):
 def on_train_epoch_start(self,trainer,module):self.t=time.time()
 def on_train_epoch_end(self,trainer,module):print(json.dumps({'event':'epoch_timing','epoch':trainer.current_epoch,'seconds':time.time()-self.t,'max_gpu_bytes':torch.cuda.max_memory_allocated()}),flush=True)
class Deadline(Callback):
 def on_train_batch_start(self,trainer,module,batch,batch_idx):
  if time.time()>float(os.environ['P8C_DEADLINE_UNIX'])-900:raise TimeoutError('Recovery margin reached')

def worker(cfg,cell,fold):
 out=Path(cfg['output'])/f'{cell}_f{fold}';out.mkdir(parents=True,exist_ok=False)
 stage=Path(cfg['stage']);manifest=json.loads((stage/'manifest.json').read_text());assert sha(stage/'manifest.json')==cfg['manifest_sha256'];assert sha(stage/'table.csv')==manifest['data_sha256']
 df=pd.read_csv(stage/'table.csv',float_precision='round_trip'); targets=manifest['targets'];Y=df[targets].to_numpy(float);lo=df[[f'low_{j}' for j in range(4)]].to_numpy(float);hi=df[[f'high_{j}' for j in range(4)]].to_numpy(float)
 f=manifest['folds'][fold];tr=np.array(f['train']);sc=StandardScaler().fit(Y[tr,:18]);active_sc=None if cell=='A' else StandardScaler().fit(Y[tr,18:22]);realmean=np.r_[sc.mean_,np.zeros(4) if active_sc is None else active_sc.mean_];realscale=np.r_[sc.scale_,np.ones(4) if active_sc is None else active_sc.scale_];mean=np.r_[realmean,np.zeros(8)];scale=np.r_[realscale,np.ones(8)]
 assert np.isfinite(mean).all() and np.isfinite(scale).all() and (scale>0).all()
 scaled=(Y-realmean)/realscale
 if cell=='A':scaled[:,18:22]=np.nan
 ys=np.c_[scaled,lo,hi];w=np.ones(len(df));wmeta={'scheme':'uniform','denominator':'batch_rows*22'}
 assert sha(stage/'selected_maps.json')==manifest['selected_maps_sha256'] and sha(stage/'selector_membership.csv')==manifest['selector_membership_sha256']
 allmaps=json.loads((stage/'selected_maps.json').read_text());eps=['cyp1a2','cyp2c9','cyp2d6','cyp3a4'];selected=[next(x for x in allmaps if x['outer_fold']==fold and x['target']==e) for e in eps]
 for j,m in enumerate(selected):
  ix=tr[np.isfinite(Y[tr,18+j])&np.isfinite(Y[tr,manifest['screen_indices'][j]])];digest=hashlib.sha256('\n'.join(df.molecule_name.iloc[ix]).encode()).hexdigest();assert digest==m['fit_ids_sha256'] and len(ix)==m['fit_count']
 save(out/'frozen_maps.json',{'outer_fold':fold,'source_sha256':manifest['selected_maps_sha256'],'maps':selected,'no_nuisance_refit':True})
 pl.seed_everything(42+fold,workers=True);torch.set_num_threads(4);torch.set_float32_matmul_precision('highest')
 feat=featurizers.SimpleMoleculeMolGraphFeaturizer()
 def dataset(indices):return data.MoleculeDataset([data.MoleculeDatapoint.from_smi(df.smiles.iloc[i],ys[i].astype(np.float32),weight=float(w[i])) for i in indices],feat)
 train=dataset(tr);stop=dataset(f['stop']);start=time.time()
 criterion=ConditionLoss(mean,scale,selected,cell,manifest['screen_indices'])
 def make():
  mp=nn.BondMessagePassing(d_h=2048,depth=4,dropout=.2)
  ff=nn.RegressionFFN(n_tasks=30,input_dim=2048,hidden_dim=1024,n_layers=2,dropout=.2,criterion=criterion,output_transform=nn.UnscaleTransform(mean,scale))
  return ConditionMPNN(mp,nn.NormAggregation(),ff,batch_norm=True,metrics=[nn.metrics.MAE()],warmup_epochs=2,init_lr=1e-4,max_lr=1e-3,final_lr=1e-4)
 model=make();h=hashlib.sha256()
 for n,p in model.named_parameters():h.update(n.encode());h.update(p.detach().numpy().tobytes())
 save(out/'initial.json',{'cell':cell,'fold':fold,'parameter_sha256':h.hexdigest(),'initial_batchnorm_buffers':{n:v.detach().cpu().tolist() for n,v in model.named_buffers() if 'running_mean' in n or 'running_var' in n or 'num_batches_tracked' in n},'parameter_count':sum(p.numel() for p in model.parameters()),'scaler_mean':mean.tolist(),'scaler_scale':scale.tolist(),'raw_unit_primary_loss_multipliers':(1/scale[:4]).tolist(),'task_weights':'22 fixed task slots; coefficient1; active A masked;8carriers excluded','active_scaler':'identity unused inA' if cell=='A' else 'postpurge train-only','direct_primary_loss_mass_unchanged_between_arms':True,'weight_fit':wmeta,'checkpoint_metric':'unweighted raw primary macro ST-RAE on stoppingonly','effective_training_metric':'fixed-slot standardized MAE; C/Dscreen terms replaced by frozen empirical route; not macroST-RAE training','train_rows':len(tr),'stop_rows':len(stop),'test_rows':len(f['test'])})
 ck=ModelCheckpoint(dirpath=out/'checkpoints',monitor='primary_strae',mode='min',save_top_k=1)
 trainer=pl.Trainer(max_epochs=cfg['epochs'],accelerator='gpu',devices=1,precision='32-true',callbacks=[ck,EarlyStopping(monitor='primary_strae',mode='min',patience=30),Timing(),Deadline()],logger=False,enable_progress_bar=False,num_sanity_val_steps=0,enable_model_summary=False)
 trainer.fit(model,data.build_dataloader(train,batch_size=128,num_workers=2),exact_eval_loader(stop))
 best=torch.load(ck.best_model_path,map_location='cpu',weights_only=False);model.load_state_dict(best['state_dict']);model.eval()
 query=data.MoleculeDataset([data.MoleculeDatapoint.from_smi(df.smiles.iloc[i]) for i in f['test']],feat)
 network_pred=np.concatenate(trainer.predict(model,exact_eval_loader(query)));model.cpu();pred=model.criterion.raw_effective(torch.as_tensor(network_pred)).detach().numpy()[:,:22];assert pred.shape==(len(query),22) and np.isfinite(pred).all()
 t=np.array(f['test']);aux=[]
 for j,screen in enumerate(manifest['screen_indices']):
  active=18+j;sm=np.isfinite(Y[t,screen]);am=np.isfinite(Y[t,active]);route=active if cell=='C' else j;mm=selected[j]['map'];z=network_pred[:,route];ex=(z<mm['fit_min'])|(z>mm['fit_max'])
  aux.append({'target':eps[j],'screen_observations':int(sm.sum()),'screen_mae':float(np.abs(pred[sm,screen]-Y[t,screen][sm]).mean()),'active_observations':int(am.sum()),'active_mae':None if cell=='A' else float(np.abs(pred[am,active]-Y[t,active][am]).mean()),'predicted_route_extrapolation_fraction':float(ex.mean()) if cell in ['C','D'] else None,'raw_potency_range':[float(z.min()),float(z.max())] if cell in ['C','D'] else None})
 save(out/'auxiliary_diagnostics.json',{'arm':cell,'scope':'heldout auxiliary diagnostics only; not used for checkpoint/promotion','values':aux})
 o=pd.DataFrame(pred,columns=targets);o.insert(0,'molecule_name',df.molecule_name.iloc[t].to_list());o.to_csv(out/'test_raw.csv',index=False,float_format='%.17g')
 score,per=macro_strae(Y[t,:4],pred[:,:4],lo[t],hi[t])
 from scipy.stats import pearsonr,spearmanr,kendalltau
 from sklearn.metrics import mean_absolute_error,r2_score
 permetrics=[]
 for j in range(4):
  mask=np.isfinite(Y[t,j]);a=Y[t,j][mask];b=pred[:,j][mask]
  permetrics.append({'ST-RAE':per[j],'MAE':float(mean_absolute_error(a,b)),'R2':float(r2_score(a,b)),'Pearson':float(pearsonr(a,b).statistic),'Spearman':float(spearmanr(a,b).statistic),'Kendall':float(kendalltau(a,b).statistic)})
 metrics={name:float(np.mean([m[name] for m in permetrics])) for name in permetrics[0]}
 save(out/'complete.json',{'status':'complete','cell':cell,'fold':fold,'seconds':time.time()-start,'best_epoch':int(best['epoch']),'epochs_run':int(trainer.current_epoch),'raw_strae':score,'raw_per_target_strae':per,'raw_metrics':metrics,'raw_per_target_metrics':permetrics,'test_not_selection':True,'served_metrics':'not computed in runtime smoke; raw and served must remain separate','initial_sha256':sha(out/'initial.json'),'parameter_sha256':h.hexdigest(),'prediction_sha256':sha(out/'test_raw.csv'),'packages':{n:importlib.metadata.version(n) for n in ['torch','chemprop','lightning','numpy','pandas','scipy','scikit-learn','rdkit']}})
 print(json.dumps({'event':'p8c_complete','cell':cell,'fold':fold,'seconds':time.time()-start,'raw_strae':score,'raw_per_target_strae':per}),flush=True)

def main():
 cfg=json.loads(Path('p8c_config.json').read_text())
 if '--worker' in sys.argv:worker(cfg,sys.argv[-2],int(sys.argv[-1]));return
 out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=True);save(out/'run_started.json',{'unix':time.time(),'config':cfg})
 jobs=[(c,f) for f in cfg['folds'] for c in cfg['cells']];running={}
 while jobs or running:
  for gpu in cfg['gpus']:
   if gpu not in running and jobs:
    c,f=jobs.pop(0);log=open(out/f'{c}_f{f}.log','w');env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu));p=subprocess.Popen([sys.executable,'-u','-m','night.p8c_runner','--worker',c,str(f)],stdout=log,stderr=subprocess.STDOUT,env=env);running[gpu]=(p,log,c,f)
  for gpu,(p,log,c,f) in list(running.items()):
   if p.poll() is not None:
    log.close();del running[gpu]
    if p.returncode:
     for q,*_ in running.values():q.terminate()
     raise RuntimeError(f'{c} fold{f} failed')
  time.sleep(2)
 initial=[json.loads(p.read_text()) for p in sorted(out.glob('*_f*/initial.json'))]
 for f in cfg['folds']:
  same=[x for x in initial if x['fold']==f];assert len(same)==4 and len({x['parameter_sha256'] for x in same})==1;assert all(x['initial_batchnorm_buffers']==same[0]['initial_batchnorm_buffers'] for x in same)
 print(json.dumps({'event':'matched_profile_summary','results':[json.loads(p.read_text()) for p in sorted(out.glob('*_f*/complete.json'))]}),flush=True)
 save(out/'complete.json',{'status':'complete','jobs':len(cfg['folds'])*len(cfg['cells']),'smoke':cfg['smoke']})
if __name__=='__main__':main()
