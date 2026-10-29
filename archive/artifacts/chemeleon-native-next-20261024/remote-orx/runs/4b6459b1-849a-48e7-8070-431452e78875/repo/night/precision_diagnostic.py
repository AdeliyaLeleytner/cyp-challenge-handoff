"""Bounded replay of one native CheMeleon fold; never a candidate training run."""
from pathlib import Path
import argparse, fcntl, json, math, os, signal, subprocess, sys, time, traceback
from unittest.mock import patch
import numpy as np
import pandas as pd
import torch
from lightning import pytorch as pl
from . import briford_native as native
from .chemeleon_native import CHECKPOINT_SHA


def safe(value):
    if isinstance(value, torch.Tensor):
        value = value.detach().cpu()
        return safe(value.item() if value.numel() == 1 else value.tolist())
    if isinstance(value, np.generic):return safe(value.item())
    if isinstance(value, np.ndarray):return safe(value.tolist())
    if isinstance(value, float) and not math.isfinite(value):
        return 'NaN' if math.isnan(value) else ('Infinity' if value > 0 else '-Infinity')
    if isinstance(value, dict):return {str(k):safe(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)):return [safe(x) for x in value]
    if isinstance(value, Path):return str(value)
    if isinstance(value, (str,int,float,bool)) or value is None:return value
    return str(value)


def finite_scalar(value):
    if value is None:return None
    return bool(torch.isfinite(value).all()) if torch.is_tensor(value) else bool(np.isfinite(value))


def snapshot(trainer):
    scaler = getattr(trainer.precision_plugin,'scaler',None)
    early = [c for c in trainer.callbacks if isinstance(c,pl.callbacks.EarlyStopping)]
    checkpoints = [c for c in trainer.callbacks if isinstance(c,pl.callbacks.ModelCheckpoint)]
    return safe({'epoch':trainer.current_epoch,'global_step':trainer.global_step,
        'val_loss':trainer.callback_metrics.get('val_loss'),
        'val_loss_finite':finite_scalar(trainer.callback_metrics.get('val_loss')),
        'callback_metrics':trainer.callback_metrics,'should_stop':trainer.should_stop,
        'state':{'fn':trainer.state.fn,'status':trainer.state.status},
        'lr':[g['lr'] for o in trainer.optimizers for g in o.param_groups],
        'early_stopping':[{'monitor':c.monitor,'check_finite':c.check_finite,
            'check_on_train_epoch_end':c._check_on_train_epoch_end,'state':c.state_dict()} for c in early],
        'scaler':None if scaler is None else scaler.state_dict(),
        'checkpoint':[{'monitor':c.monitor,'best_model_path':c.best_model_path,
            'best_model_score':c.best_model_score} for c in checkpoints]})


class Audit(pl.Callback):
    def __init__(self,directory,precision,stop_after_epoch):
        self.directory=Path(directory);self.precision=precision;self.stop_after_epoch=stop_after_epoch
        self.events=[];self.budget_stop=False;self.trainer_ref=None

    def emit(self,event,**payload):
        record=safe({'event':event,'precision':self.precision,**payload})
        self.events.append(record)
        native.save(self.directory/'audit.json',{'precision':self.precision,'events':self.events})
        print(json.dumps(record,allow_nan=False),flush=True)

    def bind_early_stopping(self,callback):
        original=callback._evaluate_stopping_criteria
        def traced(current):
            before=safe(callback.state_dict())
            should_stop,reason=original(current)  # exactly one native state transition
            self.emit('native_early_stopping_decision',
                epoch=None if self.trainer_ref is None else self.trainer_ref.current_epoch,
                current=current,current_finite=finite_scalar(current),
                should_stop=should_stop,reason=reason,before=before,after=callback.state_dict())
            return should_stop,reason
        callback._evaluate_stopping_criteria=traced

    def on_fit_start(self,trainer,pl_module):
        self.trainer_ref=trainer
        self.emit('fit_start',max_epochs=trainer.max_epochs,
            estimated_stepping_batches=trainer.estimated_stepping_batches,
            precision_plugin=type(trainer.precision_plugin).__name__,state=snapshot(trainer))

    def on_validation_end(self,trainer,pl_module):
        if not trainer.sanity_checking:self.emit('validation_end',state=snapshot(trainer))

    def on_train_epoch_end(self,trainer,pl_module):
        # Original EarlyStopping precedes this appended callback. The separate native
        # decision event records its result regardless of which hook it uses.
        self.emit('train_epoch_end_before_budget',state=snapshot(trainer))
        if trainer.current_epoch >= self.stop_after_epoch:
            self.budget_stop=True;trainer.should_stop=True
            self.emit('diagnostic_epoch_budget_stop',stop_after_epoch=self.stop_after_epoch,
                explanation='Bounded diagnostic stops here; Trainer.max_epochs and original LR schedule remain400.',
                state=snapshot(trainer))

    def on_fit_end(self,trainer,pl_module):
        nonfinite=[name for name,value in pl_module.state_dict().items()
                   if torch.is_tensor(value) and (value.is_floating_point() or value.is_complex())
                   and not bool(torch.isfinite(value).all())]
        self.emit('fit_end',state=snapshot(trainer),model_state_nonfinite_keys=nonfinite,
                  model_state_finite_before_checkpoint_restore=not nonfinite)

    def on_exception(self,trainer,pl_module,exception):
        self.emit('fit_exception',type=type(exception).__name__,message=str(exception),state=snapshot(trainer))


