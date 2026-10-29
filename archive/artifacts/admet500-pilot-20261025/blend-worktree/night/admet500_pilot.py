"""Matched small-sample ADMETlab feature pilot; no full-matrix or leaderboard claim."""
from pathlib import Path
import json,hashlib,time,warnings,importlib.metadata,subprocess,sys,faulthandler
faulthandler.enable()
import numpy as np
import pandas as pd
from scipy.stats import spearmanr,kendalltau
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import Ridge
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics.pairwise import rbf_kernel
from lightgbm import LGBMRegressor
from rdkit import Chem,RDLogger
from rdkit.Chem import Descriptors,rdFingerprintGenerator
from rdkit.Chem.Scaffolds import MurckoScaffold
from .admet500_parser import parse_batch
from official_scoring_functions import rae_soft_threshold_absolute_error

TARGETS=[f'{x}_pIC50_direct_inhibition' for x in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False,default=lambda x:x.item() if isinstance(x,np.generic) else str(x))+'\n')
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def event(name,**kw):print(json.dumps({'event':name,**kw}),flush=True)

def prepare(cfg):
    out=Path(cfg['output_dir']);out.mkdir(parents=True,exist_ok=True)
    assert digest(cfg['asset_manifest'])==cfg['asset_manifest_sha256']
    manifest=json.loads(Path(cfg['asset_manifest']).read_text())
    for value in manifest.values():assert digest(value['path'])==value['sha256'],value['path']
    paths={key:Path(value['path']) for key,value in manifest.items()}
    raw=pd.read_csv(paths['admet.csv']);assert raw.raw_smiles.nunique()==len(raw)==500
    queue=pd.read_csv(paths['queue.csv'],dtype=str);queue=queue[queue.SMILES.isin(raw.raw_smiles)]
    assert len(queue)==500
    parsed,failed,audit=parse_batch(paths['admet.csv'].read_bytes(),queue.to_dict('records'),json.loads(paths['web-schema.json'].read_text()),'user-supplied-500')
    assert not failed and len(parsed)==500
    columns=sorted({key for r in parsed for key in r['features']});assert len(columns)==120
    bykey={r['request_id']:r for r in parsed}
    mapping=pd.read_csv(paths['id-map.csv'],dtype=str)
    chosen=mapping[(mapping.source=='official-train.csv')&mapping.request_id.isin(bykey)].copy()
    assert chosen.Molecule_Name.is_unique and chosen.request_id.is_unique
    official=pd.read_csv(paths['official-train.csv'])
    data=official[official.Molecule_Name.isin(chosen.Molecule_Name)].copy().reset_index(drop=True)
    chosen=chosen.set_index('Molecule_Name').loc[data.Molecule_Name]
    data['request_id']=chosen.request_id.to_numpy();data['request_smiles']=chosen.request_smiles.to_numpy()
    assert len(data)==431
    Xad=np.array([[bykey[key]['features'].get(col,np.nan) for col in columns] for key in data.request_id],float)
    assert np.isfinite(Xad).all(),'Unexpected missing feature values require explicit audit'
    RDLogger.DisableLog('rdApp.*')
    mols=[Chem.MolFromSmiles(s) for s in data.SMILES];assert all(m is not None for m in mols)
    for mol,s in zip(mols,data.request_smiles):assert Chem.MolToSmiles(mol)==s
    gen=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048)
    fp=np.array([gen.GetFingerprintAsNumPy(m) for m in mols],np.float64)
    descriptors=[name for name,fn in Descriptors._descList]
    rd=np.array([[fn(m) for name,fn in Descriptors._descList] for m in mols],float)
    rd[~np.isfinite(rd)]=np.nan
    groups=[];parents=[]
    for m in mols:
        parent=Chem.MolToInchiKey(m).split('-')[0];parents.append(parent)
        scaffold=Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(m),isomericSmiles=False)
        groups.append(scaffold or 'acyclic:'+parent)
    data['scaffold_group']=groups;data['connectivity']=parents
    y=data[TARGETS].to_numpy(float)
    lo=data[[t+'_conf_low' for t in TARGETS]].to_numpy(float);hi=data[[t+'_conf_high' for t in TARGETS]].to_numpy(float)
    observed=np.isfinite(y);assert np.isfinite(lo[observed]).all() and np.isfinite(hi[observed]).all()
    cohorts=json.loads(paths['cohorts.json'].read_text())['cohorts']
    count={name:{'train':int(data.Molecule_Name.isin(c['train_ids']).sum()),'test':int(data.Molecule_Name.isin(c['test_ids']).sum()),
                 'test_labels':data[data.Molecule_Name.isin(c['test_ids'])][TARGETS].notna().sum().to_dict()} for name,c in cohorts.items()}
    analysis={'received':500,'labeled_molecules':len(data),'blind_test_molecules':69,'endpoints':columns,
        'label_counts':data[TARGETS].notna().sum().to_dict(),'scaffold_groups':len(set(groups)),
        'largest_scaffold_group':int(pd.Series(groups).value_counts().max()),'frozen_cohort_coverage':count,
        'source_hashes':manifest,'external_teacher_training_membership':'unknown; do not claim end-to-end label-independent external model',
        'scope':'Pilot on500 manually supplied web-default predictions; no imputation of unacquired molecules and no full native feature refit',
        'criterion':'Report measured gains/losses and paired uncertainty without an invented promotion threshold.'}
    save(out/'data-audit.json',analysis);save(out/'admet-row-alignment.json',audit)
    data.to_csv(out/'labeled-molecules.csv',index=False)
    save(out/'feature-columns.json',{'ADMETlab':columns,'RDKit':descriptors,'ECFP':'Morgan radius2,2048binary'})
    event('data_verified',labels=analysis['label_counts'],coverage=count,scaffolds=len(set(groups)))
    return paths,data,fp,rd,Xad,columns,y,lo,hi,np.array(groups),cohorts

