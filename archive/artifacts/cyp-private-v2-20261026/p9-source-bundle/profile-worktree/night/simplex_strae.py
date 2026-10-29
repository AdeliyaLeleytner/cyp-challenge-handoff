"""Exact CI-distance macro ST-RAE over one global convex expert mixture."""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,hstack,vstack,eye

def fit_simplex(y,predictions,low,high):
    """Return weights[K], metadata; predictions has shape[N,T,K]. No query labels accepted."""
    y=np.asarray(y,float);p=np.asarray(predictions,float);lo=np.asarray(low,float);hi=np.asarray(high,float)
    if y.ndim!=2 or p.ndim!=3 or p.shape[:2]!=y.shape or lo.shape!=y.shape or hi.shape!=y.shape or p.shape[2]<2:raise ValueError('Invalid aligned array shapes')
    observed=np.isfinite(y);den=[];counts=[]
    if not np.isfinite(p[observed]).all() or not np.isfinite(lo[observed]).all() or not np.isfinite(hi[observed]).all() or np.any(lo[observed]>hi[observed]):raise ValueError('Invalid observed prediction/bounds')
    for j in range(y.shape[1]):
        m=observed[:,j];yy=y[m,j];d=(np.maximum(lo[m,j]-yy.mean(),0)+np.maximum(yy.mean()-hi[m,j],0)).sum() if len(yy) else 0
        if len(yy)<2 or not np.isfinite(d) or d<=0:raise ValueError('Undefined training denominator')
        den.append(d);counts.append(int(m.sum()))
    row,target=np.nonzero(observed);e=p[row,target,:];n,k=e.shape
    # Slacks are distance to the interval: max(lower-prediction,prediction-upper,0).
    a=csr_matrix(e);negI=-eye(n,format='csr')
    A=vstack([hstack([a,negI]),hstack([-a,negI])],format='csr')
    b=np.concatenate([hi[row,target],-lo[row,target]])
    c=np.r_[np.zeros(k),1/(y.shape[1]*np.asarray(den)[target])]
    equality=csr_matrix((np.ones(k),(np.zeros(k,dtype=int),np.arange(k))),shape=(1,k+n))
    result=linprog(c,A_ub=A,b_ub=b,A_eq=equality,b_eq=[1.],bounds=[(0,1)]*k+[(0,None)]*n,method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9,'ipm_optimality_tolerance':1e-10})
    if not result.success:raise RuntimeError('Simplex LP failed: '+result.message)
    w=result.x[:k]
    if not np.isfinite(w).all() or np.any(w<0) or np.any(w>1) or abs(w.sum()-1)>1e-8:raise RuntimeError('Invalid fitted simplex')
    q=e@w;error=np.maximum(lo[row,target]-q,0)+np.maximum(q-hi[row,target],0);actual=float(np.dot(c[k:],error))
    if abs(actual-result.fun)>1e-8:raise RuntimeError('LP and rescored objective mismatch')
    return w,{'method':'sparse HiGHS linear program; interval-distance exact macro ST-RAE','weight_scope':'one global simplex shared across targets','solver_status':int(result.status),'solver_message':result.message,'solver_iterations':int(result.nit),'training_OOF_ST_RAE':actual,'solver_objective':float(result.fun),'target_denominators':list(map(float,den)),'observed_per_target':counts,'sum_weights':float(w.sum()),'maximum_constraint_violation':float(max(0,np.max(A@result.x-b))),'tie_policy':'Deterministic solver result for frozen row/expert order; no outer selection or secondary fit'}
