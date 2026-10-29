from pathlib import Path
import argparse,sys,json,os,time,gc,hashlib,shutil,subprocess
import numpy as np,pandas as pd,torch
from lightning import pytorch as pl
from lightning.pytorch.callbacks import EarlyStopping,Callback
from chemprop import data,featurizers,nn
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor/src'))
from cyp_submission.chemprop_transfer import build_finetune_model,compute_inverse_count_task_weights
from cyp_submission.calibration import fit_placement_correction,apply_placement_correction
from cyp_submission.caruana import caruana_bagged_ensemble
from cyp_submission.metrics import isoform_st_rae
from cyp_submission.tabular_cv import pca_pipeline
from lightgbm import LGBMRegressor
CACHE=ROOT/'prepared'
PRIMARY=json.loads((CACHE/'target-columns.json').read_text())['primary'];TARGETS=json.loads((CACHE/'target-columns.json').read_text())['all']
CYP=[c.split('_')[0] for c in PRIMARY]
LGB_PARAMS=dict(n_estimators=500,learning_rate=.05,num_leaves=31,subsample=.8,colsample_bytree=.8,random_state=42,verbose=-1,n_jobs=4)
torch.set_num_threads(4)
class History(Callback):
    def __init__(self,path,tag):self.path=path;self.tag=tag
    def on_validation_end(self,trainer,model):
        if trainer.sanity_checking:return
        r={'model':self.tag,'epoch':trainer.current_epoch,'val_loss':float(trainer.callback_metrics['val_loss'].cpu())}
        with self.path.open('a') as h:h.write(json.dumps(r)+'\n')
        print('EPOCH',json.dumps(r),flush=True)
def ds(df,cols):
    d=data.MoleculeDataset([data.MoleculeDatapoint.from_smi(s,y) for s,y in zip(df.SMILES,df[cols].to_numpy(np.float32))],featurizers.SimpleMoleculeMolGraphFeaturizer());d.cache=True;return d

def finetune(tr,va,te,out,tag,weights):
    pl.seed_everything(42,workers=True)
    td=ds(tr,TARGETS);scaler=td.normalize_targets();vd=ds(va,TARGETS);vd.normalize_targets(scaler)
    model=build_finetune_model(ROOT/'vendor/checkpoints/chemprop_medium.pt',len(TARGETS),task_weights=weights,output_transform=nn.UnscaleTransform.from_standard_scaler(scaler))
    tl=data.build_dataloader(td,num_workers=0,batch_size=256);vl=data.build_dataloader(vd,num_workers=0,batch_size=256,shuffle=False,drop_last=False)
    trainer=pl.Trainer(logger=False,enable_checkpointing=False,enable_progress_bar=False,enable_model_summary=False,accelerator='gpu',devices=1,max_epochs=60,callbacks=[EarlyStopping(monitor='val_loss',patience=10,mode='min'),History(out/'history.jsonl',tag)])
    t=time.monotonic();trainer.fit(model,tl,vl)
    predset=data.MoleculeDataset([data.MoleculeDatapoint.from_smi(s,np.full(len(TARGETS),np.nan,dtype=np.float32)) for s in te.SMILES],featurizers.SimpleMoleculeMolGraphFeaturizer());predset.cache=True
    pred=torch.cat(trainer.predict(model,dataloaders=data.build_dataloader(predset,num_workers=0,batch_size=256,shuffle=False,drop_last=False))).cpu().numpy()[:,:4]
    assert pred.shape==(len(te),4) and np.isfinite(pred).all()
    meta={'tag':tag,'epochs_completed':trainer.current_epoch,'train_rows':len(tr),'validation_rows':len(va),'seconds':time.monotonic()-t,'task_weights':weights,'checkpoint':'Last stopping epoch, matching participant implementation; not best-epoch restoration.'}
    (out/(tag+'-training.json')).write_text(json.dumps(meta,indent=2));print('FINETUNE_COMPLETE',json.dumps(meta),flush=True)
    if tag=='final':torch.save({'state_dict':model.cpu().state_dict(),'hyper_parameters':model.hparams},out/'chemprop-final.pt')
    del model,trainer,td,vd,predset,tl,vl;gc.collect();torch.cuda.empty_cache()
    return pred

