"""Full-data refit of an already selected ST recipe. No selection or upload here.

Copy into night/fullfit_strae.py only on a new child of the selected winner.
"""
from pathlib import Path
import json, os, shutil, signal, subprocess, sys, time
import numpy as np
import pandas as pd
from . import briford_native as native
from . import gpu_slots
from .chemeleon_native import CHECKPOINT_SHA, ENCODER
from .strae_objective import MODE

APPROVED_ORIGINAL_INPUTS={
  "activity_validation.py": {
    "sha256": "276a53d7f22ff973aaf567e64d977202995e91ba3cef2bbdc4de71c13bdebcb2",
    "bytes": 3051
  },
  "official-test.csv": {
    "sha256": "a342f8444a8dcb531ca12f3685293f0bd6c36ae9073f491e44a9bc1cc4b741f9",
    "bytes": 44935
  },
  "prepared/2d6single.csv": {
    "sha256": "b155217ba8cd4a72365d6cb75780fa4b773466665d25db1ffae7f8b2f35abef8",
    "bytes": 465474
  },
  "prepared/2d6single.json": {
    "sha256": "a8a5139d96bbcb47fda8b73eeeba26beb01306533ebbe3ed336f84ec0e002fda",
    "bytes": 100205
  },
  "prepared/mtaux8.json": {
    "sha256": "e00111366d655ba164e6829f78b372808870b850efa0ddc7ee1f359c76033ee5",
    "bytes": 339695
  },
  "prepared/2d6isoform6.json": {
    "sha256": "b7e61ea738b0100ec69e738505921a6b7ffe764ba38d3850bb1dc72154506ea9",
    "bytes": 1690912
  },
  "prepared/2d6isoform6.csv": {
    "sha256": "0ed26a5d2a0fb301d364fff8055ac0ed468063f743e3413e73c1a9ff61a9e714",
    "bytes": 5033645
  },
  "prepared/union18.json": {
    "sha256": "8afff7b7d40dd448fc923b961863af76ea567f665080f7d82d468f4223d78d88",
    "bytes": 2322480
  },
  "prepared/complete.json": {
    "sha256": "12d541eabfd0cbe9a2de395d8152bfd02345a5522fc16ae8fde87194843e788e",
    "bytes": 116
  },
  "prepared/union18.csv": {
    "sha256": "6dfb2235d3ae61914b6cecc50a3ee4d30d735c3a63f117baa14ef8d9b1aa73d1",
    "bytes": 6125534
  },
  "prepared/manifest.json": {
    "sha256": "655d38c3f4ac7f1cf219ef715b6df9870ccc703562001894e3d46b117957a5e2",
    "bytes": 10058
  },
  "prepared/mtaux8.csv": {
    "sha256": "b12d50d94b815551659116331e54eafb7022b5813407729e1e58d66c8d31d6c6",
    "bytes": 1159728
  },
  "prepared/native_overlap_audit.json": {
    "sha256": "cfcec3be24e8ef473b7b15d95f0155512e293a68135679d65592d45bb36ffa76",
    "bytes": 218
  }
}

ORIGINAL_FULL_MANIFEST_SHA256='655d38c3f4ac7f1cf219ef715b6df9870ccc703562001894e3d46b117957a5e2'
ORIGINAL_TEST_SHA256='a342f8444a8dcb531ca12f3685293f0bd6c36ae9073f491e44a9bc1cc4b741f9'


def _copy_unchanged(source,target):
    if target.exists():
        if native.sha(source)!=native.sha(target):raise ValueError(f'Existing refit input differs: {target}')
    else:shutil.copy2(source,target)


def _save_unchanged(path,value):
    if path.exists():
        if json.loads(path.read_text())!=value:raise ValueError(f'Existing refit specification differs: {path}')
    else:native.save(path,value)


