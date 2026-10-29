"""ORX entry point for frozen stack, interval-forest, and transductive candidates.

Usage: python -m night.metamodel_runner --config /path/to/config.json

Config: asset_root, output_dir, cohorts, seeds, methods. Each method has name,
 type (stack|width|transductive), models={name:rootpath_template}, config={}, and
 optional feature_specs=[{family:'precomputed',asset_key:'chemeleon_foundation'}].
Templates accept {cohort}, {seed}, {model}, {asset_root}. Each resolved root must
contain oof.csv and outer_raw.csv. No method/model is silently omitted.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import re
import time
import traceback
import numpy as np
import pandas as pd
from .reference import CANONICAL


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _json_default(value):
    if isinstance(value,Path): return str(value)
    if isinstance(value,np.generic): return value.item()
    if isinstance(value,np.ndarray): return value.tolist()
    raise TypeError(f'Not JSON serializable: {type(value).__name__}')

def _write_json(path,value):
    path=Path(path);temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,default=_json_default,allow_nan=False)+'\n')
    temp.replace(path)

def _safe_name(name,label):
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+',name) or name in {'.','..'}:
        raise ValueError(f'Unsafe/invalid {label}: {name!r}')
    return name

def _read_snapshot(path):
    path=Path(path);raw=path.read_bytes()
    return raw,{'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}

def _check_ids(values,label):
    if any(pd.isna(v) for v in values): raise ValueError(f'Null IDs in {label}')
    ids=[str(v) for v in values]
    if not ids or len(ids)!=len(set(ids)): raise ValueError(f'Empty/duplicate IDs in {label}')
    return ids

def _prediction_snapshot(path,expected_ids):
    raw,manifest=_read_snapshot(path)
    frame=pd.read_csv(io.BytesIO(raw),dtype={'Molecule_Name':str})
    if 'Molecule_Name' not in frame: raise ValueError(f'{path}: Molecule_Name missing')
    ids=_check_ids(frame.Molecule_Name.tolist(),str(path))
    if set(ids)!=set(expected_ids):
        raise ValueError(f'{path}: frozen cohort ID mismatch; missing={len(set(expected_ids)-set(ids))}, extra={len(set(ids)-set(expected_ids))}')
    targets=[c for c in CANONICAL if c in frame]
    if not targets or set(frame)-{'Molecule_Name'}-set(targets):
        raise ValueError(f'{path}: expected canonical prediction columns only')
    frame=frame.set_index('Molecule_Name').loc[expected_ids,targets].reset_index()
    if not np.isfinite(frame[targets].to_numpy(float)).all(): raise ValueError(f'{path}: nonfinite predictions')
    manifest.update(rows=len(frame),targets=targets,order_reindexed_to_frozen_cohort=True)
    return frame,manifest

def _validate_cohort(cohort,name,known_ids):
    train=_check_ids(cohort['train_ids'],name+' training')
    test=_check_ids(cohort['test_ids'],name+' outer')
    if set(train)&set(test): raise ValueError(f'{name}: outer/train ID overlap')
    if not set(train+test)<=known_ids: raise ValueError(f'{name}: IDs absent from official training table')
    mapping={}
    for k,fold in enumerate(cohort['inner_folds']):
        val=_check_ids(fold['val_ids'],f'{name} fold{k} validation')
        fit=_check_ids(fold['train_ids'],f'{name} fold{k} fit')
        if not set(val+fit)<=set(train) or set(val)&set(fit): raise ValueError(f'{name}: invalid inner fold{k}')
        for value in val:
            if value in mapping: raise ValueError(f'{name}: repeated OOF validation ID')
            mapping[value]=k
    if set(mapping)!=set(train): raise ValueError(f'{name}: folds do not cover all training IDs exactly')
    if len(set(mapping.values()))<2: raise ValueError('At least two development folds required')
    return train,test,mapping

def _wait_for_sources(paths,wait_seconds):
    if not np.isfinite(wait_seconds) or not 0<=wait_seconds<=86400:
        raise ValueError('wait_seconds must be within [0,86400]')
    deadline=time.monotonic()+wait_seconds;last_notice=-float('inf')
    while True:
        missing=[str(p) for p in paths if not p.is_file()]
        if not missing: return
        if time.monotonic()>=deadline:
            raise FileNotFoundError('Required upstream files missing: '+json.dumps(missing))
        if time.monotonic()-last_notice>=30:
            print(json.dumps({'event':'waiting_for_upstreams','missing_count':len(missing),
                'examples':missing[:4],'seconds_remaining':round(deadline-time.monotonic())}),flush=True)
            last_notice=time.monotonic()
        time.sleep(min(5.,max(0.,deadline-time.monotonic())))

def _feature_frames(train_molecules,query_molecules,specs,asset_root,options,seed,output_dir):
    from .features import build_features
    arrays=[];queries=[];columns=[];metadata=[]
    for index,raw_spec in enumerate(specs):
        spec={'family':raw_spec} if isinstance(raw_spec,str) else dict(raw_spec)
        nested=spec.pop('config',{})
        if not isinstance(nested,dict): raise ValueError('feature_specs.config must be a dictionary')
        spec={**nested,**spec}
        family=spec.get('family')
        if family=='chemeleon_foundation':
            family='precomputed';spec['family']=family;spec.setdefault('asset_key','chemeleon_foundation')
        if not family: raise ValueError('Every feature spec needs family')
        a,names,meta=build_features(train_molecules,family,asset_root,spec)
        q,qnames,qmeta=build_features(query_molecules,family,asset_root,spec)
        if names!=qnames or a.shape!=(len(train_molecules),len(names)) or q.shape!=(len(query_molecules),len(names)):
            raise ValueError('Feature builder shape/name drift')
        arrays.append(a);queries.append(q);columns.extend(f'f{index}_{n}' for n in names)
        metadata.append({'spec':spec,'training':meta,'query':qmeta})
    x=np.concatenate(arrays,axis=1).astype(np.float64)
    q=np.concatenate(queries,axis=1).astype(np.float64)
    x[~np.isfinite(x)]=np.nan;q[~np.isfinite(q)]=np.nan
    options=dict(options or {})
    unknown=set(options)-{'impute_strategy','fill_value','add_indicator','scale','pca_components','pca_solver'}
    if unknown: raise ValueError(f'Unsupported preprocessing keys: {sorted(unknown)}')
    steps=[]
    if options.get('impute_strategy') is not None:
        from sklearn.impute import SimpleImputer
        impute={'strategy':options['impute_strategy'],'keep_empty_features':True,'add_indicator':bool(options.get('add_indicator',False))}
        if impute['strategy']=='constant': impute['fill_value']=options.get('fill_value',0.)
        steps.append(('impute',SimpleImputer(**impute)))
    elif not np.isfinite(x).all() or not np.isfinite(q).all():
        raise ValueError('Nonfinite chemistry features: specify source-only impute_strategy explicitly')
    if options.get('scale',False):
        from sklearn.preprocessing import StandardScaler
        steps.append(('scale',StandardScaler()))
    if options.get('pca_components') is not None:
        from sklearn.decomposition import PCA
        n=int(options['pca_components'])
        if n<1 or n>min(x.shape): raise ValueError('Requested PCA dimension exceeds source matrix dimensions')
        steps.append(('pca',PCA(n_components=n,svd_solver=options.get('pca_solver','auto'),random_state=seed)))
    original_columns=columns.copy()
    if steps:
        from sklearn.pipeline import Pipeline
        import joblib
        transform=Pipeline(steps)
        x=transform.fit_transform(x);q=transform.transform(q)
        joblib.dump(transform,Path(output_dir)/'feature_transform.joblib',compress=3)
        if any(name=='pca' for name,_ in steps): columns=[f'chemistry_pca_{j}' for j in range(x.shape[1])]
        elif x.shape[1]!=len(columns): columns=[f'chemistry_processed_{j}' for j in range(x.shape[1])]
    if not np.isfinite(x).all() or not np.isfinite(q).all(): raise ValueError('Nonfinite transformed chemistry features')
    xf=pd.DataFrame(x,columns=columns);xf.insert(0,'Molecule_Name',train_molecules.Molecule_Name.to_numpy())
    qf=pd.DataFrame(q,columns=columns);qf.insert(0,'Molecule_Name',query_molecules.Molecule_Name.to_numpy())
    return xf,qf,{'sources':metadata,'raw_columns':original_columns,'output_columns':columns,
        'preprocessing':options,'transform_fit_scope':'Outer training chemistry only; no outer query rows or any labels.',
        'development_scope_note':'Any optional unsupervised transform uses all outer-development geometry; downstream pseudoquery folds still exclude their activity labels.',
        'training_matrix_sha256':hashlib.sha256(np.ascontiguousarray(x,dtype='<f8').tobytes()).hexdigest(),
        'query_matrix_sha256':hashlib.sha256(np.ascontiguousarray(q,dtype='<f8').tobytes()).hexdigest()}

def run_config(config_path):
    config_path=Path(config_path).resolve()
    config_bytes,config_source=_read_snapshot(config_path)
    cfg=json.loads(config_bytes)
    root=Path(cfg['asset_root']).expanduser().resolve();out=Path(cfg['output_dir']).expanduser().resolve()
    if (out/'complete.json').exists(): raise FileExistsError(f'Completed output cannot be overwritten: {out}')
    methods=cfg['methods'];seeds=cfg['seeds'];cohort_names=cfg['cohorts']
    if not isinstance(methods,list) or not methods: raise ValueError('Nonempty methods list required')
    if not isinstance(seeds,list) or not seeds or len(set(seeds))!=len(seeds) or any(type(s) is not int or s<0 for s in seeds):
        raise ValueError('Distinct nonnegative integer seeds required')
    if not isinstance(cohort_names,list) or not cohort_names or len(set(cohort_names))!=len(cohort_names): raise ValueError('Distinct cohort names required')
    cohort_bytes,cohort_source=_read_snapshot(root/'cohorts.json')
    frozen=json.loads(cohort_bytes)['cohorts']
    truth_bytes,truth_source=_read_snapshot(root/'official-train.csv')
    truth=pd.read_csv(io.BytesIO(truth_bytes),dtype={'Molecule_Name':str})
    all_ids=_check_ids(truth.Molecule_Name.tolist(),'official training table')
    truth=truth.set_index('Molecule_Name',drop=False)
    cohorts={}
    for name in cohort_names:
        _safe_name(name,'cohort')
        if name not in frozen: raise KeyError(f'Unknown frozen cohort {name}')
        cohorts[name]=_validate_cohort(frozen[name],name,set(all_ids))
    jobs=[];required=[];names=[]
    for method in methods:
        name=_safe_name(method['name'],'method');names.append(name)
        kind=method['type'];models=method['models']
        if kind not in {'stack','width','transductive'}: raise ValueError(f'Unknown method type {kind}')
        if not isinstance(models,dict) or not models: raise ValueError(f'{name}: explicit model mapping required')
        for model in models: _safe_name(model,'model')
        if kind in {'width','transductive'} and len(models)!=1: raise ValueError(f'{name}: {kind} requires exactly one base model')
        specs=method.get('feature_specs',[])
        if not isinstance(specs,list): raise ValueError('feature_specs must be a list')
        if kind=='stack' and specs: raise ValueError('Stack does not consume chemistry feature specs')
        if kind=='transductive' and not specs: raise ValueError('Transductive method requires explicit structure-only feature_specs')
        for cohort in cohort_names:
            for seed in seeds:
                dest=out/name/cohort/f'seed{seed}'
                if (dest/'complete.json').exists(): raise FileExistsError(f'Completed method output cannot be overwritten: {dest}')
                paths={}
                for model,template in models.items():
                    if not isinstance(template,str): raise TypeError('Model rootpath templates must be strings')
                    base=Path(template.format(cohort=cohort,seed=seed,model=model,asset_root=str(root))).expanduser()
                    if not base.is_absolute(): base=root/base
                    paths[model]={'oof':base/'oof.csv','outer':base/'outer_raw.csv'}
                    required.extend(paths[model].values())
                jobs.append((method,cohort,seed,dest,paths))
    if len(names)!=len(set(names)): raise ValueError('Duplicate method names')
    out.mkdir(parents=True,exist_ok=True)
    snapshot=out/'run_config.json'
    if snapshot.exists() and json.loads(snapshot.read_text())!=cfg: raise ValueError('Partial output has a different frozen config')
    _write_json(snapshot,cfg)
    _wait_for_sources(required,float(cfg.get('wait_seconds',0)))
    code_names=['metamodel_runner.py','stacking.py','width_calibration.py','transductive_calibration.py','evaluation.py','features.py','reference.py']
    provenance={'config':config_source,'cohorts':cohort_source,'official_train':truth_source,
        'code_sha256':{name:_sha(Path(__file__).parent/name) for name in code_names},
        'scorer_sha256':_sha(Path(__file__).parents[1]/'official_scoring_functions.py')}
    _write_json(out/'run_provenance.json',provenance)
    summaries=[]
    from .evaluation import score
    for method,cohort,seed,dest,paths in jobs:
        started=time.monotonic();dest.mkdir(parents=True,exist_ok=True)
        if (dest/'complete.json').exists(): raise FileExistsError(f'Completed output appeared during run: {dest}')
        train_ids,test_ids,folds=cohorts[cohort]
        method_cfg=dict(method.get('config',{}));method_cfg['seed']=seed
        preprocessing=method.get('preprocessing',method_cfg.pop('preprocessing',{}))
        intent={'method':method,'cohort':cohort,'seed':seed,'effective_method_config':method_cfg,
            'frozen_cohort_sha256':cohort_source['sha256'],'fit_ids':train_ids,'query_ids':test_ids,
            'fit_label_scope':'Only allowed training OOF truth; outer truth is passed solely to scorer after fitting returns.'}
        _write_json(dest/'intent.json',intent)
        print(json.dumps({'event':'metamodel_started','method':method['name'],'type':method['type'],'cohort':cohort,'seed':seed}),flush=True)
        try:
            oofs={};queries={};source_files={}
            for name,files in paths.items():
                oofs[name],om=_prediction_snapshot(files['oof'],train_ids)
                queries[name],qm=_prediction_snapshot(files['outer'],test_ids)
                if list(oofs[name].columns)!=list(queries[name].columns): raise ValueError(f'{name}: OOF/query target mismatch')
                source_files[name]={'oof':om,'outer':qm}
            _write_json(dest/'upstream_manifest.json',source_files)
            train_truth=truth.loc[train_ids].reset_index(drop=True)
            # Query molecule tables expose structure only; predictions expose canonical output columns only.
            train_molecules=truth.loc[train_ids,['Molecule_Name','SMILES']].reset_index(drop=True)
            query_molecules=truth.loc[test_ids,['Molecule_Name','SMILES']].reset_index(drop=True)
            xf=qf=None;feature_meta=None
            if method.get('feature_specs'):
                xf,qf,feature_meta=_feature_frames(train_molecules,query_molecules,method['feature_specs'],root,preprocessing,seed,dest)
            elif preprocessing: raise ValueError('Preprocessing configured without feature_specs')
            if method['type']=='stack':
                from .stacking import fit_stack
                if 'model_names' in method_cfg and list(method_cfg['model_names'])!=list(method['models']):
                    raise ValueError('Stack model_names must equal explicit models mapping order')
                method_cfg.update(model_names=list(method['models']),allowed_fit_ids=train_ids,forbidden_fit_ids=test_ids)
                result,metadata=fit_stack(train_truth,oofs,queries,folds,method_cfg)
            elif method['type']=='width':
                from .width_calibration import run_candidate
                base=next(iter(method['models']))
                result,metadata=run_candidate(train_truth,oofs[base],queries[base],folds,
                    allowed_fit_ids=train_ids,forbidden_fit_ids=test_ids,training_features=xf,query_features=qf,
                    config=method_cfg,output_dir=dest/'artifacts')
            else:
                from .transductive_calibration import run_candidate
                base=next(iter(method['models']))
                result,metadata=run_candidate(train_truth,oofs[base],queries[base],xf,qf,folds,method_cfg,
                    allowed_fit_ids=train_ids,forbidden_fit_ids=test_ids,output_dir=dest/'artifacts')
            if result.Molecule_Name.astype(str).tolist()!=test_ids: raise ValueError('Returned query ID/order drift')
            # Lock the result and its provenance before exposing any outer labels to scoring.
            result.to_csv(dest/'predictions.csv',index=False)
            metadata.update(runner_provenance=provenance,upstream_files=source_files,
                            runner_features=feature_meta,runner_method_config=method_cfg)
            _write_json(dest/'metadata.json',metadata)
            prediction_sha=_sha(dest/'predictions.csv')
            _write_json(dest/'prediction_lock.json',{'sha256':prediction_sha,'rows':len(result),
                'query_truth_passed_to_fit':False,'locked_before_outer_scoring':True})
            measured=score(truth.loc[test_ids].reset_index(drop=True),result)
            if not measured['defined']: raise ValueError('Undefined outer score; no successful result recorded')
            for source in source_files.values():
                for item in source.values():
                    if _sha(item['path'])!=item['sha256']: raise RuntimeError('Upstream changed during this metamodel fit')
            if _sha(root/'cohorts.json')!=cohort_source['sha256'] or _sha(root/'official-train.csv')!=truth_source['sha256']:
                raise RuntimeError('Frozen data/cohorts changed during run')
            summary={'method':method['name'],'type':method['type'],'cohort':cohort,'seed':seed,
                'score':measured,'seconds':time.monotonic()-started,'prediction_sha256':prediction_sha,
                'output_dir':str(dest)}
            _write_json(dest/'score.json',summary)
            _write_json(dest/'complete.json',{'status':'complete',**summary})
            summaries.append(summary)
            _write_json(out/'summary.json',summaries)
            print(json.dumps({'event':'metamodel_complete','method':method['name'],'cohort':cohort,'seed':seed,
                'macro_ST_RAE':measured['macro_ST_RAE'],
                'per_target':{t:v['ST_RAE'] for t,v in measured['endpoints'].items()},
                'seconds':round(summary['seconds'],3)}),flush=True)
        except Exception as exc:
            failure={'method':method['name'],'cohort':cohort,'seed':seed,'error':repr(exc),'traceback':traceback.format_exc()}
            _write_json(dest/'failure.json',failure)
            _write_json(out/'failure.json',failure)
            raise
    _write_json(out/'complete.json',{'status':'complete','jobs':len(summaries),'config_sha256':config_source['sha256'],
        'summary_sha256':_sha(out/'summary.json')})
    return summaries

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config_path',nargs='?')
    parser.add_argument('--config',dest='config_option')
    args=parser.parse_args()
    if bool(args.config_path)==bool(args.config_option): parser.error('Provide exactly one config path, positional or --config')
    run_config(args.config_option or args.config_path)

if __name__=='__main__': main()
