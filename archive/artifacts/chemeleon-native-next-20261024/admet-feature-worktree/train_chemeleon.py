from pathlib import Path
import json,time,hashlib,platform
import numpy as np
import pandas as pd
import torch,chemprop
from lightning import pytorch as pl
from lightning.pytorch.callbacks import ModelCheckpoint,EarlyStopping,Callback
from lightning.pytorch.loggers import CSVLogger
from chemprop import data
from scipy.stats import spearmanr,kendalltau
from sklearn.metrics import mean_absolute_error,r2_score
from modeling import datasets,build,CYP,COLS
from official_scoring_functions import rae_soft_threshold_absolute_error as strae

OUT=Path('outputs');OUT.mkdir(exist_ok=True)
cfg=json.loads(Path('config.json').read_text());pl.seed_everything(cfg['seed'],workers=True);torch.set_num_threads(6)
assert cfg['accelerator']=='gpu' and torch.cuda.is_available()
train,val,td,vd,scaler,feat=datasets();model,info=build(scaler,cfg)
initial_encoder=model.message_passing.W_i.weight.detach().clone()
info.update({'configuration':cfg,'torch':torch.__version__,'chemprop':chemprop.__version__,'lightning':pl.__version__,
             'python':platform.python_version(),'n_train':len(train),'n_validation':len(val),'target_means':scaler.mean_.tolist(),'target_scales':scaler.scale_.tolist()})
(OUT/'run-manifest.json').write_text(json.dumps(info,indent=2)+'\n');print('RUN_CONFIGURATION',json.dumps(info),flush=True)
tl=data.build_dataloader(td,batch_size=cfg['batch_size'],num_workers=0,seed=cfg['seed'])
vl=data.build_dataloader(vd,batch_size=cfg['batch_size'],num_workers=0,shuffle=False)

class Progress(Callback):
    def on_train_epoch_start(self,trainer,pl_module):self.start=time.monotonic()
    def on_validation_end(self,trainer,pl_module):
        if trainer.sanity_checking:return
        row={'epoch':trainer.current_epoch,'elapsed_epoch_seconds':time.monotonic()-self.start}
        for k,v in trainer.callback_metrics.items():
            if hasattr(v,'numel') and v.numel()==1:row[k]=float(v.detach().cpu())
        with (OUT/'history.jsonl').open('a') as h:h.write(json.dumps(row)+'\n')
        print('EPOCH',json.dumps(row),flush=True)

checkpoint=ModelCheckpoint(dirpath=OUT/'checkpoints',filename='best-{epoch:03d}-{val_loss:.5f}',monitor='val_loss',mode='min',save_top_k=1,save_last=False,save_weights_only=True)
trainer=pl.Trainer(accelerator=cfg['accelerator'],devices=1,precision='32-true',min_epochs=cfg['min_epochs'],max_epochs=cfg['max_epochs'],
    max_time={'hours':cfg['max_wall_hours']},callbacks=[checkpoint,EarlyStopping(monitor='val_loss',mode='min',patience=cfg['patience'],check_finite=True),Progress()],
    logger=CSVLogger(OUT,name='training'),enable_progress_bar=False,log_every_n_steps=10,num_sanity_val_steps=2,
    enable_model_summary=False,deterministic=False)
start=time.monotonic();trainer.fit(model,tl,vl,ckpt_path=cfg.get('resume_checkpoint'));training_seconds=time.monotonic()-start
assert checkpoint.best_model_path,'No best checkpoint'
# Lightning resets best-score metadata when the run directory changes. Preserve
# the preceding leg's best validation checkpoint explicitly; holdout remains unseen.
selected_path=checkpoint.best_model_path
selected_score=float(checkpoint.best_model_score.cpu()) if checkpoint.best_model_score is not None else float('inf')
if cfg.get('prior_best_validation_loss',float('inf'))<selected_score:
    selected_path=cfg['prior_best_checkpoint'];selected_score=cfg['prior_best_validation_loss']
# Trusted checkpoint produced by this run; no arbitrary external pickle.
ck=torch.load(selected_path,map_location='cpu',weights_only=False)
model.load_state_dict(ck['state_dict'],strict=True)
change=float((model.message_passing.W_i.weight.detach().cpu()-initial_encoder).abs().max())
assert change>0,'Encoder did not update'

