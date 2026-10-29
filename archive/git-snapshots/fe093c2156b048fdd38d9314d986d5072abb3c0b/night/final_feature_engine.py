"""Full official OOF selection and one final refit. No submission/network code."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from .admet_full_contract_v1 import require,digest
from .admet_full_math import blend_weight,place
from .admet500_pilot import scores
TARGETS=[f'{c}_pIC50_direct_inhibition' for c in ('CYP1A2','CYP2C9','CYP2D6','CYP3A4')]

def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False,default=lambda x:x.item() if isinstance(x,np.generic) else str(x))+'\n')

def align_prediction(frame,official,columns=TARGETS,smiles=True):
    require('Molecule_Name' in frame and frame.Molecule_Name.is_unique,'Duplicate/missing prediction IDs')
    require(set(frame.Molecule_Name)==set(official.Molecule_Name),'Prediction ID set mismatch')
    q=frame.set_index('Molecule_Name').loc[official.Molecule_Name]
    if smiles:require('SMILES' in q and q.SMILES.tolist()==official.SMILES.tolist(),'Prediction SMILES mismatch')
    values=q[columns].to_numpy(float);require(np.isfinite(values).all(),'Nonfinite predictions');return values

def native_vectors(paths,official,blind):
    oof=align_prediction(pd.read_csv(paths['native_official_oof']),official)
    raw=align_prediction(pd.read_csv(paths['native_blind_raw']),blind)
    placed=align_prediction(pd.read_csv(paths['native_blind_placed']),blind)
    total=np.zeros_like(oof);counts=np.zeros_like(oof)
    for member in ('union18','mtaux8','2d6isoform6','2d6single'):
        table=pd.read_csv(paths[member+'_oof']).set_index('molecule_name');require(table.index.is_unique,'Duplicate component OOF IDs')
        for j,target in enumerate(TARGETS):
            key=target.lower()+'_pred'
            if key not in table:continue
            values=table[key].reindex(official.Molecule_Name).to_numpy();mask=np.isfinite(values)
            total[mask,j]+=values[mask];counts[mask,j]+=1
    require(np.all(counts>0),'Missing native rowwise OOF coverage')
    rebuilt=total/counts;require(np.allclose(rebuilt,oof,atol=1e-12,rtol=1e-12),'Combined native OOF disagrees with component vectors')
    for j,target in enumerate(TARGETS):
        observed=np.isfinite(official[target].to_numpy(float));require(np.all(counts[observed,j]==(4 if '2D6' in target else 2)),'Incorrect observed-label component coverage')
    return oof,raw,placed

def emit_predictions(path,data,pred):
    require(pred.shape==(len(data),4) and np.isfinite(pred).all(),'Invalid prediction shape/values')
    f=data[['Molecule_Name','SMILES']].copy()
    if 'request_id' in data:f['request_id']=data.request_id.to_numpy()
    for j,t in enumerate(TARGETS):f[t]=pred[:,j]
    f.to_csv(path,index=False,float_format='%.17g')

def select_training_oof(cfg,data,y,lo,hi,X,folds,native_oof,predict,out,constants=None):
    """No blind labels/predictions are accepted here. Callback sees only train targets."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True);n=len(data)
    require(y.shape==(n,4) and native_oof.shape==y.shape,'Official target/OOF shape mismatch')
    require(sorted(np.concatenate([v for _,v in folds]).tolist())==list(range(n)),'Incomplete/duplicated OOF validation coverage')
    rows=[];per=[];options={};recipes={};selected_oofs={}
    def report(name,lane,pred):
        measured=scores(y,pred,lo,hi);rows.append({'model':name,'lane':lane,**measured['macro']})
        for target,values in measured['per_cyp'].items():per.append({'model':name,'lane':lane,'target':target,**values})
        print(json.dumps({'event':'finalfit_training_OOF_metric','model':name,'lane':lane,'macro':measured['macro'],'not_independent_validation':True}),flush=True)
        return measured
    native_metrics=report('native','training_OOF_raw',native_oof)
    options['native']={'name':'native','recipe':None,'mode':'native','weight':None,'training_OOF':native_metrics}
    selected_oofs['native']=native_oof
    emit_predictions(out/'native__training_OOF.csv',data,native_oof)
    for spec in cfg['portfolio']:
        name=spec['name'];candidate_rows=[];candidate_oof={}
        for number,params in enumerate(spec['grid']):
            candidate=name+'__grid'+str(number);oof=np.full_like(y,np.nan,dtype=float)
            for fold,(train,val) in enumerate(folds):
                require(not set(train)&set(val) and set(train)<=set(range(n)) and set(val)<=set(range(n)),'Fold train/query leakage')
                for j in range(4):
                    fit=train[np.isfinite(y[train,j])];require(len(fit)>=2,'Insufficient observed labels')
                    oof[val,j]=predict(spec,params,fit,val,y[fit,j],X,cfg['model_seed'],cfg['threads'])
            require(np.isfinite(oof).all(),'Incomplete feature OOF')
            measured=report(candidate,'training_OOF_raw',oof);candidate_rows.append({'candidate':candidate,'params':params,'training_OOF':measured});candidate_oof[candidate]=oof
            emit_predictions(out/(candidate+'__training_OOF.csv'),data,oof)
        chosen=min(candidate_rows,key=lambda z:(z['training_OOF']['macro']['ST_RAE'],z['candidate']))
        oof=candidate_oof[chosen['candidate']];recipes[name]={'spec':spec,'selected':chosen,'candidates':candidate_rows}
        options[name]={'name':name,'recipe':name,'params':chosen['params'],'mode':'standalone','weight':1.0,'training_OOF':chosen['training_OOF']};selected_oofs[name]=oof
        for mode in cfg['blend_modes']:
            if mode=='global':w,details=blend_weight(y,native_oof,oof,lo,hi)
            elif mode=='per_target':
                pieces=[blend_weight(y[:,j:j+1],native_oof[:,j:j+1],oof[:,j:j+1],lo[:,j:j+1],hi[:,j:j+1]) for j in range(4)]
                w=np.array([r[0] for r in pieces]);details={'per_target_fit':dict(zip(TARGETS,[r[1] for r in pieces]))}
            else:raise ValueError('Unsupported blend mode')
            blended=native_oof+(oof-native_oof)*w;option=name+'__native_blend_'+mode
            options[option]={'name':option,'recipe':name,'params':chosen['params'],'mode':mode,'weight':w.tolist() if isinstance(w,np.ndarray) else w,'training_OOF':report(option,'training_OOF_raw',blended),'fit_details':details}
            selected_oofs[option]=blended;emit_predictions(out/(option+'__training_OOF.csv'),data,blended)
    # Raw training OOF only determines selection, before any final query inference.
    chosen=min(options.values(),key=lambda z:(z['training_OOF']['macro']['ST_RAE'],z['name']))
    selection={'chosen':chosen,'options':options,'recipes':recipes,'selection_scope':'Full official training OOF only; no outer/hidden outcomes','not_independent_validation':True,'submission_lane':cfg['submission_lane'],'configuration_sha256':hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()}
    selection_path=out/'full-data-selection.json';save(selection_path,selection)
    selected=selected_oofs[chosen['name']];emit_predictions(out/'selected__training_OOF.csv',data,selected)
    save(out/'selection-lock.json',{'selection_sha256':digest(selection_path),'selected_oof_sha256':digest(out/'selected__training_OOF.csv'),'submission_lane':cfg['submission_lane'],'final_query_inference_started':False})
    if constants is not None:
        for name,pred in selected_oofs.items():
            transformed,meta=place(y,pred,pred,TARGETS,constants)
            if transformed is not None:report(name,'published_placement_training_diagnostic',transformed)
            save(out/(name+'__placement-training-diagnostic.json'),meta)
    pd.DataFrame(rows).to_csv(out/'all-metrics-OOF.csv',index=False);pd.DataFrame(per).to_csv(out/'per-cyp-metrics-OOF.csv',index=False)
    return selection,selected

