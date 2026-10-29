"""Exact scorer and native-vector reader copied from CPU evaluator at 6b3ff843ff40b02ac679f305988aabfefb92dcd5."""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr,kendalltau
from official_scoring_functions import rae_soft_threshold_absolute_error
TARGETS=[f"{x}_pIC50_direct_inhibition" for x in ("CYP1A2","CYP2C9","CYP2D6","CYP3A4")]

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
