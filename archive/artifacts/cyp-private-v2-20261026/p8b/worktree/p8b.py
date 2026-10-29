from pathlib import Path
import json,hashlib,time,sys,platform,importlib.metadata
import numpy as np,pandas as pd

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def design(z,knots):return np.column_stack([np.ones(len(z)),z]+[np.maximum(z-k,0) for k in knots])
def fit(x,y,kind):
 xm=float(x.mean());xs=float(x.std());ym=float(y.mean());ys=float(y.std());assert xs>0 and ys>0
 basis='spline' if kind.startswith('spline') else 'affine';alpha=float(kind.rsplit('_',1)[1]) if kind!='mean' else None
 z=(x-xm)/xs;v=(y-ym)/ys;knots=np.quantile(z,[.25,.5,.75]) if basis=='spline' else np.array([]);X=design(z,knots)
 if kind=='mean':coef=np.array([0.,0.]);rank=1
 elif alpha==0:
  coef,_,rank,_=np.linalg.lstsq(X,v,rcond=None)
 else:
  pen=np.eye(X.shape[1]);pen[0,0]=0;coef=np.linalg.solve(X.T@X/len(x)+alpha*pen,X.T@v/len(x));rank=np.linalg.matrix_rank(X)
 return dict(kind=kind,design_rank=int(rank),basis=basis,alpha_mean_mse=alpha,x_mean=xm,x_scale=xs,y_mean=ym,y_scale=ys,knots=knots.tolist(),coefficients=coef.tolist(),fit_min=float(x.min()),fit_max=float(x.max()))
