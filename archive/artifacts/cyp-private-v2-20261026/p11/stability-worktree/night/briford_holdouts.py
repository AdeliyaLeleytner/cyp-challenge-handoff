"""Frozen outer validation of the native briford recipe. No holdout-label fitting."""
from pathlib import Path
from functools import lru_cache
import json, subprocess, sys, time, os, signal
import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from . import briford_native as native
from .public_data import normalize_parent_key

@lru_cache(maxsize=100000)
def keys(smiles):
    mol=Chem.MolFromSmiles(smiles)
    if mol is None: raise ValueError('Invalid SMILES in frozen native inputs')
    return normalize_parent_key(smiles),Chem.MolToInchiKey(mol).split('-')[0]

def prepare(config):
    RDLogger.DisableLog('rdApp.*')
    assets=Path(config['assets']);dest=Path(config['output_dir']);dest.mkdir(parents=True,exist_ok=True)
    truth=pd.read_csv(assets/'official-train.csv');allids=set(truth.Molecule_Name)
    cohorts=json.loads((assets/'cohorts.json').read_text())['cohorts']
    original=assets/'prepared';manifest=json.loads((original/'manifest.json').read_text())
    assert native.sources()==manifest['source_sha256']
    splits=native.load_module('native_holdout_splits',native.VENDOR/'splits.py')
    weights=native.load_module('native_holdout_weights',native.VENDOR/'multi_task.py')
    configs=[]
    for ci,name in enumerate(['own750','briford529']):
        cohort=cohorts[name];held=truth.set_index('Molecule_Name').loc[cohort['test_ids']].reset_index()
        assert len(held)==(750 if name=='own750' else 529)
        excluded_ids=set(cohort['test_ids'])|set(cohort['outer_parent_purged_ids'])
        heldkeys=[keys(s) for s in truth[truth.Molecule_Name.isin(excluded_ids)].SMILES]
        parentkeys={k[0] for k in heldkeys};connectivity={k[1] for k in heldkeys}
        root=dest/name;prep=root/'prepared';prep.mkdir(parents=True,exist_ok=True)
        held.to_csv(root/'truth.csv',index=False,float_format='%.17g')
        held[['Molecule_Name','SMILES']].to_csv(root/'query.csv',index=False)
        audits={};models={}
        for member in native.MODELS:
            spec=json.loads((original/f'{member}.json').read_text())
            assert native.sha(original/f'{member}.csv')==spec['data_sha256']
            frame=pd.read_csv(original/f'{member}.csv',float_precision='round_trip')
            pairs=[keys(s) for s in frame.smiles]
            drop=np.array([i in excluded_ids or p in parentkeys or c in connectivity for i,(p,c) in zip(frame.molecule_name,pairs)])
            # Respect the exact frozen official development pool as well.
            drop |= frame.molecule_name.isin(allids-set(cohort['train_ids'])).to_numpy()
            kept=frame.loc[~drop].reset_index(drop=True);targets=spec['targets'];hp=spec['hyperparameters']
            if member in ['union18','mtaux8']:
                primary=weights.compute_inverse_count_task_weights(kept,native.PRIMARY)
                hp['task_weights']=primary+[.3*float(np.mean(primary))]*(len(targets)-4)
            folds=splits.get_split_indices(kept,n_splits=hp['n_folds'],strategy=hp['split_strategy'],test_size=.2,random_state=hp['seed'],butina_cutoff=None)
            assert not (set(kept.molecule_name)&excluded_ids)
            assert all(p not in parentkeys and c not in connectivity for p,c in map(keys,kept.smiles))
            val=np.concatenate([v for t,v in folds]);assert sorted(val.tolist())==list(range(len(kept)))
            for tr,va in folds: assert not set(tr)&set(va)
            kept.to_csv(prep/f'{member}.csv',index=False,float_format='%.17g')
            spec.update(rows=len(kept),target_counts=kept[targets].notna().sum().astype(int).to_dict(),data_sha256=native.sha(prep/f'{member}.csv'),folds=[{'train':t.tolist(),'validation':v.tolist()} for t,v in folds])
            native.save(prep/f'{member}.json',spec)
            models[member]={k:v for k,v in spec.items() if k!='folds'}
            audits[member]={'before':len(frame),'after':len(kept),'removed':int(drop.sum()),'removed_ids':frame.loc[drop,'molecule_name'].tolist(),'remaining_held_id_parent_or_connectivity_overlap':0,'target_counts':spec['target_counts'],'task_weights':hp.get('task_weights')}
        native.save(prep/'manifest.json',{**manifest,'models':models,'base_official_rows':len(cohort['train_ids']),'official_test_sha256':native.sha(root/'query.csv'),'outer_cohort':name,'outer_exclusion_audit':audits,'original_manifest_sha256':native.sha(original/'manifest.json')})
        native.save(root/'exclusion-audit.json',audits)
        cfg={'phase':'train','prepared_dir':str(prep),'output_dir':str(root/'results'),'official_test':str(root/'query.csv'),'validator_path':str(assets/'activity_validation.py'),'gpus':config['gpus'][ci*4:(ci+1)*4],'known_limits':['Outer holdout labels absent from all member pools; native source recipe retained. Published test-distribution placement constants frozen; not optimized for these holdouts.']}
        native.save(root/'config.json',cfg);configs.append(root/'config.json')
        print(json.dumps({'event':'outer_pool_prepared','cohort':name,'rows':{m:a['after'] for m,a in audits.items()},'holdout_rows':len(held)}),flush=True)
    return configs

def score(config):
    from .evaluation import score as official_score
    dest=Path(config['output_dir']);results={}
    for name in ['own750','briford529']:
        root=dest/name;truth=pd.read_csv(root/'truth.csv');r=root/'results'
        raw=pd.read_csv(r/'cyp-ensemble_activity_submission_native_raw.csv')
        placed=pd.read_csv(r/'cyp-ensemble_activity_submission_native_raw_native_strae.csv')
        result={'raw':official_score(truth,raw),'native_published_placement':official_score(truth,placed)}
        assert all(x['defined'] for x in result.values())
        native.save(root/'scores.json',result);results[name]=result
    native.save(dest/'scores.json',results)
    print(json.dumps({'event':'outer_holdout_scores','scores':results}),flush=True)

def run(config):
    configs=prepare(config)
    running=[]
    for path in configs:
        log=(path.parent/'train.log').open('a')
        proc=subprocess.Popen([sys.executable,'-u','-m','night.briford_native','--config',str(path)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        running.append((proc,log,path))
    def cancelled(signum, frame):
        raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,cancelled)
    signal.signal(signal.SIGINT,cancelled)
    try:
        while running:
            for proc,log,path in list(running):
                rc=proc.poll()
                if rc is None:continue
                log.close()
                if rc:raise RuntimeError(f'Native outer run failed: {path}, exit={rc}')
                running.remove((proc,log,path))
                print(json.dumps({'event':'outer_training_complete','config':str(path)}),flush=True)
            time.sleep(5)
    finally:
        for proc,log,path in running:
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        if running:time.sleep(3)
        for proc,log,path in running:
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            proc.wait();log.close()
    score(config)
    root=Path(config['output_dir'])
    native.save(root/'complete.json',{'status':'complete','models':40,'files':{str(p.relative_to(root)):native.sha(p) for p in root.rglob('*') if p.is_file() and p.suffix!='.log' and p.name!='complete.json'}})

if __name__=='__main__':run(json.loads(Path('briford_config.json').read_text()))