def final_predict(cfg,selection,data,y,X,query_indices,native_raw,predict,out):
    out=Path(out);locked=json.loads((out/'selection-lock.json').read_text())
    require(locked['selection_sha256']==digest(out/'full-data-selection.json'),'Selection lock changed')
    require(json.loads((out/'full-data-selection.json').read_text())==selection,'In-memory selection differs from lock')
    require(selection['submission_lane']==cfg['submission_lane']==locked['submission_lane'],'Submission lane changed after selection')
    require(selection['configuration_sha256']==hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest(),'Configuration changed after selection')
    require(not set(query_indices)&set(range(len(data))),'Blind query indices overlap training rows')
    chosen=selection['chosen']
    from datetime import datetime,timezone
    save(out/'final-query-started.json',{'utc':datetime.now(timezone.utc).isoformat(),'selected_option':chosen['name'],'final_query_inference_started':chosen['mode']!='native','uses_existing_native_only':chosen['mode']=='native','selection_sha256':locked['selection_sha256'],'query_rows':len(query_indices)})
    if chosen['mode']=='native':return native_raw.copy()
    spec=selection['recipes'][chosen['recipe']]['spec'];result=np.empty((len(query_indices),4))
    for j in range(4):
        fit=np.flatnonzero(np.isfinite(y[:,j]));require(len(fit)>=2,'Insufficient final labels')
        result[:,j]=predict(spec,chosen['params'],fit,query_indices,y[fit,j],X,cfg['model_seed'],cfg['threads'])
    require(np.isfinite(result).all(),'Final feature predictions nonfinite')
    if chosen['mode']=='standalone':return result
    return native_raw+(result-native_raw)*np.asarray(chosen['weight'])

def validate_export(frame,blind,require_spread=True):
    require(list(frame.columns)==['SMILES','Molecule_Name']+TARGETS,'Submission columns/order mismatch')
    require(len(frame)==len(blind),'Submission row count mismatch')
    require(frame.Molecule_Name.tolist()==blind.Molecule_Name.tolist(),'Submission order/IDs mismatch')
    values=align_prediction(frame,blind)
    std=values.std(axis=0,ddof=1)
    if require_spread:require(np.all(std>=.01),'Near-constant endpoint below official minimum sample SD0.01')
    return {'rows':len(frame),'exact_official_order':True,'exact_smiles':True,'finite':True,'sample_std':dict(zip(TARGETS,std.tolist())),'spread_valid':bool(np.all(std>=.01))}

def export_submission(path,blind,pred,require_spread=True):
    frame=blind[['SMILES','Molecule_Name']].copy()
    for j,t in enumerate(TARGETS):frame[t]=pred[:,j]
    receipt=validate_export(frame,blind,require_spread);frame.to_csv(path,index=False,float_format='%.17g')
    validate_export(pd.read_csv(path,float_precision='round_trip'),blind,require_spread)
    return {**receipt,'sha256':digest(path),'path':str(path)}
