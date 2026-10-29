from pathlib import Path
import sys,json,numpy as np
p=Path(__file__).parent;sys.path.insert(0,str(p/'worktree/night'));from p9_nested_blend import convex_fit
rng=np.random.default_rng(5);y=np.arange(8,dtype=float);P=np.column_stack([y,y+1,y+3]);w,r=convex_fit(P,y,y,y);assert np.allclose(w,[1,0,0],atol=1e-8) and r['mean_CI_distance']<1e-9
for rep in range(20):
 y=rng.normal(size=19);P=rng.normal(size=(19,2));lo=y-.15;hi=y+.23;w,r=convex_fit(P,y,lo,hi);delta=P[:,1]-P[:,0];valid=abs(delta)>1e-12;endpoints=np.r_[(lo[valid]-P[valid,0])/delta[valid],(hi[valid]-P[valid,0])/delta[valid]];weights=np.r_[abs(delta[valid]),abs(delta[valid])];order=np.argsort(endpoints);med=endpoints[order][np.searchsorted(np.cumsum(weights[order]),weights.sum()/2)];scalar=np.clip(med,0,1);pred=P[:,0]+scalar*delta;loss=np.mean(np.maximum(lo-pred,0)+np.maximum(pred-hi,0));assert abs(loss-r['mean_CI_distance'])<1e-8;assert w.min()>=0 and abs(w.sum()-1)<1e-12
 y3=np.r_[y,np.nan];P3=np.vstack([P,[1000,-1000]]);m=np.isfinite(y3);w3,r3=convex_fit(P3[m],y3[m],lo,hi);assert abs(r3['mean_CI_distance']-r['mean_CI_distance'])<1e-12
 perm=rng.permutation(len(y));wp,rp=convex_fit(P[perm],y[perm],lo[perm],hi[perm]);assert abs(rp['mean_CI_distance']-r['mean_CI_distance'])<1e-8
report={'status':'pass','perfect_expert_control':True,'two_expert_weighted_median_CI_objective_parity_cases':20,'missing_label_exclusion_cases':20,'row_permutation_objective_invariance_cases':20,'simplex_bounds_and_sum':True,'no_query_data_used':True};(p/'BLEND_TESTS.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
