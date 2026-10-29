from pathlib import Path
import json
import numpy as np,pandas as pd
from .admet_full_contract import validate,digest,require
from .admet_full import TARGETS,native_predictions
from .h5_features import validate_embedding_assets

def read_vector(path,ids,smiles):
    x=pd.read_csv(path)
    require(x.Molecule_Name.is_unique and x.Molecule_Name.tolist()==list(ids),'Prediction ID/order mismatch: '+str(path))
    require(x.SMILES.tolist()==list(smiles),'Prediction exact SMILES/order mismatch: '+str(path))
    p=x[TARGETS].to_numpy(float);require(p.shape==(len(ids),4) and np.isfinite(p).all(),'Nonfinite prediction')
    return p

def load_inputs(cfg):
    for key,x in cfg['files'].items():require(digest(x['path'])==x['sha256'],'Pinned H7 asset changed:'+key)
    base=json.loads(Path(cfg['files']['base_config']['path']).read_text());manifest,paths,columns=validate(base)
    require(digest(Path(__file__).parent/'h5_features.py')==base['embedding_contract_sha256'],'Embedding validator changed')
    assets,proof=validate_embedding_assets(base)
    data=pd.read_csv(paths['official_train']);rows=pd.read_csv(assets['adme_source_rows']['path']);e=np.load(assets['adme_matrix']['path'],allow_pickle=False)
    require(rows.Molecule_Name.tolist()==data.Molecule_Name.tolist() and rows.SMILES.tolist()==data.SMILES.tolist(),'Embedding identity/order mismatch')
    require(e.shape==(4905,600) and e.dtype==np.float32 and np.isfinite(e).all(),'Invalid embedding bank')
    require(digest(Path(__file__).resolve().parents[1]/'official_scoring_functions.py')==base['scorer_sha256'],'Scorer changed')
    require(digest(Path(__file__).resolve().parents[1]/'vendor/briford_native/cyp_recalibrate.py')==base['placement_source_sha256'],'Placement changed')
    cohorts=json.loads(paths['cohorts'].read_text())['cohorts'];indexed=data.set_index('Molecule_Name');lookup={n:i for i,n in enumerate(data.Molecule_Name)};result={}
    primary=json.loads(Path(cfg['files']['primary_inner']['path']).read_text());h6=json.loads(Path(cfg['files']['h6_inner']['path']).read_text())
    for name,c in cohorts.items():
        if name not in ['own750','briford529']:continue
        tr=np.array([lookup[x] for x in c['train_ids']]);te=np.array([lookup[x] for x in c['test_ids']]);require(not set(tr)&set(te),'Train/query overlap')
        trdf=data.iloc[tr];tedf=data.iloc[te];base_oof,base_query=native_predictions(paths,name,data)
        oof=[base_oof[tr]];query=[base_query[te]];params={}
        for source,spec in [('primary',primary[name]['lightgbm__admet']),('h6',h6[name]['lightgbm__adme720'])]:
            chosen=min(spec['candidates'],key=lambda z:(z['training_OOF']['macro']['ST_RAE'],z['candidate']))
            require(chosen['candidate']==spec['selected']['candidate'],'Stored hyperparameter selection mismatch')
            require(cfg['cohorts'][name][source+'_candidate']==chosen['candidate'],'Frozen candidate mismatch')
            oof.append(read_vector(cfg['files'][name+'_'+source+'_oof']['path'],trdf.Molecule_Name,trdf.SMILES));query.append(read_vector(cfg['files'][name+'_'+source+'_query']['path'],tedf.Molecule_Name,tedf.SMILES));params[source]=chosen['params']
        require(np.isfinite(oof).all() and np.isfinite(query).all(),'Incomplete expert predictions')
        native_saved=read_vector(cfg['files'][name+'_native_query']['path'],tedf.Molecule_Name,tedf.SMILES);require(np.allclose(native_saved,query[0],atol=1e-12,rtol=0),'Native certificate/vector parity')
        w=float(primary[name]['lightgbm__admet']['blends']['global']['weight']);primary_query=(1-w)*query[0]+w*query[1];saved=read_vector(cfg['files'][name+'_primary_global_query']['path'],tedf.Molecule_Name,tedf.SMILES);require(np.allclose(primary_query,saved,atol=1e-12,rtol=0),'Primary global reference parity')
        result[name]={'train':tr,'test':te,'oof':np.stack(oof,axis=-1),'query':np.stack(query,axis=-1),'primary_weight':w,'selected_params':params}
    require(set(result)=={'own750','briford529'},'Wrong cohorts')
    return data,result,base,manifest