def tabfit(X,tridx,predidx,train,out,tag,save=False):
    from tabpfn import TabPFNRegressor
    xt,xp=pca_pipeline(X[tridx],X[predidx],n_components=200)
    pred=np.empty((len(predidx),4))
    for k,c in enumerate(PRIMARY):
        y=train.iloc[tridx][c].to_numpy();m=np.isfinite(y)
        model=TabPFNRegressor(n_estimators=8,device='cuda',random_state=42)
        model.fit(xt[m],y[m]);pred[:,k]=np.asarray(model.predict(xp)).ravel()
        print('TABPFN_DONE',tag,c,'fit',int(m.sum()),'pred',len(predidx),flush=True)
        del model;gc.collect();torch.cuda.empty_cache()
    return pred

def lgbfit(X,tridx,predidx,train,out=None,tag=''):
    pred=np.empty((len(predidx),4))
    for k,c in enumerate(PRIMARY):
        y=train.iloc[tridx][c].to_numpy();m=np.isfinite(y);model=LGBMRegressor(**LGB_PARAMS);model.fit(X[tridx][m],y[m]);pred[:,k]=model.predict(X[predidx])
        if out is not None:model.booster_.save_model(str(out/f'lgb-{tag}-{CYP[k]}.txt'))
    return pred

def savepred(out,name,ids,pred):
    assert pred.shape==(len(ids),4) and np.isfinite(pred).all()
    pd.DataFrame({'Molecule_Name':ids,**{c:pred[:,k] for k,c in enumerate(PRIMARY)}}).to_csv(out/f'{name}.csv',index=False)