# Final report set is loaded only after checkpoint selection. No target given to inference.
holdout=pd.read_csv('data/holdout.csv')
hd=data.MoleculeDataset([data.MoleculeDatapoint.from_smi(s,np.full(4,np.nan,dtype=np.float32)) for s in holdout.SMILES],feat);hd.cache=True
hl=data.build_dataloader(hd,batch_size=cfg['batch_size'],num_workers=0,shuffle=False)
preds=torch.cat(trainer.predict(model,dataloaders=hl)).detach().cpu().numpy()
assert preds.shape==(len(holdout),4) and np.isfinite(preds).all()
pd.DataFrame({'Molecule_Name':holdout.Molecule_Name,**{c:preds[:,i] for i,c in enumerate(COLS)}}).to_csv(OUT/'holdout_predictions.csv',index=False)
summary={'configuration':cfg,'training_seconds':training_seconds+cfg.get('prior_training_seconds',0),
         'current_leg_training_seconds':training_seconds,'epochs_completed':trainer.current_epoch,
         'selected_epoch':int(ck['epoch']),'best_validation_scaled_MSE':selected_score,
         'encoder_max_weight_change':change,'holdout_count':len(holdout),'endpoints':{}}
rng=np.random.default_rng(cfg['seed']+1);bs=[];bs_mean=[]
for k,c in enumerate(CYP):
    col=COLS[k];mask=holdout[col].notna().to_numpy();y=holdout.loc[mask,col].to_numpy();p=preds[mask,k]
    lo=holdout.loc[mask,col+'_conf_low'].to_numpy();hi=holdout.loc[mask,col+'_conf_high'].to_numpy()
    assert np.isfinite(lo).all() and np.isfinite(hi).all() and (lo<=hi).all()
    baseline=np.full_like(y,train[col].mean())
    denominator=float(np.maximum(lo-y.mean(),0).sum()+np.maximum(y.mean()-hi,0).sum())
    assert denominator>0
    b=[];bm=[]
    for _ in range(cfg['bootstrap_samples']):
        ii=rng.integers(0,len(y),size=len(y))
        b.append(float(strae(y[ii],p[ii],hi[ii],lo[ii])));bm.append(float(strae(y[ii],baseline[ii],hi[ii],lo[ii])))
    assert np.isfinite(b).all() and np.isfinite(bm).all()
    bs.append(b);bs_mean.append(bm)
    out={'n':len(y),'ST_RAE':float(strae(y,p,hi,lo)),'MAE':float(mean_absolute_error(y,p)),
       'R2':float(r2_score(y,p)),'Spearman':float(spearmanr(y,p).statistic),'Kendall':float(kendalltau(y,p).statistic),
       'train_mean_ST_RAE':float(strae(y,baseline,hi,lo)),'mean_reference_denominator':denominator,
       'predicted_std':float(np.std(p)),'interval_hit_fraction':float(np.mean((p>=lo)&(p<=hi))),
       'bootstrap_mean_ST_RAE':float(np.mean(b)),'bootstrap_95CI_ST_RAE':np.quantile(b,[.025,.975]).tolist()}
    summary['endpoints'][c]=out
    print('ENDPOINT',c,json.dumps(out),flush=True)
macro=np.mean(bs,axis=0);macromean=np.mean(bs_mean,axis=0)
summary['macro']={'ST_RAE':float(np.mean([v['ST_RAE'] for v in summary['endpoints'].values()])),
    'MAE':float(np.mean([v['MAE'] for v in summary['endpoints'].values()])),
    'train_mean_ST_RAE':float(np.mean([v['train_mean_ST_RAE'] for v in summary['endpoints'].values()])),
    'bootstrap_mean_ST_RAE':float(macro.mean()),'bootstrap_95CI_ST_RAE':np.quantile(macro,[.025,.975]).tolist(),
    'train_mean_bootstrap_mean_ST_RAE':float(macromean.mean())}
np.savez(OUT/'bootstrap_scores.npz',model=np.array(bs),train_mean=np.array(bs_mean),macro=macro)
summary['prediction_sha256']=hashlib.sha256((OUT/'holdout_predictions.csv').read_bytes()).hexdigest()
summary['selected_checkpoint']=selected_path
(OUT/'results.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
print('BASELINE_RESULT',json.dumps(summary,allow_nan=False),flush=True)
