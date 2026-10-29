"""All-endpoint ADMETlab descriptors added to the frozen native scratch-MAE recipe."""
from pathlib import Path
import argparse,json,os,signal,subprocess,sys,time,shutil
import numpy as np
import pandas as pd
from . import briford_native as native
from . import gpu_slots
from .admet_feature_contract import verify_ready
from .admet_features import AdmetFeatureCache,prepare_fold_descriptors,build_with_zero_extended_fresh_head
from .briford_holdouts import score


def write_json_once(path,value):
    path=Path(path)
    if path.exists():
        if json.loads(path.read_text())!=value:raise ValueError('Existing output belongs to another feature recipe: '+str(path))
    else:native.save(path,value)


def copy_verified(source,target,expected=None):
    source=Path(source);target=Path(target);digest=expected or native.sha(source)
    if target.exists():
        if native.sha(target)!=digest:raise ValueError('Existing snapshot differs: '+str(target))
    else:target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    if native.sha(target)!=digest or native.sha(source)!=digest:raise ValueError('Input changed during snapshot copy: '+str(source))


def prepare(config):
    ready=verify_ready(config);assets=Path(config['assets']);out=Path(config['output_dir'])
    if config['initialization']!='scratch':raise ValueError('Native scratch MAE is the declared first feature comparison')
    cohorts=config['cohorts']
    if cohorts!=['own750','briford529']:raise ValueError('Expected both frozen outer cohorts in fixed order')
    frozen_hashes={}
    for cohort in cohorts:
        src=assets/'frozen_holdouts'/cohort
        for file in src.rglob('*'):
            if file.is_file():frozen_hashes[str(file.relative_to(assets))]=native.sha(file)
    identity={'recipe_id':config['recipe_id'],'initialization':'scratch','loss':'native_mae',
              'source_sha256':native.sources(),
              'experiment_modules_sha256':{f.name:native.sha(f) for f in Path(__file__).parent.glob('*.py')},
              'feature_input_sha256':{k:ready['input_sha256'][k] for k in ['feature_table','feature_schema','id_map','queue']},
              'source_mode':ready['source_mode'],'backend':ready['backend'],'api_probe_vectors_used':False,
              'frozen_native_input_sha256':frozen_hashes,'control_scores_sha256':native.sha(assets/'control-scores.json')}
    out.mkdir(parents=True,exist_ok=True);write_json_once(out/'recipe-identity.json',identity)
    copy_verified(assets/'control-scores.json',out/'control-scores.json',identity['control_scores_sha256'])
    snapshot=out/'feature-inputs';snapshot.mkdir(exist_ok=True)
    names={'feature_table':'features.csv','feature_schema':'feature-schema.json','id_map':'id-map.csv','queue':'queue.csv',
           'complete':'source-complete.json','status':'source-status.json','pending':'source-missing-or-pending.csv','id_map_provenance':'source-id-map-provenance.json'}
    for key,name in names.items():copy_verified(ready['source_paths'][key],snapshot/name,ready['input_sha256'][key])
    write_json_once(snapshot/'readiness.json',ready)
    cache=AdmetFeatureCache.from_files(snapshot/'id-map.csv',snapshot/'features.csv',snapshot/'feature-schema.json',
            expected_sha256={k:ready['input_sha256'][k] for k in ['id_map','feature_table','feature_schema']})
    feature_spec={'feature_table':str(snapshot/'features.csv'),'feature_schema':str(snapshot/'feature-schema.json'),
                  'id_map':str(snapshot/'id-map.csv'),'input_sha256':cache.provenance['input_sha256'],
                  'feature_count':ready['feature_count'],'descriptor_count_with_missing_flags':2*ready['feature_count'],
                  'queue_sha256':config['queue_sha256'],'all_endpoint_columns':ready['feature_columns'],
                  'initialization':'paired_fresh_head_zero_descriptor_weights','teacher_training_membership':'unknown',
                  'source_mode':ready['source_mode'],'backend':ready['backend'],'api_probe_vectors_used':False}
    controls=json.loads((out/'control-scores.json').read_text());configs=[]
    for cohort in cohorts:
        source=assets/'frozen_holdouts'/cohort;root=out/cohort;prep=root/'prepared';prep.mkdir(parents=True,exist_ok=True)
        for name in ['truth.csv','query.csv','exclusion-audit.json']:copy_verified(source/name,root/name)
        query=pd.read_csv(root/'query.csv');truth=pd.read_csv(root/'truth.csv')
        if len(query)!=config['expected_holdout_rows'][cohort] or len(query)!=controls[cohort]['raw']['n_molecules']:
            raise ValueError('Holdout size does not match the declared native control: '+cohort)
        if query.Molecule_Name.tolist()!=truth.Molecule_Name.tolist():raise ValueError('Truth/query order mismatch')
        query_features=cache.align(query)
        manifest=json.loads((source/'prepared/manifest.json').read_text());assert manifest['source_sha256']==native.sources()
        models={};alignment={}
        for member in native.MODELS:
            old=json.loads((source/'prepared'/f'{member}.json').read_text())
            src=source/'prepared'/f'{member}.csv';assert native.sha(src)==old['data_sha256']
            assert manifest['outer_exclusion_audit'][member]['remaining_held_id_parent_or_connectivity_overlap']==0
            hp=old['hyperparameters']
            if hp.get('from_foundation') or hp['criterion']!='mae' or hp.get('bounded_loss',False):
                raise ValueError('Frozen control is not native scratch point-MAE: '+member)
            copy_verified(src,prep/f'{member}.csv',old['data_sha256'])
            df=pd.read_csv(src,float_precision='round_trip');aligned=cache.align(df)
            if set(aligned.request_ids)&set(query_features.request_ids):raise ValueError('Outer request-ID overlap: '+cohort+'/'+member)
            folds=old['folds']
            if len(folds)!=5:raise ValueError('Expected five native scaffold folds')
            for fold in folds:
                tr={aligned.request_ids[i] for i in fold['train']};va={aligned.request_ids[i] for i in fold['validation']}
                if tr&va:raise ValueError('Inner request-ID overlap: '+cohort+'/'+member)
            spec=json.loads(json.dumps(old));spec['admet_features']=feature_spec
            write_json_once(prep/f'{member}.json',spec);models[member]={k:v for k,v in spec.items() if k!='folds'}
            alignment[member]=aligned.audit()
        write_json_once(prep/'manifest.json',{**manifest,'models':models,'admet_features':feature_spec,
                      'frozen_control_manifest_sha256':native.sha(source/'prepared/manifest.json')})
        write_json_once(root/'feature-alignment-audit.json',{'members':alignment,'query':query_features.audit(),'preserved_native_rows_folds_and_hyperparameters':True})
        cfg={'phase':'train','prepared_dir':str(prep),'output_dir':str(root/'results'),'official_test':str(root/'query.csv'),
             'validator_path':str(assets/'activity_validation.py'),
             'known_limits':['Native scratch MAE champion plus every manifested ADMETlab numeric feature. This is not the CheMeleon feature arm.',
                             'External teacher historical training membership unknown; local exclusions do not establish end-to-end label independence.',
                             'Native published placement targets real contest TEST, not these local outer cohorts.']}
        write_json_once(root/'config.json',cfg);configs.append(cfg)
    write_json_once(out/'input-comparison.json',{'feature_input':feature_spec,'control_scores':controls,'all_local_coverage_checks_passed':True})
    print(json.dumps({'event':'admet_feature_inputs_verified','recipe':config['recipe_id'],'initialization':'scratch','feature_count':ready['feature_count'],'descriptors_with_flags':2*ready['feature_count'],'cohorts':cohorts,'external_teacher_membership':'unknown'}),flush=True)
    return configs