def worker(config,precision):
    directory=Path(config['output_dir'])/precision.replace('-','_')
    directory.mkdir(parents=True,exist_ok=True)
    if (directory/'report.json').exists():raise FileExistsError(directory/'report.json')
    prep=Path(config['prepared_dir']);member=config['member'];fold=config['fold']
    spec=json.loads((prep/f'{member}.json').read_text())
    assert spec['hyperparameters']['max_epochs']==400 and spec['hyperparameters']['patience']==40
    assert spec['hyperparameters']['max_lr']==.001 and spec['hyperparameters']['seed']==42
    assert spec['hyperparameters'].get('freeze_mpnn_epochs',0)==0
    assert native.sha(prep/f'{member}.csv')==spec['data_sha256']
    assert native.sha(spec['hyperparameters']['from_foundation'])==CHECKPOINT_SHA
    frame=pd.read_csv(prep/f'{member}.csv',float_precision='round_trip')
    split=spec['folds'][fold];targets=spec['targets'];y=frame[targets].to_numpy(np.float32)
    manifest=json.loads((prep/'manifest.json').read_text());assert manifest['source_sha256']==native.sources()
    core=native.runtime();torch.set_num_threads(4)
    if not torch.cuda.is_available():raise RuntimeError('Real diagnostic must run on GPU; CPU is allowed only in unit fixtures')
    if precision=='bf16-mixed' and not torch.cuda.is_bf16_supported():raise RuntimeError('GPU does not support bf16')
    fs=core.FoldSpec(hyperparameters=spec['hyperparameters'],task='regression',model_type='uq_regressor',
        smiles_column='smiles',n_targets=len(targets),target_columns=targets,
        task_weights=np.asarray(spec['hyperparameters']['task_weights'],np.float32),
        num_workers=2,concurrent=True,enable_progress_bar=False,verbose=True)
    audit=Audit(directory,precision,config['stop_after_epoch'])
    real_trainer=core.pl.Trainer;trainers=[]
    provenance={'member':member,'fold':fold,'precision':precision,'seed':42,'hyperparameters':spec['hyperparameters'],
        'spec_sha256':native.sha(prep/f'{member}.json'),'data_sha256':native.sha(prep/f'{member}.csv'),
        'foundation_sha256':CHECKPOINT_SHA,'native_sources':native.sources(),
        'diagnostic_source_sha256':native.sha(Path(__file__)),
        'train_rows':len(split['train']),'validation_rows':len(split['validation']),
        'bounded_after_epoch':config['stop_after_epoch'],'candidate':False,
        'cuda_name':torch.cuda.get_device_name(0),'torch':torch.__version__,'lightning':pl.__version__,
        'early_stopping_code_sha256':native.sha(Path(sys.modules[pl.callbacks.EarlyStopping.__module__].__file__))}
    native.save(directory/'provenance.json',provenance)

    def instrumented_trainer(**kwargs):
        assert kwargs['max_epochs']==400 and kwargs['precision']=='16-mixed'
        callbacks=list(kwargs['callbacks'])
        for callback in callbacks:
            if isinstance(callback,pl.callbacks.EarlyStopping):audit.bind_early_stopping(callback)
        # This is the sole treatment difference. No LR, horizon, model or loss change.
        kwargs['precision']=precision;kwargs['callbacks']=callbacks+[audit]
        trainer=real_trainer(**kwargs);trainers.append(trainer);audit.trainer_ref=trainer
        return trainer

    start=time.time();report={'status':'started',**provenance}
    try:
        with patch.object(core.pl,'Trainer',new=instrumented_trainer):
            model,predictions=core.train_chemprop_fold(fs,
                frame.iloc[split['train']].reset_index(drop=True),frame.iloc[split['validation']].reset_index(drop=True),
                y[split['train']],y[split['validation']],fold_idx=fold,checkpoint_dir=str(directory/'checkpoints'))
        report.update(status='native_call_completed',seconds=time.time()-start,
            predictions_shape=list(predictions.shape),predictions_finite=bool(np.isfinite(predictions).all()),
            model_parameters_finite=all(bool(torch.isfinite(p).all()) for p in model.parameters()),
            trainer_after_return=snapshot(trainers[-1]))
        pd.DataFrame(predictions,columns=targets).to_csv(directory/'diagnostic_only_validation_predictions.csv',index=False)
    except Exception as exc:
        report.update(status='native_call_exception',seconds=time.time()-start,exception_type=type(exc).__name__,exception_message=str(exc))
        (directory/'exception.txt').write_text(traceback.format_exc())
        raise
    finally:
        report['budget_stop_reached']=audit.budget_stop
        report['native_stopping_decisions']=[e for e in audit.events if e['event']=='native_early_stopping_decision']
        report['epoch_validation']=[e for e in audit.events if e['event']=='validation_end']
        report['fit_end_events']=[e for e in audit.events if e['event']=='fit_end']
        if trainers:report['trainer_final_snapshot']=snapshot(trainers[-1])
        native.save(directory/'report.json',safe(report))
        print(json.dumps(safe({'event':'bounded_precision_diagnostic_complete','precision':precision,
            'status':report['status'],'seconds':report.get('seconds'),'budget_stop_reached':audit.budget_stop,
            'native_stopping_decisions':report['native_stopping_decisions']}),allow_nan=False),flush=True)


