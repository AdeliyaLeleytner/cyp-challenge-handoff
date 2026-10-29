"""Immutable ORX campaign batch; each fit is isolated and survives coordinator restarts."""
import os, sys, json, time, subprocess, traceback, hashlib, argparse
from pathlib import Path
import pandas as pd
import numpy as np

def worker(job_path):
    job=json.loads(Path(job_path).read_text()); root=Path(job['asset_root']); out=Path(job['output_dir'])
    config=job['config']; cohorts=json.loads((root/'cohorts.json').read_text())
    cohort=cohorts['cohorts'][job['cohort']]; fold=cohort['inner_folds'][job['fold']]
    df=pd.read_csv(root/'official-train.csv').set_index('Molecule_Name',drop=False)
    train=df.loc[fold['train_ids']].reset_index(drop=True)
    val=df.loc[fold['val_ids']].reset_index(drop=True)
    query=df.loc[fold['val_ids']+cohort['test_ids'],['Molecule_Name','SMILES']].reset_index(drop=True)
    config.update(fold_index=job['fold'],excluded_parent_keys=cohorts['excluded_parent_keys'],torch_num_threads=4,num_workers=0)
    if config['kind']=='neural':
        from .neural import run_trial
    elif config['kind']=='adapted_tfm':
        from .adapted_tfm import run_trial
        manifest_path=root/config['parent_manifest']
        if hashlib.sha256(manifest_path.read_bytes()).hexdigest()!=config['parent_manifest_sha256']:
            raise ValueError('Parent encoder manifest changed')
        parent=json.loads(manifest_path.read_text())['parents'][config['parent_model']][job['cohort']][str(config['seed'])][str(job['fold'])]
        config.update(parent,cohort=job['cohort'])
    else:
        from .tabular import run_trial
    started=time.time()
    result=run_trial(config,train,query,root,out,validation_df=val)
    if result.Molecule_Name.tolist()!=query.Molecule_Name.tolist():raise ValueError('Query ID/order drift')
    result.to_csv(out/'predictions.csv',index=False)
    (out/'worker_done.json').write_text(json.dumps({'seconds':time.time()-started,'rows':len(result)}))
    print(json.dumps({'event':'fit_complete','job':job['name'],'seconds':time.time()-started}),flush=True)

def collect(root,out,config):
    from .evaluation import score,calibrate_variants
    cohorts=json.loads((root/'cohorts.json').read_text())['cohorts']
    truth=pd.read_csv(root/'official-train.csv').set_index('Molecule_Name',drop=False)
    summaries=[]
    for model in config['models']:
        for name,cohort in cohorts.items():
            for seed in config['seeds']:
                parts=[]; outers=[]
                for f,fold in enumerate(cohort['inner_folds']):
                    path=out/model['name']/name/f'seed{seed}'/f'fold{f}'/'predictions.csv'
                    if not path.exists():break
                    pred=pd.read_csv(path).set_index('Molecule_Name',drop=False)
                    parts.append(pred.loc[fold['val_ids']].reset_index(drop=True))
                    outers.append(pred.loc[cohort['test_ids']].reset_index(drop=True))
                if len(parts)!=5:continue
                oof=pd.concat(parts).set_index('Molecule_Name').loc[cohort['train_ids']].reset_index()
                outer=outers[0].copy(); cols=[c for c in outer if c!='Molecule_Name']
                outer[cols]=np.mean([x[cols].to_numpy() for x in outers],axis=0)
                dest=out/model['name']/name/f'seed{seed}'
                oof.to_csv(dest/'oof.csv',index=False);outer.to_csv(dest/'outer_raw.csv',index=False)
                # All calibration labels are from outer-development OOF only.
                mapping={i:f for f,fold in enumerate(cohort['inner_folds']) for i in fold['val_ids']}
                variants,params=calibrate_variants(truth.loc[cohort['train_ids']].reset_index(drop=True),oof,outer,mapping,
                    allowed_fit_ids=cohort['train_ids'],forbidden_fit_ids=cohort['test_ids'])
                placed=variants[params['selected_name']]
                placed.to_csv(dest/'outer_calibrated.csv',index=False)
                (dest/'calibration.json').write_text(json.dumps(params,indent=2,default=str))
                row={'model':model['name'],'cohort':name,'seed':seed,
                     'raw':score(truth.loc[cohort['test_ids']].reset_index(drop=True),outer),
                     'calibrated':score(truth.loc[cohort['test_ids']].reset_index(drop=True),placed)}
                summaries.append(row)
                print(json.dumps({'event':'model_evaluated',**row},default=str),flush=True)
    reference_members=['union18','mtaux8','2d6isoform6','2d6single']
    if set(reference_members)<=set(m['name'] for m in config['models']):
        for name,cohort in cohorts.items():
            for seed in config['seeds']:
                assembled={}
                for kind in ['oof','outer_raw']:
                    paths=[out/m/name/f'seed{seed}'/f'{kind}.csv' for m in reference_members]
                    if not all(p.exists() for p in paths):break
                    frames=[pd.read_csv(p).set_index('Molecule_Name') for p in paths]
                    ids=cohort['train_ids'] if kind=='oof' else cohort['test_ids']
                    result=pd.DataFrame({'Molecule_Name':ids})
                    for target in frames[0].columns:
                        members=[f.loc[ids,target].to_numpy() for f in frames if target in f]
                        result[target]=np.mean(members,axis=0)
                    assembled[kind]=result
                if len(assembled)!=2:continue
                dest=out/'briford_reference'/name/f'seed{seed}';dest.mkdir(parents=True,exist_ok=True)
                mapping={i:f for f,fold in enumerate(cohort['inner_folds']) for i in fold['val_ids']}
                variants,params=calibrate_variants(truth.loc[cohort['train_ids']].reset_index(drop=True),assembled['oof'],assembled['outer_raw'],mapping,
                    allowed_fit_ids=cohort['train_ids'],forbidden_fit_ids=cohort['test_ids'])
                assembled['outer_calibrated']=variants[params['selected_name']]
                for key,frame in assembled.items():frame.to_csv(dest/f'{key}.csv',index=False)
                for key,frame in variants.items():frame.to_csv(dest/f'outer_{key}.csv',index=False)
                (dest/'calibration.json').write_text(json.dumps(params,indent=2))
                row={'model':'briford_reference','cohort':name,'seed':seed,'selected_calibration':params['selected_name'],
                    'raw':score(truth.loc[cohort['test_ids']].reset_index(drop=True),assembled['outer_raw']),
                    'calibrated':score(truth.loc[cohort['test_ids']].reset_index(drop=True),assembled['outer_calibrated'])}
                summaries.append(row);print(json.dumps({'event':'reference_evaluated',**row}),flush=True)
    (out/'summary.json').write_text(json.dumps(summaries,indent=2,default=str))