def feature_cache(spec):
    source=spec['admet_features']
    expected={'source_mode':'web_default','backend':'documented_web_batch','api_probe_vectors_used':False}
    if any(source.get(k)!=v for k,v in expected.items()):raise ValueError('Worker specification is not the declared web_default regime')
    cache=AdmetFeatureCache.from_files(source['id_map'],source['feature_table'],source['feature_schema'],expected_sha256=source['input_sha256'])
    if cache.provenance.get('service_regime')!=expected:raise ValueError('Worker cache schema mixes or omits prediction regime provenance')
    return cache


def worker(jobpath):
    import torch,importlib.metadata
    job=json.loads(Path(jobpath).read_text());prep=Path(job['prepared_dir']);out=Path(job['output_dir']);out.mkdir(parents=True,exist_ok=True)
    if not torch.cuda.is_available():raise RuntimeError('ADMET feature training requires its leased CUDA GPU; CPU fallback is disabled')
    if (out/'complete.json').exists():raise FileExistsError(out)
    manifest=json.loads((prep/'manifest.json').read_text());assert native.sources()==manifest['source_sha256']
    member=job['member'];spec=json.loads((prep/f'{member}.json').read_text());assert native.sha(prep/f'{member}.csv')==spec['data_sha256']
    assert not spec['hyperparameters'].get('from_foundation') and spec['hyperparameters']['criterion']=='mae'
    df=pd.read_csv(prep/f'{member}.csv',float_precision='round_trip');fold=spec['folds'][job['fold']];targets=spec['targets'];y=df[targets].to_numpy(dtype=np.float32)
    tr=df.iloc[fold['train']].reset_index(drop=True);va=df.iloc[fold['validation']].reset_index(drop=True)
    query=pd.read_csv(job['official_test']).rename(columns={'Molecule_Name':'molecule_name','SMILES':'smiles'})
    descriptors=prepare_fold_descriptors(feature_cache(spec),tr,va,query)
    native.save(out/'admet-feature-audit.json',descriptors.audit)
    native.save(out/'admet-imputer.json',descriptors.imputer.to_dict())
    core=native.runtime();torch.set_num_threads(4)
    original_builder=core.build_mpnn_model
    def feature_builder(hp,**kwargs):
        model,note=build_with_zero_extended_fresh_head(original_builder,hp,**kwargs)
        model.admet_feature_initialization=note
        return model
    core.build_mpnn_model=feature_builder
    fs=core.FoldSpec(hyperparameters=spec['hyperparameters'],task='regression',model_type='uq_regressor',smiles_column='smiles',
            n_targets=len(targets),target_columns=targets,task_weights=np.asarray(spec['hyperparameters']['task_weights'],dtype=np.float32) if len(targets)>1 else None,
            num_workers=2,concurrent=True,enable_progress_bar=False,verbose=True)
    fs=descriptors.configure_spec(fs);started=time.time()
    model,valid=core.train_chemprop_fold(fs,tr,va,y[fold['train']],y[fold['validation']],fold_idx=job['fold'],
            checkpoint_dir=str(out/'checkpoints'),**descriptors.native_training_kwargs())
    pred=core.predict_chemprop_frame(model,fs,query,extra=descriptors.query.copy())
    assert valid.shape==(len(va),len(targets)) and pred.shape==(len(query),len(targets)) and np.isfinite(valid).all() and np.isfinite(pred).all()
    for label,ids,values in [('oof',va.molecule_name,valid),('test',query.molecule_name,pred)]:
        table=pd.DataFrame(values,columns=targets);table.insert(0,'molecule_name',list(ids));table.to_csv(out/f'{label}.csv',index=False,float_format='%.17g')
    checkpoints=list((out/'checkpoints').glob('*.ckpt'));assert len(checkpoints)==1
    checkpoint=torch.load(checkpoints[0],map_location='cpu',weights_only=False)
    native.save(out/'metadata.json',{'member':member,'fold':job['fold'],'seconds':time.time()-started,'best_epoch':checkpoint['epoch'],
            'initialization':'scratch','features':'all_admetlab_numeric','source_mode':'web_default','api_probe_vectors_used':False,'training_rows':len(tr),'validation_rows':len(va),
            'native_training_source':native.sha(native.VENDOR/'chemprop_core.py'),'model_hyperparameters':spec['hyperparameters'],
            'actual_encoder_output_dim':model.message_passing.output_dim,'actual_aggregation':type(model.agg).__name__,
            'actual_ffn_input_dim':model.predictor.input_dim,'n_extra_descriptors':descriptors.n_extra_descriptors,
            'feature_initialization':model.admet_feature_initialization,'feature_input_sha256':spec['admet_features']['input_sha256'],
            'external_teacher_training_membership':'unknown','packages':{n:importlib.metadata.version(n) for n in ['torch','chemprop','lightning','rdkit','numpy','pandas','scikit-learn']}})
    native.save(out/'complete.json',{'status':'complete','job_identity':native.job_identity(job),'source_sha256':native.sources(),
            'files':{str(f.relative_to(out)):native.sha(f) for f in out.rglob('*') if f.is_file() and f.name not in {'complete.json','worker.log'}}})
    print(json.dumps({'event':'admet_feature_fold_complete','member':member,'fold':job['fold'],'seconds':time.time()-started,'best_epoch':checkpoint['epoch']}),flush=True)


