"""Fixed tabular/frozen-encoder portfolio; all transformations fit inside training partitions."""
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics.pairwise import rbf_kernel
from lightgbm import LGBMRegressor

def transform(a,b,scale=True,return_objects=False):
    imputer=SimpleImputer(strategy='median',keep_empty_features=True)
    a=imputer.fit_transform(a);b=imputer.transform(b)
    fitted={'imputer':imputer,'scaler':None}
    if scale:
        scaler=StandardScaler();a=scaler.fit_transform(a);b=scaler.transform(b);fitted['scaler']=scaler
        a=np.clip(a,-20,20);b=np.clip(b,-20,20)
    return (a,b,fitted) if return_objects else (a,b)

def tanimoto(a,b):
    numerator=a@b.T;den=a.sum(1)[:,None]+b.sum(1)[None,:]-numerator
    return np.divide(numerator,den,out=np.zeros_like(numerator),where=den>0)

def feature_groups(columns):
    cyp=np.array([name.startswith('ADMETLAB::metabolism::CYP') for name in columns])
    if len(columns)!=120 or int(cyp.sum())!=13:raise ValueError('Expected120 features with13 prespecified CYP endpoints')
    return {'cyp_only':np.flatnonzero(cyp),'non_cyp':np.flatnonzero(~cyp)}

def predict(spec,params,train,query,target,X,seed,threads,artifact=None):
    family,view=spec['family'],spec['view']
    if family=='kernel':
        def block(key,kind):
            a,b=X[key][train],X[key][query]
            if kind=='tanimoto':return tanimoto(a,a),tanimoto(b,a)
            a,b=transform(a,b);gamma=.5/a.shape[1]
            return rbf_kernel(a,a,gamma=gamma),rbf_kernel(b,a,gamma=gamma)
        if view!='admet':
            kf,qf=block('fp','tanimoto');kr,qr=block('rd','rbf');ks,qs=.75*kf+.25*kr,.75*qf+.25*qr
        if view!='structure':ka,qa=block('admet','rbf')
        if view=='admet':k,q=ka,qa
        elif view=='structure':k,q=ks,qs
        else:k,q=.5*(ks+ka),.5*(qs+qa)
        center=target.mean();return center+q@np.linalg.solve(k+np.eye(len(train))*params['alpha'],target-center)
    if family=='chemeleon_ridge':
        a,b=transform(X['chemeleon'][train],X['chemeleon'][query]);a/=np.sqrt(a.shape[1]);b/=np.sqrt(b.shape[1])
        if view=='augmented':
            aa,bb=transform(X['admet'][train],X['admet'][query]);aa/=np.sqrt(aa.shape[1]);bb/=np.sqrt(bb.shape[1])
            a=np.column_stack([a,aa])/np.sqrt(2);b=np.column_stack([b,bb])/np.sqrt(2)
        return Ridge(alpha=params['alpha']).fit(a,target).predict(b)
    if family!='lightgbm':raise ValueError(family)
    if view in ('adme','adme_admet'):features=X[view]
    elif view in ('cyp_only','non_cyp'):features=X['admet'][:,X['admet_groups'][view]]
    else:features={'admet':X['admet'],'structure':X['structure'],'augmented':np.column_stack([X['structure'],X['admet']])}[view]
    if artifact is not None:
        from .final_model_artifacts import identity,reuse,persist
        expected=identity(spec,params,train,query,target,features,seed,threads,artifact)
        cached=reuse(artifact,expected,features[query])
        if cached is not None:return cached
        a,b,preprocessing=transform(features[train],features[query],False,True)
    else:a,b=transform(features[train],features[query],False)
    model=LGBMRegressor(n_estimators=220,num_leaves=params['num_leaves'],max_depth=params['max_depth'],min_child_samples=10,learning_rate=.03,reg_lambda=5,objective='regression_l1',verbosity=-1,n_jobs=threads,random_state=seed,force_col_wise=True)
    prediction=model.fit(a,target).predict(b)
    if artifact is not None:return persist(artifact,expected,model,preprocessing,features[query],prediction)
    return prediction