def main():
    p=argparse.ArgumentParser();p.add_argument('--worker');p.add_argument('--config',default='night_config.json');args=p.parse_args()
    if args.worker:return worker(args.worker)
    config=json.loads(Path(args.config).read_text());root=Path(config['asset_root']);out=Path(config['output_dir']);out.mkdir(parents=True,exist_ok=True)
    (out/'config.json').write_text(json.dumps(config,indent=2))
    jobs=[]
    # All source/model seeds are fixed before results. Cohort selection never adapts to scores.
    for seed in config['seeds']:
        for cname in config.get('cohorts',['briford529','own750']):
            for f in range(5):
                for model in config['models']:
                    target=out/model['name']/cname/f'seed{seed}'/f'fold{f}'; target.mkdir(parents=True,exist_ok=True)
                    job={'name':f"{model['name']}/{cname}/{seed}/{f}",'asset_root':str(root),'output_dir':str(target),
                         'config':dict(model,seed=seed),'cohort':cname,'fold':f}
                    jp=target/'job.json';jp.write_text(json.dumps(job,indent=2))
                    if not (target/'worker_done.json').exists():jobs.append((job,jp))
    slots={};failed=[];gpu_ids=config.get('gpus',[0,1,2,3])
    while jobs or slots:
        for gpu in gpu_ids:
            if gpu in slots:continue
            if not jobs:break
            job,jp=jobs.pop(0);env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu))
            log=open(Path(job['output_dir'])/'worker.log','a')
            proc=subprocess.Popen([sys.executable,'-u','-m','night.runner','--worker',str(jp)],env=env,stdout=log,stderr=subprocess.STDOUT)
            slots[gpu]=(proc,log,job)
            print(json.dumps({'event':'fit_started','gpu':gpu,'job':job['name'],'pid':proc.pid}),flush=True)
        for gpu,(proc,log,job) in list(slots.items()):
            status=proc.poll()
            if status is None:continue
            log.close();del slots[gpu]
            print(json.dumps({'event':'fit_exited','job':job['name'],'exit':status}),flush=True)
            if status:failed.append({'job':job,'exit':status})
        (out/'status.json').write_text(json.dumps({'queued':len(jobs),'running':[x[2]['name'] for x in slots.values()],'failed':failed,'time':time.time()},indent=2))
        time.sleep(5)
    collect(root,out,config)
    if failed:raise RuntimeError(f'{len(failed)} fits failed; inspect worker logs')

if __name__=='__main__':main()