def verify_inputs(config):
    assets=Path(config['assets']);original=assets/config['full_input_subdir']
    if not original.resolve().is_relative_to(assets.resolve()):raise ValueError('Full inputs must be inside assets')
    approved=json.loads(Path(config['input_manifest_path']).read_text())
    for relative,record in approved.items():
        path=assets/relative
        if not path.resolve().is_relative_to(assets.resolve()):raise ValueError('Unsafe manifest path')
        if path.stat().st_size!=record['bytes'] or native.sha(path)!=record['sha256']:
            raise ValueError(f'Original refit asset hash mismatch: {relative}')
    # Independent immutable hashes from the original source commit also prevent an
    # accidentally stale bootstrap manifest from weakening original-input verification.
    for relative,record in APPROVED_ORIGINAL_INPUTS.items():
        path=original/relative
        if path.stat().st_size!=record['bytes'] or native.sha(path)!=record['sha256']:
            raise ValueError(f'Approved original full-data input changed: {relative}')
    prep=original/'prepared'
    if native.sha(prep/'manifest.json')!=ORIGINAL_FULL_MANIFEST_SHA256:raise ValueError('Not the approved original full-data manifest')
    manifest=json.loads((prep/'manifest.json').read_text())
    if manifest['source_sha256']!=native.sources():raise ValueError('Original vendor source differs')
    for filename,digest in manifest['raw_sha256'].items():
        if native.sha(original/'raw'/filename)!=digest:raise ValueError(f'Original raw source changed: {filename}')
    query=original/'official-test.csv'
    if native.sha(query)!=ORIGINAL_TEST_SHA256:raise ValueError('Original structure-only TEST file changed')
    test=pd.read_csv(query)
    if set(test.columns)!={'Molecule_Name','SMILES'} or len(test)!=750 or test.Molecule_Name.isna().any() or test.Molecule_Name.duplicated().any() or test.SMILES.isna().any():
        raise ValueError('TEST must contain exactly750 unique IDs and SMILES, with no target-label columns')
    summary={}
    for member in native.MODELS:
        spec=json.loads((prep/f'{member}.json').read_text())
        if native.sha(prep/f'{member}.csv')!=spec['data_sha256']:raise ValueError(f'Original full table changed: {member}')
        frame=pd.read_csv(prep/f'{member}.csv',float_precision='round_trip')
        if len(frame)!=spec['rows'] or frame.molecule_name.duplicated().any():raise ValueError(f'Row identity problem: {member}')
        primary=[t for t in spec['targets'] if t in native.PRIMARY]
        for target in primary:
            observed=frame[target].notna()
            bounds=frame.loc[observed,[target+'_ci_lower',target+'_ci_upper']].to_numpy(float)
            if not np.isfinite(bounds).all() or np.any(bounds[:,0]>bounds[:,1]):raise ValueError(f'Invalid observed CI: {member}/{target}')
        validations=[]
        if len(spec['folds'])!=5:raise ValueError(f'Expected original five folds: {member}')
        for fold in spec['folds']:
            train,validation=fold['train'],fold['validation']
            if len(set(train))!=len(train) or len(set(validation))!=len(validation) or set(train)&set(validation) or set(train)|set(validation)!=set(range(len(frame))):
                raise ValueError(f'Invalid original fold partition: {member}')
            validations.extend(validation)
        if sorted(validations)!=list(range(len(frame))):raise ValueError(f'Original OOF coverage differs: {member}')
        summary[member]={'rows':len(frame),'targets':len(spec['targets']),'primary_ci_columns_present':True,
                         'original_data_sha256':spec['data_sha256'],'original_spec_sha256':native.sha(prep/f'{member}.json')}
    return original,manifest,{'input_files_verified':len(approved),'raw_source_files_verified':len(manifest['raw_sha256']),
        'test_rows':750,'test_columns':test.columns.tolist(),'hidden_test_labels_read':False,'members':summary}