def ensemble(name):
    train=pd.read_csv(CACHE/'challenge.csv');aux=pd.read_csv(CACHE/'aux.csv');r=json.loads((CACHE/'roles.json').read_text())[name]
    out=ROOT/'outputs'/name;out.mkdir(exist_ok=True)
    dev=np.asarray(r['dev']);outer=np.asarray(r['test']);folds=np.asarray(r['inner_folds']);X=np.load(CACHE/'classical.npy')
    savepred(out,'lgb_matched',train.iloc[outer].Molecule_Name.to_numpy(),lgbfit(X,np.array(r['fit']),outer,train,out,'matched'))
    candidates={};testpred={}
    # Same participant algorithms, nested strictly inside the outer development set.
    for tag in ['lgb','tabpfn_adme_pretrain','tabpfn_chemeleon']:
        features=X if tag=='lgb' else np.load(CACHE/(tag.replace('tabpfn_','')+'.npy'))
        oof=np.full((len(dev),4),np.nan)
        for f in range(5):
            tr=dev[folds!=f];va=dev[folds==f]
            pred=lgbfit(features,tr,va,train) if tag=='lgb' else tabfit(features,tr,va,train,out,f'{tag}/inner{f}')
            oof[folds==f]=pred
        final=lgbfit(features,dev,outer,train,out,'full') if tag=='lgb' else tabfit(features,dev,outer,train,out,tag+'/final')
        candidates[tag]=oof;testpred[tag]=final;savepred(out,tag+'_inner_oof',train.iloc[dev].Molecule_Name.to_numpy(),oof);savepred(out,tag,train.iloc[outer].Molecule_Name.to_numpy(),final)
        print('COMPONENT_COMPLETE',name,tag,flush=True)
    oof=np.full((len(dev),4),np.nan)
    for f in range(5):
        tridx=dev[~np.isin(folds,[f,(f+1)%5])];vidx=dev[folds==(f+1)%5];tidx=dev[folds==f]
        assert set(tridx).isdisjoint(tidx) and set(vidx).isdisjoint(tidx)
        weights=compute_inverse_count_task_weights(train.iloc[tridx],PRIMARY)+[.3]*13
        tr=pd.concat([train.iloc[tridx],aux],ignore_index=True)
        oof[folds==f]=finetune(tr,train.iloc[vidx],train.iloc[tidx],out,f'inner{f}',weights)
        savepred(out,f'chemprop_inner{f}',train.iloc[tidx].Molecule_Name.to_numpy(),oof[folds==f])
    tridx=dev[folds!=4];vidx=dev[folds==4]
    weights=compute_inverse_count_task_weights(train.iloc[tridx],PRIMARY)+[.3]*13
    final=finetune(pd.concat([train.iloc[tridx],aux],ignore_index=True),train.iloc[vidx],train.iloc[outer],out,'final',weights)
    candidates['chemprop_multitask']=oof;testpred['chemprop_multitask']=final
    savepred(out,'chemprop_multitask_inner_oof',train.iloc[dev].Molecule_Name.to_numpy(),oof);savepred(out,'chemprop_multitask',train.iloc[outer].Molecule_Name.to_numpy(),final)
    ensemble_pred=np.empty_like(final);details={}
    # Outer labels intentionally not consulted by calibration/selection.
    for k,c in enumerate(PRIMARY):
        y=train.iloc[dev][c].to_numpy();m=np.isfinite(y)
        names=[];mat=[];tmat=[];placement={}
        for tag in candidates:
            p=candidates[tag][:,k];tp=testpred[tag][:,k]
            slope,intercept=fit_placement_correction(y[m],p[m]);placement[tag]=[slope,intercept]
            names += [tag+'_raw',tag+'_cal'];mat += [p,apply_placement_correction(p,slope,intercept)];tmat += [tp,apply_placement_correction(tp,slope,intercept)]
        mat=np.asarray(mat).T;tmat=np.asarray(tmat).T
        lo=train.iloc[dev][c+'_conf_low'].to_numpy()[m];hi=train.iloc[dev][c+'_conf_high'].to_numpy()[m]
        def score(yt,p):return isoform_st_rae(yt,p,lo,hi)
        weights=caruana_bagged_ensemble(mat[m],y[m],score,minimize=True)
        ensemble_pred[:,k]=tmat@weights
        details[c]={'candidate_names':names,'weights':weights.tolist(),'placement':placement,'inner_selection_score_optimistic':float(score(y[m],mat[m]@weights))}
    savepred(out,'jeremy_ensemble',train.iloc[outer].Molecule_Name.to_numpy(),ensemble_pred)
    (out/'ensemble-fitting.json').write_text(json.dumps(details,indent=2));(out/'complete.json').write_text(json.dumps({'status':'complete','name':name,'kind':'ensemble'}));print('ENSEMBLE_COMPLETE',name,flush=True)

def chemeleon(name):
    out=ROOT/'outputs'/name/'chemeleon';out.mkdir(parents=True,exist_ok=True)
    r=json.loads((CACHE/'roles.json').read_text())[name];train=pd.read_csv(CACHE/'challenge.csv')
    d=out/'data';d.mkdir(exist_ok=True)
    for role,file in [('fit','train'),('val','validation'),('test','holdout')]:train.iloc[r[role]].to_csv(d/(file+'.csv'),index=False)
    (d/'manifest.json').write_text(json.dumps({'sha256':{f:hashlib.sha256((d/f).read_bytes()).hexdigest() for f in ['train.csv','validation.csv','holdout.csv']}}))
    for f in ['config.json','modeling.py','official_scoring_functions.py','train_chemeleon.py']:shutil.copy2(ROOT/f,out/f)
    with (out/'train.log').open('w') as log:
        subprocess.run([sys.executable,'-u','train_chemeleon.py'],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
    (out/'complete.json').write_text(json.dumps({'status':'complete','name':name,'kind':'chemeleon'}));print('CHEMELEON_COMPLETE',name,flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('kind');ap.add_argument('name');a=ap.parse_args()
    if a.kind=='ensemble':ensemble(a.name)
    elif a.kind=='chemeleon':chemeleon(a.name)
    else:raise ValueError(a.kind)
