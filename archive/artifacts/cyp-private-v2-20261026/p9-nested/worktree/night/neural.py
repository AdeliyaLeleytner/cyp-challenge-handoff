"""One train-only Chemprop fit; the caller owns cohorts, folds, and ensembles."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import numpy as np
import pandas as pd
from .reference import (DEFAULTS, CANONICAL, DIRECT, build_component_data,
                        prepare_validation_data, _standard)

CHEMELEON_SHA256 = 'c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651'
CHEMELEON_DEFAULTS = dict(DEFAULTS, dropout=0., ffn_num_layers=1,
                         batch_norm=False, aggregation='mean', loss='mse',
                         max_epochs=60, min_epochs=20, patience=10)

def _digest_ids(df):
    return hashlib.sha256(('\n'.join(df.Molecule_Name.astype(str))+'\n').encode()).hexdigest()

def _bound_arrays(frame, targets, fallback=False):
    """Intervals are target uncertainty, not prediction uncertainty or extra labels."""
    center = frame[targets].to_numpy(np.float32)
    low, high = center.copy(), center.copy()
    for j,t in enumerate(targets):
        if t not in DIRECT: continue  # Auxiliary measurements remain point targets.
        lc,hc = t+'_ci_lower',t+'_ci_upper'
        if lc not in frame or hc not in frame:
            if fallback: continue
            raise ValueError(f'Interval loss needs both confidence bounds for {t}')
        labelled = np.isfinite(center[:,j])
        l,h = frame[lc].to_numpy(float),frame[hc].to_numpy(float)
        valid = np.isfinite(l)&np.isfinite(h)&(l<=h)
        if (labelled & ~valid).any() and not fallback:
            raise ValueError(f'{int((labelled & ~valid).sum())} labelled {t} rows lack valid intervals')
        use = labelled & valid
        low[use,j],high[use,j] = l[use],h[use]
    return center,low,high

def interval_distance(prediction, low, high):
    """Differentiable interval MAE, usable directly by a tiny synthetic smoke test."""
    import torch
    return torch.relu(low-prediction)+torch.relu(prediction-high)

def _interval_model_type():
    import torch
    from chemprop.models import MPNN
    class IntervalMPNN(MPNN):
        # Dataset targets are [central, lower, upper], each with T entries.
        # Scaling is fit to train central labels only, and shared with both bounds.
        def _parts(self,batch):
            bmg,V_d,X_d,y,weights,*_ = batch
            n = self.n_tasks
            mask = y[:,:n].isfinite()
            low,high = y[:,n:2*n].nan_to_num(),y[:,2*n:].nan_to_num()
            pred = self.predictor.train_step(self.fingerprint(bmg,V_d,X_d))
            loss = interval_distance(pred,low,high)
            numerator = (loss*mask*weights.view(-1,1)*self.criterion.task_weights).sum()
            denominator = mask.sum()
            if denominator == 0: raise ValueError('Batch has no observed targets')
            return numerator,denominator
        def training_step(self,batch,batch_idx):
            numerator,denominator = self._parts(batch)
            loss = numerator/denominator
            self.log('train_loss',loss,on_step=False,on_epoch=True,batch_size=int(denominator))
            return loss
        def on_validation_epoch_start(self):
            self._val_num = torch.zeros((),device=self.device)
            self._val_den = torch.zeros((),device=self.device)
        def validation_step(self,batch,batch_idx=0):
            numerator,denominator = self._parts(batch)
            self._val_num += numerator.detach()
            self._val_den += denominator.detach()
        def on_validation_epoch_end(self):
            if self._val_den == 0: raise ValueError('Validation has no observed targets')
            self.log('val_loss',self._val_num/self._val_den,prog_bar=True)
    return IntervalMPNN

def run_trial(config, train_df, query_df, asset_root, output_dir, validation_df=None):
    import torch
    from lightning import pytorch as pl
    from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint, Callback
    from lightning.pytorch.loggers import CSVLogger
    from torch.utils.data import DataLoader
    from sklearn.preprocessing import StandardScaler
    from rdkit import Chem
    from chemprop import data, featurizers, nn, models
    from chemprop.data.collate import collate_batch

    cfg = dict(config)
    initialization = cfg.get('initialization','scratch')
    if initialization not in {'scratch','chemeleon'}: raise ValueError('Unknown initialization')
    effective = dict(CHEMELEON_DEFAULTS if initialization=='chemeleon' else DEFAULTS)
    effective.update(cfg)
    cfg = effective
    component = cfg.get('component','direct')
    out = Path(output_dir)
    out.mkdir(parents=True,exist_ok=True)
    if (out/'complete.json').exists(): raise FileExistsError('Completed trial directory must not be overwritten')
    if validation_df is None or len(validation_df)==0:
        raise ValueError('validation_df is required; no outer-label or training-loss epoch selection')
    for name,frame in [('train',train_df),('query',query_df),('validation',validation_df)]:
        if frame.Molecule_Name.isna().any() or frame.Molecule_Name.duplicated().any():
            raise ValueError(f'Invalid/duplicate IDs in {name}')
        if frame.SMILES.isna().any(): raise ValueError(f'Null SMILES in {name}')
    if set(train_df.Molecule_Name)&set(query_df.Molecule_Name): raise ValueError('Training/query ID overlap')
    if set(train_df.Molecule_Name)&set(validation_df.Molecule_Name): raise ValueError('Training/validation ID overlap')
    prepared = build_component_data(component,train_df,asset_root,cfg,cfg.get('excluded_parent_keys'))
    td = prepared.train_df
    targets = prepared.target_columns
    vd = prepare_validation_data(component,validation_df,asset_root,cfg,targets)
    # No external or side-only observations are introduced into the validation set.
    vd = vd[vd[targets].notna().any(axis=1)].reset_index(drop=True)
    if len(vd)==0: raise ValueError('Validation has no observed component labels')
    if set(td.Molecule_Name)&set(query_df.Molecule_Name): raise ValueError('Augmented training/query ID overlap')
    if set(td.Molecule_Name)&set(vd.Molecule_Name): raise ValueError('Augmented training/validation ID overlap')
    for name,frame in [('fit',td),('validation',vd),('query',query_df)]:
        invalid = [str(row.Molecule_Name) for row in frame.itertuples() if Chem.MolFromSmiles(row.SMILES) is None]
        if invalid: raise ValueError(f'Invalid {name} SMILES, IDs: {invalid[:20]}')
    if len(td)<2: raise ValueError('At least two fit rows required')
    seed = int(cfg['seed'])+int(cfg.get('fold_index',0))
    pl.seed_everything(seed,workers=True)
    if cfg.get('torch_num_threads'): torch.set_num_threads(int(cfg['torch_num_threads']))
    scaler = StandardScaler().fit(td[targets].to_numpy(np.float32))
    if not np.isfinite(scaler.mean_).all() or not np.isfinite(scaler.scale_).all():
        raise ValueError('Nonfinite train-only scaler')
    loss_name = cfg['loss'].lower()
    if loss_name not in {'mae','mse','interval_mae'}: raise ValueError('Unknown loss')
    interval = loss_name=='interval_mae'
    feat = featurizers.SimpleMoleculeMolGraphFeaturizer()
    def make(frame,prediction=False):
        if prediction:
            y = np.full((len(frame),len(targets)*(3 if interval else 1)),np.nan,dtype=np.float32)
        elif interval:
            arrays = _bound_arrays(frame,targets,cfg.get('interval_point_fallback',False))
            y = np.concatenate([scaler.transform(a) for a in arrays],axis=1).astype(np.float32)
        else: y = scaler.transform(frame[targets].to_numpy(np.float32)).astype(np.float32)
        dataset = data.MoleculeDataset([data.MoleculeDatapoint.from_smi(s,v) for s,v in zip(frame.SMILES,y)],feat)
        dataset.cache = True
        return dataset
    train_set,valid_set,query_set = make(td),make(vd),make(query_df,True)
    batch_size = int(cfg['batch_size'])
    if batch_size<2: raise ValueError('batch_size must be >=2')
    # Chemprop internally drops a singleton final train batch for BatchNorm safety.
    train_loader = data.build_dataloader(train_set,batch_size=batch_size,num_workers=int(cfg.get('num_workers',0)),shuffle=True,seed=seed)
    def inference_loader(dataset):
        return DataLoader(dataset,batch_size=batch_size,num_workers=int(cfg.get('num_workers',0)),shuffle=False,drop_last=False,collate_fn=collate_batch)
    valid_loader,query_loader = inference_loader(valid_set),inference_loader(query_set)
    initialization_meta = {'initialization':initialization}
    if initialization=='chemeleon':
        checkpoint = Path(cfg.get('checkpoint_path',Path(asset_root)/'weights/chemeleon_mp.pt'))
        actual_sha = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        expected_sha = cfg.get('checkpoint_sha256',CHEMELEON_SHA256)
        if actual_sha != expected_sha: raise ValueError('Foundation checkpoint SHA256 mismatch')
        ck = torch.load(checkpoint,weights_only=True,map_location='cpu')
        mp = nn.BondMessagePassing(**ck['hyper_parameters'])
        mp.load_state_dict(ck['state_dict'],strict=True)
        initialization_meta.update(checkpoint_sha256=actual_sha,checkpoint_path=str(checkpoint),
            encoder_hyperparameters={k:v for k,v in ck['hyper_parameters'].items() if isinstance(v,(str,int,float,bool,type(None)))})
    else:
        mp = nn.BondMessagePassing(d_h=int(cfg['hidden_dim']),depth=int(cfg['depth']),dropout=float(cfg['dropout']))
    aggregate = {'norm':nn.NormAggregation,'mean':nn.MeanAggregation,'sum':nn.SumAggregation}
    if cfg['aggregation'] not in aggregate: raise ValueError('Unknown aggregation')
    criterion_cls = nn.metrics.MSE if loss_name=='mse' else nn.metrics.MAE
    criterion = criterion_cls(task_weights=prepared.task_weights)
    ffn = nn.RegressionFFN(n_tasks=len(targets),input_dim=mp.output_dim,
        hidden_dim=int(cfg['ffn_hidden_dim']),n_layers=int(cfg['ffn_num_layers']),
        dropout=float(cfg['dropout']),criterion=criterion,
        output_transform=nn.UnscaleTransform.from_standard_scaler(scaler))
    model_cls = _interval_model_type() if interval else models.MPNN
    model = model_cls(mp,aggregate[cfg['aggregation']](),ffn,batch_norm=bool(cfg['batch_norm']),
        warmup_epochs=int(cfg['warmup_epochs']),init_lr=float(cfg['init_lr']),
        max_lr=float(cfg['max_lr']),final_lr=float(cfg['final_lr']))
    class History(Callback):
        def __init__(self): self.rows=[]
        def on_validation_end(self,trainer,pl_module):
            if trainer.sanity_checking: return
            self.rows.append({'epoch':trainer.current_epoch,**{k:float(v.detach().cpu()) for k,v in trainer.callback_metrics.items() if torch.is_tensor(v) and v.numel()==1}})
    history = History()
    checkpoint_callback = ModelCheckpoint(dirpath=out/'checkpoints',filename='best',monitor='val_loss',mode='min',save_top_k=1,save_last=False,save_weights_only=True)
    stopping = EarlyStopping(monitor='val_loss',mode='min',patience=int(cfg['patience']),check_finite=True)
    accelerator = cfg.get('accelerator','gpu' if torch.cuda.is_available() else 'cpu')
    precision = cfg.get('precision','16-mixed' if accelerator in {'gpu','cuda'} else '32-true')
    metadata = dict(component=prepared.metadata,initialization=initialization_meta,
        effective_config={k:v for k,v in cfg.items() if k!='excluded_parent_keys'},
        excluded_parent_keys_count=len(cfg.get('excluded_parent_keys',[])),
        target_order=targets,output_mapping=prepared.primary_mapping,
        supplied_train_id_sha256=_digest_ids(train_df),fit_id_sha256=_digest_ids(td),
        validation_id_sha256=_digest_ids(vd),query_id_sha256=_digest_ids(query_df),
        validation_query_overlap=len(set(vd.Molecule_Name)&set(query_df.Molecule_Name)),
        query_labels_used=False,scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),
        accelerator=accelerator,precision=precision,seed=seed,
        packages={p:importlib.metadata.version(p) for p in ['torch','chemprop','lightning','rdkit','numpy','pandas']})
    (out/'trial_metadata.json').write_text(json.dumps(metadata,indent=2,default=str))
    td[['Molecule_Name']].to_csv(out/'fit_ids.csv',index=False)
    vd[['Molecule_Name']].to_csv(out/'validation_ids.csv',index=False)
    trainer = pl.Trainer(accelerator=accelerator,devices=1,precision=precision,
        max_epochs=int(cfg['max_epochs']),min_epochs=int(cfg.get('min_epochs',0)),
        callbacks=[checkpoint_callback,stopping,history],logger=CSVLogger(str(out),name='logs'),
        enable_progress_bar=bool(cfg.get('progress_bar',False)),enable_model_summary=False,
        deterministic=bool(cfg.get('deterministic',False)),num_sanity_val_steps=0)
    trainer.fit(model,train_loader,valid_loader)
    best = checkpoint_callback.best_model_path
    if not best: raise RuntimeError('No best-validation checkpoint was saved')
    # This checkpoint was just written by this fit; load only its state into the same architecture.
    saved = torch.load(best,map_location='cpu',weights_only=False)
    model.load_state_dict(saved['state_dict'],strict=True)
    predictions = torch.cat(trainer.predict(model,dataloaders=query_loader),dim=0).cpu().numpy()
    if predictions.shape != (len(query_df),len(targets)) or not np.isfinite(predictions).all():
        raise RuntimeError('Nonfinite or misaligned predictions')
    auxiliary = pd.DataFrame(predictions,columns=targets)
    auxiliary.insert(0,'Molecule_Name',query_df.Molecule_Name.to_numpy())
    auxiliary.to_csv(out/'all_head_predictions.csv',index=False)
    result = auxiliary[['Molecule_Name']+list(prepared.primary_mapping)].rename(columns=prepared.primary_mapping)
    requested = cfg.get('targets',[t for t in CANONICAL if t in result])
    if not set(requested)<=set(result): raise ValueError('Requested targets absent from component')
    result = result[['Molecule_Name']+list(requested)]
    result.to_csv(out/'predictions.csv',index=False)
    pd.DataFrame(history.rows).to_csv(out/'epoch_history.csv',index=False)
    metadata.update(best_epoch=int(saved['epoch']),best_val_loss=float(checkpoint_callback.best_model_score),
                    elapsed_epochs=int(trainer.current_epoch),best_checkpoint=best,
                    trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad))
    (out/'trial_metadata.json').write_text(json.dumps(metadata,indent=2,default=str))
    (out/'complete.json').write_text(json.dumps({'status':'complete','rows':len(result),'targets':requested,'best_epoch':metadata['best_epoch']}))
    return result