def embed(data,checkpoint,out):
    subprocess.run([sys.executable,'-u','-m','night.admet500_embed',str(out/'labeled-molecules.csv'),str(checkpoint),str(out/'frozen-chemeleon.npy')],check=True)
    result=np.load(out/'frozen-chemeleon.npy')
    assert result.shape==(len(data),2048) and np.isfinite(result).all()
    event('frozen_encoder_complete',shape=list(result.shape),trained_on_current_labels=False)
    return result

def transform(a,b,scale=True):
    imputer=SimpleImputer(strategy='median',keep_empty_features=True);a=imputer.fit_transform(a);b=imputer.transform(b)
    if scale:
        scaler=StandardScaler();a=scaler.fit_transform(a);b=scaler.transform(b)
        a=np.clip(a,-20,20);b=np.clip(b,-20,20)
    return a,b
def tanimoto(a,b):
    product=a@b.T;den=a.sum(1)[:,None]+b.sum(1)[None,:]-product
    return np.divide(product,den,out=np.zeros_like(product),where=den>0)
def similarity(a,b,kind):
    if kind=='tanimoto':return tanimoto(a,b)
    return rbf_kernel(a,b,gamma=.5/a.shape[1])
def predict(family,view,train,test,target,X,seed):
    if family=='kernel':
        def block(key,kind):
            a,b=X[key][train],X[key][test]
            if kind!='tanimoto':a,b=transform(a,b)
            return similarity(a,a,kind),similarity(b,a,kind)
        if view!='admet':
            kf,qf=block('fp','tanimoto');kr,qr=block('rd','rbf');ks,qs=.75*kf+.25*kr,.75*qf+.25*qr
        if view!='structure':ka,qa=block('admet','rbf')
        if view=='structure':k,q=ks,qs
        elif view=='admet':k,q=ka,qa
        else:k,q=.5*(ks+ka),.5*(qs+qa)
        center=target.mean();return center+q@np.linalg.solve(k+np.eye(len(train)),target-center)
    if family=='chemeleon_ridge':
        a,b=transform(X['chemeleon'][train],X['chemeleon'][test]);a/=np.sqrt(a.shape[1]);b/=np.sqrt(b.shape[1])
        if view=='augmented':
            aa,bb=transform(X['admet'][train],X['admet'][test]);aa/=np.sqrt(aa.shape[1]);bb/=np.sqrt(bb.shape[1])
            a=np.concatenate([a,aa],axis=1)/np.sqrt(2);b=np.concatenate([b,bb],axis=1)/np.sqrt(2)
        return Ridge(alpha=1.0).fit(a,target).predict(b)
    if view=='structure':raw=X['structure']
    elif view=='admet':raw=X['admet']
    elif view=='no_cyp':raw=np.column_stack([X['structure'],X['admet_no_cyp']])
    else:raw=np.column_stack([X['structure'],X['admet']])
    a,b=transform(raw[train],raw[test],False)
    if family=='extratrees':model=ExtraTreesRegressor(n_estimators=192,min_samples_leaf=3,max_features=.3,n_jobs=2,random_state=seed)
    elif family=='lightgbm':model=LGBMRegressor(n_estimators=220,num_leaves=7,max_depth=3,min_child_samples=10,learning_rate=.03,reg_lambda=5,objective='regression_l1',verbosity=-1,n_jobs=2,random_state=seed,force_col_wise=True)
    else:raise ValueError(family)
    return model.fit(a,target).predict(b)