def run(config):
    assert config['precisions']==['16-mixed','bf16-mixed'] and config['gpus']==[0,1]
    assert config['stop_after_epoch']==3 and config['member']=='2d6isoform6' and config['fold']==0
    out=Path(config['output_dir']);out.mkdir(parents=True,exist_ok=True);native.save(out/'config.json',config)
    processes=[];gpu_locks={}
    lock_root=Path('/workspace/cyp-repro/gpu-slots');lock_root.mkdir(parents=True,exist_ok=True)
    def cancelled(signum,frame):raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,cancelled);signal.signal(signal.SIGINT,cancelled)
    try:
        # Reserve both diagnostic slots before workers start; inherit each lock FD so
        # an unexpected coordinator death cannot expose a still-running GPU worker.
        for gpu in config['gpus']:
            handle=(lock_root/f'gpu-{gpu}.lock').open('a+')
            try:fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close();raise RuntimeError(f'Diagnostic GPU {gpu} is already reserved')
            gpu_locks[gpu]=handle
        print(json.dumps({'event':'precision_diagnostic_gpu_slots_reserved','gpus':config['gpus']}),flush=True)
        for gpu,precision in zip(config['gpus'],config['precisions']):
            log=(out/(precision.replace('-','_')+'.log')).open('a')
            process=subprocess.Popen([sys.executable,'-u','-m','night.precision_diagnostic','--worker',precision],
                env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu)),stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(gpu_locks[gpu].fileno(),))
            processes.append((process,log,precision))
        codes={}
        while len(codes)<len(processes):
            for process,log,precision in processes:
                if precision not in codes and process.poll() is not None:
                    codes[precision]=process.returncode;log.close()
            time.sleep(2)
    finally:
        active=[(p,l,n) for p,l,n in processes if p.poll() is None]
        for process,log,precision in active:
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        if active:time.sleep(3)
        for process,log,precision in active:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait();log.close()
        for handle in gpu_locks.values():
            fcntl.flock(handle.fileno(),fcntl.LOCK_UN);handle.close()
    reports={precision:json.loads((out/precision.replace('-','_')/'report.json').read_text())
             for precision in config['precisions'] if (out/precision.replace('-','_')/'report.json').exists()}
    native.save(out/'combined-report.json',{'candidate':False,'return_codes':codes,'reports':reports})
    print(json.dumps({'event':'precision_diagnostic_pair_finished','return_codes':codes,
        'report_paths':{k:str(out/k.replace('-','_')/'report.json') for k in reports}}),flush=True)
    if any(codes.values()) or len(reports)!=2:raise RuntimeError('A diagnostic worker failed; inspect saved report/exception')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker',choices=['16-mixed','bf16-mixed']);args=parser.parse_args()
    config=json.loads(Path('briford_config.json').read_text())
    worker(config,args.worker) if args.worker else run(config)