def run(config):
    configs=prepare(config);out=Path(config['output_dir']);jobs=[]
    if (out/'complete.json').exists():
        done=json.loads((out/'complete.json').read_text())
        for rel,digest in done['files'].items():assert native.sha(out/rel)==digest
        print(json.dumps({'event':'admet_feature_completed_recipe_verified','scores':done['scores']}),flush=True);return
    gpus=config['gpus']
    if not gpus or len(set(gpus))!=len(gpus) or any(not isinstance(g,int) or g<0 for g in gpus):raise ValueError('Invalid GPU slot list')
    for member in ['union18','2d6isoform6','mtaux8','2d6single']:
        for fold in range(5):
            for cfg in configs:
                directory=Path(cfg['output_dir'])/member/f'fold{fold}';directory.mkdir(parents=True,exist_ok=True)
                job={'member':member,'fold':fold,'prepared_dir':cfg['prepared_dir'],'output_dir':str(directory),'official_test':cfg['official_test']}
                write_json_once(directory/'job.json',job)
                if (directory/'complete.json').exists():
                    done=json.loads((directory/'complete.json').read_text());assert done['job_identity']==native.job_identity(job),'Completed fold belongs to a different recipe'
                    for rel,digest in done['files'].items():assert native.sha(directory/rel)==digest
                else:jobs.append(directory/'job.json')
    running={};last_wait_message=0.
    def cancelled(signum,frame):raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,cancelled);signal.signal(signal.SIGINT,cancelled)
    try:
        while jobs or running:
            for gpu in gpus:
                if gpu in running or not jobs:continue
                lease=gpu_slots.acquire(gpu)
                if lease is None:continue
                job=jobs.pop(0);log=(job.parent/'worker.log').open('a')
                try:
                    proc=subprocess.Popen([sys.executable,'-u','-m','night.admet_feature_runner','--worker',str(job)],
                        env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu)),stdout=log,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lease.fileno(),))
                except BaseException:log.close();gpu_slots.release(lease);raise
                running[gpu]=(proc,log,job,lease);print(json.dumps({'event':'admet_feature_fold_start','gpu':gpu,'job':str(job)}),flush=True)
            for gpu,(proc,log,job,lease) in list(running.items()):
                rc=proc.poll()
                if rc is None:continue
                if rc:raise RuntimeError(f'Feature worker failed exit={rc}: {job}')
                done=json.loads((job.parent/'complete.json').read_text());assert done['job_identity']==native.job_identity(json.loads(job.read_text()))
                log.close();gpu_slots.release(lease);del running[gpu]
                print(json.dumps({'event':'admet_feature_worker_complete','job':str(job),'remaining':len(jobs)+len(running)}),flush=True)
            if jobs and not running and time.time()-last_wait_message>30:
                print(json.dumps({'event':'admet_feature_waiting_for_shared_gpu_slots','pending':len(jobs)}),flush=True);last_wait_message=time.time()
            time.sleep(2)
    finally:
        for proc,log,job,lease in running.values():
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        if running:time.sleep(3)
        for proc,log,job,lease in running.values():
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            proc.wait();log.close();gpu_slots.release(lease)
    for cfg in configs:native.collect(cfg)
    score(config);results=json.loads((out/'scores.json').read_text());control=json.loads((out/'control-scores.json').read_text())
    comparison={cohort:{variant:{'feature_ST_RAE':values['macro_ST_RAE'],'control_ST_RAE':control[cohort][variant]['macro_ST_RAE'],
                 'delta':values['macro_ST_RAE']-control[cohort][variant]['macro_ST_RAE']} for variant,values in item.items()} for cohort,item in results.items()}
    native.save(out/'comparison.json',comparison)
    native.save(out/'complete.json',{'status':'complete','models':40,'initialization':'scratch','features':'all_admetlab_numeric','source_mode':'web_default','api_probe_vectors_used':False,'scores':results,
            'external_teacher_training_membership':'unknown','files':{str(f.relative_to(out)):native.sha(f) for f in out.rglob('*') if f.is_file() and f.suffix!='.log' and f.name!='complete.json'}})
    print(json.dumps({'event':'admet_feature_ensemble_complete','comparison':comparison}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',default='admet_feature_config.json');parser.add_argument('--worker');args=parser.parse_args()
    if args.worker:return worker(args.worker)
    run(json.loads(Path(args.config).read_text()))

if __name__=='__main__':main()