def metric(y,p,lo,hi):
    mask=np.isfinite(y);y,p,lo,hi=y[mask],p[mask],lo[mask],hi[mask]
    assert len(y)>=2 and np.isfinite(p).all()
    denom=np.sum(np.maximum(lo-y.mean(),0)+np.maximum(y.mean()-hi,0))
    if denom<=0:raise ValueError('Undefined ST-RAE denominator')
    return {'ST_RAE':float(rae_soft_threshold_absolute_error(y,p,y_true_lower=lo,y_true_upper=hi)),
        'MAE':float(np.abs(y-p).mean()),'R2':float(1-np.sum((y-p)**2)/np.sum((y-y.mean())**2)),
        'Spearman':float(spearmanr(y,p).statistic) if np.std(p)>0 else None,
        'Kendall':float(kendalltau(y,p).statistic) if np.std(p)>0 else None,'n':len(y)}
def scores(y,p,lo,hi):
    per=[metric(y[:,j],p[:,j],lo[:,j],hi[:,j]) for j in range(4)]
    macro={k:float(np.mean([r[k] for r in per])) if all(r[k] is not None for r in per) else None for k in ['ST_RAE','MAE','R2','Spearman','Kendall']}
    return {'macro':macro,'per_cyp':dict(zip(TARGETS,per))}
def save_prediction(out,name,frame,p):
    result=frame[['Molecule_Name','request_id']].copy()
    for j,t in enumerate(TARGETS):result[t]=p[:,j]
    result.to_csv(out/(name+'.csv'),index=False)

def old_base_predictions(paths,cohort,data):
    lower=[x.lower() for x in TARGETS];total=np.zeros((len(data),4));count=np.zeros_like(total)
    for member in ['union18','mtaux8','2d6isoform6','2d6single']:
        table=pd.read_csv(paths[f'{cohort}_{member}_oof']).set_index('molecule_name');assert table.index.is_unique
        for j,t in enumerate(lower):
            if t+'_pred' not in table:continue
            values=table[t+'_pred'].reindex(data.Molecule_Name).to_numpy();mask=np.isfinite(values)
            total[mask,j]+=values[mask];count[mask,j]+=1
    train=np.divide(total,count,out=np.full_like(total,np.nan),where=count>0)
    for j,t in enumerate(TARGETS):
        mask=np.isfinite(data[t])&(count[:,j]>0)
        assert np.all(count[mask,j]==(4 if '2D6' in t else 2)),'Different OOF component coverage'
    test=pd.read_csv(paths[f'{cohort}_native_test']).set_index('Molecule_Name').reindex(data.Molecule_Name)[TARGETS].to_numpy()
    return train,test

def correction(base_train,base_test,y,tr,te,X,method,features):
    result=np.empty((len(te),4))
    for j in range(4):
        fit=tr[np.isfinite(y[tr,j])];assert np.isfinite(base_train[fit,j]).all()
        a=base_train[fit,j,None];b=base_test[te,j,None]
        extra=[]
        if features in ('structure','both'):extra.append('structure')
        if features in ('admet','both'):extra.append('admet')
        for key in extra:a=np.column_stack([a,X[key][fit]]);b=np.column_stack([b,X[key][te]])
        a,b=transform(a,b,scale=method=='ridge');residual=y[fit,j]-base_train[fit,j]
        if method=='ridge':model=Ridge(alpha=100)
        else:model=LGBMRegressor(n_estimators=120,num_leaves=3,max_depth=2,min_child_samples=15,learning_rate=.03,reg_lambda=10,n_jobs=2,verbosity=-1,random_state=42,force_col_wise=True)
        result[:,j]=base_test[te,j]+model.fit(a,residual).predict(b)
    return result