def prepare(config):
    initialization=config.get('initialization')
    if initialization not in {'scratch','chemeleon'}:raise ValueError('Initialization remains unresolved until root selects the qualifying recipe')
    if config.get('selection_confirmed_by_root') is not True or not config.get('selected_recipe_commit') or not config.get('selection_evidence'):
        raise ValueError('Root must record the qualifying selected recipe and evidence before full-data refit')
    if config.get('criterion_mode')!=MODE or config.get('training_precision')!='bf16-mixed':
        raise ValueError('This adapter is only for the selected exact-ST/BF16/FP32-validation recipe')
    original,manifest,audit=verify_inputs(config)
    output=Path(config['output_dir']);prep=output/'prepared';prep.mkdir(parents=True,exist_ok=True)
    _copy_unchanged(original/'official-test.csv',output/'official-test.csv')
    _save_unchanged(output/'resolved-fullfit-config.json',config)
    _save_unchanged(output/'full-input-audit.json',audit)
    models={}
    for member in native.MODELS:
        source=original/'prepared';spec=json.loads((source/f'{member}.json').read_text())
        _copy_unchanged(source/f'{member}.csv',prep/f'{member}.csv')
        hp=spec['hyperparameters'];hp['criterion_mode']=MODE;hp['training_precision']='bf16-mixed'
        if initialization=='chemeleon':
            checkpoint=Path(config['assets'])/'weights/chemeleon_mp.pt'
            if native.sha(checkpoint)!=CHECKPOINT_SHA:raise ValueError('Selected foundation checkpoint changed')
            hp.update(from_foundation=str(checkpoint),hidden_dim=2048,depth=6)
            spec['foundation']={'checkpoint_sha256':CHECKPOINT_SHA,'effective_encoder':ENCODER,'fixed_ffn_dropout':hp['dropout']}
        elif hp.get('from_foundation'):
            raise ValueError('Original scratch specification unexpectedly contains pretrained initialization')
        # Full-source native task weights are intentionally retained. Outer-holdout
        # weights are not copied; fit-specific D/sigma/n are computed by ST trainer.
        spec['loss_design']={'mode':MODE,'normalizers':'inner-fit only','checkpoint_monitor':'val_primary_strae',
            'auxiliary_rule':'native_aux_weight/sum_native_primary_weights times per-auxiliary-head observed-label mean',
            'training_precision':'bf16-mixed','validation_precision':'explicit_fp32','smooth_or_center_penalty':False}
        _save_unchanged(prep/f'{member}.json',spec);models[member]={k:v for k,v in spec.items() if k!='folds'}
    _save_unchanged(prep/'manifest.json',{**manifest,'models':models,'criterion_mode':MODE,'initialization':initialization,
        'original_full_manifest_sha256':ORIGINAL_FULL_MANIFEST_SHA256,'selected_recipe_commit':config['selected_recipe_commit'],
        'scope':'full-source refit; native original full-pool scaffold folds; TEST inputs are IDs/SMILES only'})
    cfg={'phase':'train','prepared_dir':str(prep),'output_dir':str(output/'results'),'official_test':str(output/'official-test.csv'),
         'validator_path':str(original/'activity_validation.py'),
         'known_limits':['Full-source refit of a previously selected ST recipe; no new method selection occurs here.',
             'Original public data joins and documented public Veith TEST overlap are retained; no hidden challenge labels are read.',
             'Original full-pool folds and full-source native nominal task weights are retained; fold-specific ST statistics are refitted.',
             'Published native placement is applied after raw member averaging; it uses public leaderboard-derived constants.',
             'This module creates a candidate CSV but never uploads it.']}
    _save_unchanged(output/'native-assembly-config.json',cfg)
    return cfg


