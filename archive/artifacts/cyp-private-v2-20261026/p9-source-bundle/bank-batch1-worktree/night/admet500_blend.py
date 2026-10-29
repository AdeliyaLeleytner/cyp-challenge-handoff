"""One scalar convex stacking weight fitted only on outer-training OOF predictions."""
from pathlib import Path
import json,time,warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from threadpoolctl import threadpool_limits
from .admet500_pilot import prepare,predict,old_base_predictions,scores,save_prediction,save,event,TARGETS

def primary(y,p,lo,hi):
    values=[]
    for j in range(4):
        m=np.isfinite(y[:,j]);yy=y[m,j];den=(np.maximum(lo[m,j]-yy.mean(),0)+np.maximum(yy.mean()-hi[m,j],0)).sum()
        if len(yy)<2 or den<=0:return float('nan')
        values.append(float((np.maximum(lo[m,j]-p[m,j],0)+np.maximum(p[m,j]-hi[m,j],0)).sum()/den))
    return float(np.mean(values))

def fit_weight(y,base,extra,lo,hi):
    mask=np.isfinite(y);assert np.isfinite(base[mask]).all() and np.isfinite(extra[mask]).all()
    delta=extra-base;points=[0.,1.]
    for bound in [lo,hi]:
        use=mask&np.isfinite(delta)&(np.abs(delta)>1e-12)
        candidates=(bound-base)[use]/delta[use]
        points.extend(candidates[(candidates>=0)&(candidates<=1)].tolist())
    points=np.unique(points);values=np.array([primary(y,base+w*delta,lo,hi) for w in points])
    minimum=values.min();weight=float(points[np.flatnonzero(values<=minimum+1e-12)[0]])
    return weight,{'training_OOF_ST_RAE_native':primary(y,base,lo,hi),'training_OOF_ST_RAE_admet':primary(y,extra,lo,hi),
        'training_OOF_ST_RAE_blend':float(minimum),'candidate_breakpoints':len(points),'weight_scope':'one global scalar shared byfour targets','tie_rule':'smallest ADMET weight amongnumerically tied minima'}

def run(cfg):
    started=time.time();out=Path(cfg['output_dir']);paths,data,fp,rd,ad,columns,y,lo,hi,groups,cohorts=prepare(cfg)
    X={'fp':fp,'rd':rd,'admet':ad,'structure':np.column_stack([fp,rd])};results={};summary=[];intervals=[]
    for cohort,c in cohorts.items():
        train=np.flatnonzero(data.Molecule_Name.isin(c['train_ids']));test=np.flatnonzero(data.Molecule_Name.isin(c['test_ids']))
        native_oof,native_test=old_base_predictions(paths,cohort,data)
        base=native_test[test];frame=data.iloc[test].reset_index(drop=True)
        assert not set(data.iloc[train].connectivity)&set(data.iloc[test].connectivity)
        strata=(np.isfinite(y[train])*np.array([1,2,4,8])).sum(1)
        splits=list(StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=42).split(np.zeros(len(train)),strata,groups[train]))
        save(out/(cohort+'_inner-folds.json'),[{'train_ids':data.iloc[train[a]].Molecule_Name.tolist(),'validation_ids':data.iloc[train[b]].Molecule_Name.tolist()} for a,b in splits])
        base_result=scores(y[test],base,lo[test],hi[test]);results[cohort+'/native']=base_result
        summary.append({'cohort':cohort,'model':'native','admet_weight':0.,**base_result['macro']})
        for family in ['extratrees','lightgbm','kernel']:
            oof=np.full_like(y,np.nan)
            for a,b in splits:
                tr,va=train[a],train[b];assert not set(groups[tr])&set(groups[va])
                for j in range(4):
                    fit=tr[np.isfinite(y[tr,j])];oof[va,j]=predict(family,'admet',fit,va,y[fit,j],X,42)
            w,fit_info=fit_weight(y[train],native_oof[train],oof[train],lo[train],hi[train])
            extra=np.empty_like(base)
            for j in range(4):
                fit=train[np.isfinite(y[train,j])];extra[:,j]=predict(family,'admet',fit,test,y[fit,j],X,42)
            blend=(1-w)*base+w*extra;result=scores(y[test],blend,lo[test],hi[test])
            name='native_plus_'+family;results[cohort+'/'+name]=result
            summary.append({'cohort':cohort,'model':name,'admet_weight':w,**result['macro']})
            save_prediction(out,cohort+'_'+name,frame,blend);save_prediction(out,cohort+'_'+family+'_training_OOF',data.iloc[train],oof[train])
            save(out/(cohort+'_'+family+'_weight.json'),{'admet_weight':w,**fit_info,'fit_ids':data.iloc[train].Molecule_Name.tolist(),'excluded_evaluation_ids':frame.Molecule_Name.tolist()})
            group_values=np.unique(groups[test]);members=[np.flatnonzero(groups[test]==g) for g in group_values];rng=np.random.default_rng(20261025);delta=[]
            for _ in range(cfg['bootstrap_samples']):
                ix=np.concatenate([members[k] for k in rng.integers(0,len(members),len(members))])
                d=primary(y[test][ix],blend[ix],lo[test][ix],hi[test][ix])-primary(y[test][ix],base[ix],lo[test][ix],hi[test][ix])
                if np.isfinite(d):delta.append(d)
            intervals.append({'cohort':cohort,'model':name,'delta_ST_RAE':result['macro']['ST_RAE']-base_result['macro']['ST_RAE'],
                'lower95':float(np.quantile(delta,.025)),'upper95':float(np.quantile(delta,.975)),'valid_bootstraps':len(delta),'requested_bootstraps':cfg['bootstrap_samples'],'admet_weight':w})
            event('convex_blend_complete',cohort=cohort,model=name,weight=w,fit=fit_info,held_out=result['macro'])
    pd.DataFrame(summary).to_csv(out/'all-metrics.csv',index=False);pd.DataFrame(intervals).to_csv(out/'paired-deltas.csv',index=False)
    save(out/'scores.json',results);save(out/'complete.json',{'status':'complete','seconds':time.time()-started,'no_holdout_weight_fitting':True,'form':'(1-w)*native+w*ADMET_only; one scalar w selected on training OOF only'})
    event('convex_pilot_complete',summary=summary,seconds=round(time.time()-started,1))

if __name__=='__main__':
    warnings.filterwarnings('ignore',message='X does not have valid feature names')
    with threadpool_limits(limits=2):run(json.loads(Path('pilot_config.json').read_text()))