def run(cfg):
    started=time.time();out=Path(cfg['output_dir']);paths,data,fp,rd,ad,columns,y,lo,hi,groups,cohorts=prepare(cfg)
    X={'fp':fp,'rd':rd,'admet':ad,'structure':np.column_stack([fp,rd]),'admet_no_cyp':ad[:,[not ('::metabolism::CYP' in c) for c in columns]]}
    X['chemeleon']=embed(data,paths['chemeleon'],out)
    configs=[(family,view) for family in ['extratrees','lightgbm','kernel'] for view in ['structure','admet','augmented']]
    configs += [('chemeleon_ridge','structure'),('chemeleon_ridge','augmented'),('lightgbm','no_cyp')]
    names=[a+'__'+b for a,b in configs]
    folds={};strata=np.sum(np.isfinite(y)*np.array([1,2,4,8]),axis=1)
    for seed in cfg['cv_seeds']:
        split=StratifiedGroupKFold(n_splits=cfg['cv_folds'],shuffle=True,random_state=seed)
        folds[seed]=[(a,b) for a,b in split.split(np.zeros(len(data)),strata,groups)]
        for tr,te in folds[seed]:
            assert not set(groups[tr])&set(groups[te])
            assert all(np.isfinite(y[tr,j]).sum()>20 and np.isfinite(y[te,j]).sum()>2 for j in range(4))
    save(out/'cv-folds.json',{str(seed):[{'train_ids':data.iloc[a].Molecule_Name.tolist(),'test_ids':data.iloc[b].Molecule_Name.tolist()} for a,b in splits] for seed,splits in folds.items()})
    all_results={};predictions={};summary=[];per_rows=[]
    for (family,view),name in zip(configs,names):
        seed_predictions=[]
        for seed,splits in folds.items():
            pred=np.full_like(y,np.nan)
            for tr,te in splits:
                for j in range(4):
                    fit=tr[np.isfinite(y[tr,j])]
                    pred[te,j]=predict(family,view,fit,te,y[fit,j],X,seed)
            assert np.isfinite(pred).all();seed_predictions.append(pred)
            save_prediction(out,f'cv_seed{seed}_{name}',data,pred)
        p=np.mean(seed_predictions,axis=0);predictions[('cv',name)]=p
        result=scores(y,p,lo,hi);all_results['cv/'+name]=result
        save_prediction(out,'cv_'+name,data,p)
        event('cv_model_complete',model=name,metrics=result['macro'],seconds=round(time.time()-started,1))
    eval_data={'cv':(data,y,lo,hi,groups)}
    for cohort,cohort_spec in cohorts.items():
        tr=np.flatnonzero(data.Molecule_Name.isin(cohort_spec['train_ids']));te=np.flatnonzero(data.Molecule_Name.isin(cohort_spec['test_ids']))
        assert not set(data.iloc[tr].connectivity)&set(data.iloc[te].connectivity)
        frame=data.iloc[te].reset_index(drop=True);eval_data[cohort]=(frame,y[te],lo[te],hi[te],groups[te])
        for (family,view),name in zip(configs,names):
            pred=np.empty((len(te),4))
            for j in range(4):
                fit=tr[np.isfinite(y[tr,j])];pred[:,j]=predict(family,view,fit,te,y[fit,j],X,cfg['model_seed'])
            predictions[(cohort,name)]=pred;all_results[cohort+'/'+name]=scores(y[te],pred,lo[te],hi[te]);save_prediction(out,cohort+'_'+name,frame,pred)
        native_train,native_test=old_base_predictions(paths,cohort,data)
        assert np.isfinite(native_test[te]).all()
        predictions[(cohort,'native_fullpool')]=native_test[te]
        all_results[cohort+'/native_fullpool']=scores(y[te],native_test[te],lo[te],hi[te]);save_prediction(out,cohort+'_native_fullpool',frame,native_test[te])
        for method,views in [('ridge',['base','admet','structure','both']),('lightgbm',['base','admet'])]:
            for view in views:
                name='native_'+method+'_'+view
                pred=correction(native_train,native_test,y,tr,te,X,method,view)
                predictions[(cohort,name)]=pred;all_results[cohort+'/'+name]=scores(y[te],pred,lo[te],hi[te]);save_prediction(out,cohort+'_'+name,frame,pred)
        event('outer_cohort_complete',cohort=cohort,n=len(te),results={k.split('/')[1]:v['macro'] for k,v in all_results.items() if k.startswith(cohort+'/')})
    for key,value in all_results.items():
        cohort,name=key.split('/');summary.append({'cohort':cohort,'model':name,**value['macro']})
        for target,metrics in value['per_cyp'].items():per_rows.append({'cohort':cohort,'model':name,'target':target,**metrics})
    pd.DataFrame(summary).to_csv(out/'all-metrics.csv',index=False);pd.DataFrame(per_rows).to_csv(out/'per-cyp-metrics.csv',index=False)
    save(out/'scores.json',all_results)
    compare(cfg,out,predictions,eval_data)
    save(out/'complete.json',{'status':'complete','seconds':time.time()-started,'models':names,'cv_seeds':cfg['cv_seeds'],
        'packages':{k:importlib.metadata.version(k) for k in ['numpy','pandas','scikit-learn','lightgbm','chemprop','torch','rdkit']},
        'no_new_labels_acquired':True,'no_hidden_test_labels':True,'no_submission':True})
    event('pilot_complete',seconds=round(time.time()-started,1),output=str(out))