def predict(m,x):return m['y_mean']+m['y_scale']*(design((x-m['x_mean'])/m['x_scale'],m['knots'])@np.array(m['coefficients']))
def main():
 start=time.time();cfg=json.loads(Path('p8b_config.json').read_text());assert cfg['knots_quantiles']==[.25,.5,.75] and cfg['alphas_mean_mse']==[0,1];out=Path(cfg['output']);out.mkdir(exist_ok=False,parents=True)
 for p,h in cfg['input_hashes'].items():assert sha(p)==h,(p,'input hash mismatch')
 d=pd.read_csv(cfg['table']);a=pd.read_csv(cfg['active']).set_index('molecule_name');manifest=json.loads(Path(cfg['folds']).read_text());pairs=pd.read_csv(cfg['pairs']);assert d.molecule_name.is_unique and a.index.is_unique
 par={}
 def find(v):
  par.setdefault(v,v)
  if par[v]!=v:par[v]=find(par[v])
  return par[v]
 for ids in pairs[pairs.stereo_preserving_tautomer_key_equal==True].request_ids.str.split(';'):
  for rid in ids[1:]:par[find(ids[0])]=find(rid)
 equiv=np.array([find(r) for r in d.request_id]);original=np.full(len(d),-1)
 for k,f in enumerate(manifest['folds']):
  assert np.all(original[f['test']]==-1);original[f['test']]=k
 assert np.all(original>=0)
 metrics=[];preds=[];models=[];membership=[];shapes=[];selected=[];selector_membership=[]
 print(json.dumps({'event':'effective_config','config':cfg,'original_groups':'P7 test assignments, identical original folds','outer_holdout_outcomes_used':False,'alpha_objective':'mean standardized squared residual + alpha0 or alpha1 nonintercept coefficient L2','factorial':'affine and same spline, each alpha0/1; mean reference','runtime':{'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__}}),flush=True)
 for outer,f in enumerate(manifest['folds']):
  tr=np.array(f['train']);forbidden=set(f['stop'])|set(f['test']);assert not set(tr)&forbidden;groups=sorted(int(v) for v in set(original[tr]));assert len(groups)==3
  for c in cfg['targets']:
   y=d[c+'_log2fc'].to_numpy(float);x=a[c+'_pic50_tdi_condition'].reindex(d.molecule_name).to_numpy(float);valid=np.isfinite(x)&np.isfinite(y);pool=tr[valid[tr]]
   for group in groups:
    val=pool[original[pool]==group];candidate=pool[original[pool]!=group];blocked=set(equiv[val]);train=np.array([i for i in candidate if equiv[i] not in blocked],int);assert not set(equiv[train])&set(equiv[val]);assert set(train)|set(val)<=set(tr);assert not (set(train)|set(val))&forbidden;assert len(train)>10 and len(val)>5
    key=f'outer{outer}_{c}_heldgroup{group}'
    for role,ix in [('fit',train),('validation',val)]:
     membership += [{'key':key,'outer_fold':outer,'target':c,'inner_held_group':int(group),'role':role,'row_index':int(i),'original_group':int(original[i]),'molecule_name':d.molecule_name.iloc[i],'request_id':d.request_id.iloc[i],'equivalence_group':equiv[i]} for i in ix]
    grid=np.linspace(float(x[pool].min()),float(x[pool].max()),101)
    for kind in cfg['models']:
     m=fit(x[train],y[train],kind);yp=predict(m,x[val]);err=yp-y[val];ex=(x[val]<x[train].min())|(x[val]>x[train].max());row={'key':key,'outer_fold':outer,'target':c,'inner_held_group':int(group),'model':kind,'n_fit':len(train),'n_validation':len(val),'inner_equivalence_purged':len(candidate)-len(train),'mae':float(np.abs(err).mean()),'rmse':float(np.sqrt((err**2).mean())),'bias':float(err.mean()),'extrapolation_n':int(ex.sum()),'extrapolation_fraction':float(ex.mean()),'extrapolation_mae':float(np.abs(err[ex]).mean()) if ex.any() else None,'interpolation_mae':float(np.abs(err[~ex]).mean()) if (~ex).any() else None};metrics.append(row)
     slopes=np.r_[m['coefficients'][1],m['coefficients'][1]+np.cumsum(m['coefficients'][2:])]*m['y_scale']/m['x_scale'];models.append({'key':key,**m,'raw_segment_slopes':slopes.tolist(),'monotonic_increasing':bool(np.all(slopes>=0)),'monotonic_decreasing':bool(np.all(slopes<=0)),'fit_ids_sha256':hashlib.sha256('\n'.join(d.molecule_name.iloc[train]).encode()).hexdigest()})
     preds += [{'key':key,'outer_fold':outer,'target':c,'inner_held_group':int(group),'model':kind,'molecule_name':d.molecule_name.iloc[i],'request_id':d.request_id.iloc[i],'active_pic50':float(x[i]),'screen':float(y[i]),'prediction':float(p),'extrapolation':bool(e)} for i,p,e in zip(val,yp,ex)]
     shapes += [{'key':key,'outer_fold':outer,'target':c,'inner_held_group':int(group),'model':kind,'active_pic50':float(xx),'predicted_screen':float(pp)} for xx,pp in zip(grid,predict(m,grid))]
   # Choose only using this outer-training partition's inner held-out outcomes.
   candidates=[]
   for kind in cfg['models']:
    subset=[r for r in metrics if r['outer_fold']==outer and r['target']==c and r['model']==kind]
    denom=sum(r['n_validation'] for r in subset);criterion=sum(r['mae']*r['n_validation'] for r in subset)/denom
    candidates.append({'model':kind,'inner_mae':criterion,'n_validation_occurrences':denom})
   winner=min(candidates,key=lambda r:(r['inner_mae'],cfg['models'].index(r['model'])))['model'];refit=fit(x[pool],y[pool],winner)
   selected.append({'outer_fold':outer,'target':c,'selected_model':winner,'candidate_inner_errors':candidates,'selection_rule':'outer-local sample-weighted inner MAE; exact ties use committed candidate order','selection_error_is_not_unbiased_generalization':True,'fit_count':len(pool),'fit_ids_sha256':hashlib.sha256('\n'.join(d.molecule_name.iloc[pool]).encode()).hexdigest(),'map':refit})
   selector_membership += [{'outer_fold':outer,'target':c,'row_index':int(i),'molecule_name':d.molecule_name.iloc[i],'request_id':d.request_id.iloc[i],'original_group':int(original[i]),'equivalence_group':equiv[i]} for i in pool]
   print(json.dumps({'event':'outer_target_complete','outer_fold':outer,'target':c,'paired_training_rows':len(pool),'inner_groups':groups}),flush=True)
 for name,data in [('metrics',metrics),('predictions',preds),('membership',membership),('map_grid',shapes)]:pd.DataFrame(data).to_csv(out/(name+'.csv'),index=False)
 assert sha(out/'membership.csv')==sha(cfg['p8a_membership']), 'P8a membership changed'
 (out/'selected_maps.json').write_text(json.dumps(selected,indent=2)+'\n');pd.DataFrame(selector_membership).to_csv(out/'selector_membership.csv',index=False)
 (out/'models.json').write_text(json.dumps(models,indent=2)+'\n');v=pd.DataFrame(preds);summ=[]
 for (c,kind),g in v.groupby(['target','model']):
  err=g.prediction-g.screen;summ.append({'target':c,'model':kind,'evaluated_occurrences':len(g),'unique_molecules':g.molecule_name.nunique(),'mae':float(abs(err).mean()),'rmse':float(np.sqrt((err**2).mean())),'bias':float(err.mean()),'extrapolation_fraction':float(g.extrapolation.mean())})
 pd.DataFrame(summ).to_csv(out/'summary.csv',index=False);receipt={'status':'complete','seconds':time.time()-start,'outer_folds':5,'inner_groups_per_outer':3,'targets':4,'crossfit_maps_fitted':len(models),'refit_selected_maps':len(selected),'outer_stop_test_outcomes_used':False,'overlapping_outer_training_evaluations_not_independent':True,'global_selection':False,'outer_training_local_selection':True,'no_kinetic_interpretation':True,'config_sha256':sha('p8b_config.json'),'source_sha256':sha(__file__),'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()}};(out/'complete.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'event':'final_summary','summary':summ,'selections':[{'outer_fold':v['outer_fold'],'target':v['target'],'selected_model':v['selected_model']} for v in selected],'receipt':receipt}),flush=True)
if __name__=='__main__':main()