def run(config):
    cfg=prepare(config);output=Path(config['output_dir']);jobs=[];running={}
    for member in ['union18','2d6isoform6','mtaux8','2d6single']:
        for fold in range(5):
            directory=Path(cfg['output_dir'])/member/f'fold{fold}';directory.mkdir(parents=True,exist_ok=True)
            job={'member':member,'fold':fold,'prepared_dir':cfg['prepared_dir'],'output_dir':str(directory),'official_test':cfg['official_test']}
            _save_unchanged(directory/'job.json',job)
            if (directory/'complete.json').exists():
                done=json.loads((directory/'complete.json').read_text())
                if done['job_identity']!=native.job_identity(job):raise ValueError('Completed fullfit fold source/data/spec differs')
                for filename,digest in done['files'].items():
                    if native.sha(directory/filename)!=digest:raise ValueError('Completed fullfit fold file changed')
            else:jobs.append(directory/'job.json')
    def cancelled(signum,frame):raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,cancelled);signal.signal(signal.SIGINT,cancelled)
    print(json.dumps({'event':'selected_strae_fullfit_start','initialization':config['initialization'],
        'selected_recipe_commit':config['selected_recipe_commit'],'models_pending':len(jobs),'total_models':20,
        'hidden_test_labels_read':False}),flush=True)
    try:
        while jobs or running:
            for gpu in config['gpus']:
                if gpu not in running and jobs:
                    lease=gpu_slots.acquire(gpu)
                    if lease is None:continue
                    job=jobs[0];log=(job.parent/'worker.log').open('a')
                    try:
                        process=subprocess.Popen([sys.executable,'-u','-m','night.briford_native','--worker',str(job)],
                            env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu)),stdout=log,stderr=subprocess.STDOUT,
                            start_new_session=True,pass_fds=(lease.fileno(),))
                    except BaseException:
                        log.close();gpu_slots.release(lease);raise
                    jobs.pop(0);running[gpu]=(process,log,job,lease)
                    print(json.dumps({'event':'fullfit_fold_start','gpu':gpu,'job':str(job)}),flush=True)
            for gpu,(process,log,job,lease) in list(running.items()):
                code=process.poll()
                if code is None:continue
                if code:raise RuntimeError(f'Fullfit worker failed exit={code}: {job}')
                log.close();gpu_slots.release(lease);del running[gpu]
                print(json.dumps({'event':'fullfit_fold_complete','gpu':gpu,'job':str(job),'remaining':len(jobs)+len(running)}),flush=True)
            time.sleep(2)
    finally:
        for process,log,job,lease in running.values():
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        if running:time.sleep(3)
        for process,log,job,lease in running.values():
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait();log.close();gpu_slots.release(lease)
    for member in native.MODELS:
        for fold in range(5):
            directory=Path(cfg['output_dir'])/member/f'fold{fold}'
            job=json.loads((directory/'job.json').read_text());done=json.loads((directory/'complete.json').read_text())
            if done['job_identity']!=native.job_identity(job):raise ValueError('Fullfit fold identity mismatch at assembly')
    native.collect(cfg)
    final=json.loads((Path(cfg['output_dir'])/'final_complete.json').read_text())
    if final['model_count']!=20:raise ValueError('Expected20 fullfit models')
    if native.sha(final['submission_csv'])!=final['submission_sha256']:raise ValueError('Generated final CSV hash differs')
    result={'status':'complete','models':20,'initialization':config['initialization'],'criterion_mode':MODE,
        'training_precision':'bf16-mixed','validation_precision':'explicit_fp32',
        'selected_recipe_commit':config['selected_recipe_commit'],'selection_evidence':config['selection_evidence'],
        'original_full_manifest_sha256':ORIGINAL_FULL_MANIFEST_SHA256,'original_test_sha256':ORIGINAL_TEST_SHA256,
        'hidden_test_labels_read':False,'uploaded':False,'native_final_completion':final}
    native.save(output/'fullfit_complete.json',result)
    print(json.dumps({'event':'selected_strae_fullfit_complete','models':20,'submission_csv':final['submission_csv'],
        'submission_sha256':final['submission_sha256'],'uploaded':False}),flush=True)

if __name__=='__main__':run(json.loads(Path('briford_config.json').read_text()))