def compare(cfg,out,predictions,eval_data):
    pairs=[(f+'__structure',f+'__augmented') for f in ['extratrees','lightgbm','kernel','chemeleon_ridge']]
    pairs += [('lightgbm__no_cyp','lightgbm__augmented')]
    intervals=[]
    for cohort,(frame,y,lo,hi,groups) in eval_data.items():
        local=pairs.copy()
        if cohort!='cv':local += [('native_fullpool','native_ridge_admet'),('native_fullpool','native_lightgbm_admet'),
           ('native_ridge_base','native_ridge_admet'),('native_ridge_structure','native_ridge_both'),('native_lightgbm_base','native_lightgbm_admet')]
        unique=np.unique(groups);members=[np.flatnonzero(groups==key) for key in unique]
        rng=np.random.default_rng(20261025);indices=[np.concatenate([members[k] for k in rng.integers(0,len(unique),len(unique))]) for _ in range(cfg['bootstrap_samples'])]
        def fast_metrics(ids,p):
            st=[];ma=[]
            for j in range(4):
                ix=ids[np.isfinite(y[ids,j])]
                if len(ix)<2:return None
                yy=y[ix,j];den=np.sum(np.maximum(lo[ix,j]-yy.mean(),0)+np.maximum(yy.mean()-hi[ix,j],0))
                if den<=0:return None
                st.append(np.sum(np.maximum(lo[ix,j]-p[ix,j],0)+np.maximum(p[ix,j]-hi[ix,j],0))/den);ma.append(np.abs(yy-p[ix,j]).mean())
            return np.array([np.mean(st),np.mean(ma)])
        for baseline,augmented in local:
            a=predictions[(cohort,baseline)];b=predictions[(cohort,augmented)]
            point=fast_metrics(np.arange(len(y)),b)-fast_metrics(np.arange(len(y)),a);values=[]
            for ix in indices:
                first,second=fast_metrics(ix,a),fast_metrics(ix,b)
                if first is not None and second is not None:values.append(second-first)
            values=np.asarray(values)
            for j,metric_name in enumerate(['ST_RAE','MAE']):
                intervals.append({'cohort':cohort,'baseline':baseline,'augmented':augmented,'metric':metric_name,'delta':point[j],
                    'lower95':np.quantile(values[:,j],.025),'upper95':np.quantile(values[:,j],.975),'valid_bootstraps':len(values),'requested_bootstraps':len(indices),
                    'note':'Cluster bootstrap over scaffold groups; conditional on fixed predictions. Negative delta is improvement. Exploratory multiple comparisons, no selection adjustment.'})
    pd.DataFrame(intervals).to_csv(out/'paired-deltas.csv',index=False)
    event('paired_comparisons_complete',comparisons=len(intervals),primary_deltas=[x for x in intervals if x['metric']=='ST_RAE'])

if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    warnings.filterwarnings('ignore',message='X does not have valid feature names')
    with threadpool_limits(limits=2):run(json.loads(Path('pilot_config.json').read_text()))
