"""Exact convex blend optimization and explicitly diagnostic native placement."""
import ast
from pathlib import Path
import numpy as np
from scipy.stats import pearsonr
def primary(y,p,lo,hi):
    values=[]
    for j in range(y.shape[1]):
        m=np.isfinite(y[:,j]);yy=y[m,j]
        den=(np.maximum(lo[m,j]-yy.mean(),0)+np.maximum(yy.mean()-hi[m,j],0)).sum()
        if len(yy)<2 or den<=0:raise ValueError('Undefined training ST-RAE')
        values.append((np.maximum(lo[m,j]-p[m,j],0)+np.maximum(p[m,j]-hi[m,j],0)).sum()/den)
    return float(np.mean(values))

def blend_weight(y,base,extra,lo,hi):
    points=[];weights=[]
    for j in range(y.shape[1]):
        mask=np.isfinite(y[:,j]);yy=y[mask,j]
        den=(np.maximum(lo[mask,j]-yy.mean(),0)+np.maximum(yy.mean()-hi[mask,j],0)).sum()
        if len(yy)<2 or den<=0:raise ValueError('Undefined training ST-RAE')
        b=base[mask,j];d=extra[mask,j]-b
        if not np.isfinite(b).all() or not np.isfinite(d).all():raise ValueError('Missing OOF prediction')
        active=np.abs(d)>1e-12;d=d[active];b=b[active]
        for bound in (lo[mask,j][active],hi[mask,j][active]):
            points.extend(((bound-b)/d).tolist());weights.extend((np.abs(d)/den/y.shape[1]).tolist())
    if not points:w=0.
    else:
        points=np.asarray(points);weights=np.asarray(weights);order=np.argsort(points,kind='stable')
        x=points[order];mass=weights[order];ix=np.searchsorted(np.cumsum(mass),mass.sum()/2,side='left')
        w=float(np.clip(x[min(ix,len(x)-1)],0,1))
    return w,{'native_training_OOF_ST_RAE':primary(y,base,lo,hi),'extra_training_OOF_ST_RAE':primary(y,extra,lo,hi),'blend_training_OOF_ST_RAE':primary(y,base+w*(extra-base),lo,hi),'method':'Exact weighted endpoint median; one global convex weight; smallest minimizer','fit_scope':'outer training OOF only'}

def placement_constants(path):
    wanted={'BLIND_MOMENTS','STRAE_MOMENTS','OOF_TO_BLIND','FLOOR'};values={}
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in wanted:values[target.id]=ast.literal_eval(node.value)
    if set(values)!=wanted:raise ValueError('Native placement constants not found')
    return values

def place(y_train,oof,query,targets,constants):
    result=query.copy();details={}
    for j,target in enumerate(targets):
        iso=target.split('_')[0];mask=np.isfinite(y_train[:,j]);truth=y_train[mask,j];pred=oof[mask,j]
        if len(truth)<2 or not np.isfinite(pred).all() or np.std(pred)==0 or np.std(query[:,j],ddof=1)==0:
            return None,{'defined':False,'reason':'Undefined OOF correlation or query spread','target':target}
        rho=float(pearsonr(truth,pred).statistic)*constants['OOF_TO_BLIND'][iso]
        moments=constants['STRAE_MOMENTS'].get(iso,constants['BLIND_MOMENTS'][iso])
        target_sd=moments['sd'] if iso in constants['STRAE_MOMENTS'] else rho*moments['sd']
        if not np.isfinite(target_sd) or target_sd<=0:return None,{'defined':False,'reason':'Nonpositive published placement scale','target':target}
        mean=query[:,j].mean();scale=target_sd/query[:,j].std(ddof=1)
        values=moments['mean']+scale*(query[:,j]-mean)
        result[:,j]=np.maximum(values,constants['FLOOR'])
        details[target]={'oof_to_blind_pearson':rho,'scale':float(scale),'offset':float(moments['mean']-mean),'floor_count':int((values<constants['FLOOR']).sum())}
    return result,{'defined':True,'diagnostic_only':True,'uses_published_leaderboard_derived_constants':True,'fit_outer_labels':False,'per_cyp':details}
