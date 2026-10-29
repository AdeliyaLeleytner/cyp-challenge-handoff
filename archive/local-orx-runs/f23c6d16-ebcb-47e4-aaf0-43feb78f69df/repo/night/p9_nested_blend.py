"""Predeclared convex CI-distance blending using outer-training OOF only."""
import json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from scipy.optimize import linprog
from scipy.sparse import hstack,vstack,eye,csr_matrix
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from p9_tabicl_aggregate import score,EP,MET

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def convex_fit(P,y,low,high):
 assert P.ndim==2 and len(P)==len(y)>0 and np.isfinite(P).all() and np.isfinite(y).all() and np.isfinite(low).all() and np.isfinite(high).all() and (low<=high).all();n,k=P.shape
 A=vstack([hstack([-csr_matrix(P),-eye(n)]),hstack([csr_matrix(P),-eye(n)])],format='csr');rhs=np.r_[-low,high];cost=np.r_[np.zeros(k),np.ones(n)/n];eq=csr_matrix(np.r_[np.ones(k),np.zeros(n)][None,:]);result=linprog(cost,A_ub=A,b_ub=rhs,A_eq=eq,b_eq=[1.],bounds=[(0,1)]*k+[(0,None)]*n,method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9});assert result.success,result.message;raw=result.x[:k];w=np.clip(raw,0,1);w/=w.sum();assert np.max(abs(w-raw))<1e-8 and w.min()>=0 and abs(w.sum()-1)<1e-12;p=P@w;loss=np.mean(np.maximum(low-p,0)+np.maximum(p-high,0));den=np.mean(np.maximum(low-y.mean(),0)+np.maximum(y.mean()-high,0));assert den>0 and abs(loss-result.fun)<1e-8
 return w,{'weights':w.tolist(),'solver_raw_weights':raw.tolist(),'mean_CI_distance':float(loss),'training_ST_RAE':float(loss/den),'training_denominator':float(den),'observed':n,'solver':'scipyHiGHS','objective_reconstruction_error':float(loss-result.fun)}
def fixed_map(P,op):
 mu=np.asarray(op['original_raw_reference_mean']);return np.column_stack([np.maximum(mu[j]+op['calibration'][e]['scale']*(P[:,j]-mu[j])+op['calibration'][e]['offset'],op['floor']) for j,e in enumerate(EP)])
def checked_vector(record,ids,truth,columns):
 assert sha(record['path'])==record['sha256'];d=pd.read_csv(record['path']).set_index('Molecule_Name');assert d.index.is_unique and set(d.index)==set(ids);d=d.loc[ids];assert d.SMILES.tolist()==truth.loc[ids,'SMILES'].tolist();a=d[columns].to_numpy();assert np.isfinite(a).all();return a

def run_nested(c):
 out=Path(c['output']);m=json.load(open(c['files']['nested_manifest']['path']));truth=pd.read_csv(c['files']['official']['path']).set_index('Molecule_Name');T=[e+'_pIC50_direct_inhibition' for e in EP];L=[t+'_conf_low' for t in T];H=[t+'_conf_high' for t in T];ops={x['context']:x for x in json.load(open(c['files']['frozen_serving_maps']['path']))};all_metrics=[];all_deltas=[];all_weights={};rng=np.random.default_rng(20261026);inputpins={}
 for name,spec in m['cohorts'].items():
  train_ids=spec['train_ids'];query_ids=spec['query_ids'];trtruth=truth.loc[train_ids];Y=trtruth[T].to_numpy(float);lo=trtruth[L].to_numpy(float);hi=trtruth[H].to_numpy(float);native=checked_vector(spec['native_oof'],train_ids,truth,EP);train_features={'native':native};positions={x:i for i,x in enumerate(train_ids)}
  for rep in ['adme600','atomjepa256']:
   bank=np.full((len(train_ids),4),np.nan);seen=[]
   for fold in spec['inner_folds']:
    val=fold['val_ids'];seen+=val
    for j in range(4):
     path=out/f'{rep}-f{name}_inner{fold["fold"]}-target{j}.csv';d=pd.read_csv(path).set_index('molecule_name');assert d.index.is_unique and set(d.index)==set(val);d=d.loc[val];assert d.smiles.tolist()==truth.loc[val,'SMILES'].tolist();bank[[positions[x] for x in val],j]=d.prediction.to_numpy();inputpins[path.name]=sha(path)
   assert len(seen)==len(set(seen))==len(train_ids) and set(seen)==set(train_ids) and np.isfinite(bank).all();train_features[rep]=bank;df=trtruth[['SMILES']].reset_index()
   for j,e in enumerate(EP):df[e]=bank[:,j]
   df.to_csv(out/f'{name}-{rep}-inner-OOF.csv',index=False,float_format='%.17g')
  weights={'incumbent':np.tile([1.,0.,0.],(4,1)),'native_adme':np.zeros((4,3)),'three_experts':np.zeros((4,3))};receipts={}
  for j,e in enumerate(EP):
   observed=np.isfinite(Y[:,j]);P=np.column_stack([train_features[x][observed,j] for x in ['native','adme600','atomjepa256']]);two,r2=convex_fit(P[:,:2],Y[observed,j],lo[observed,j],hi[observed,j]);three,r3=convex_fit(P,Y[observed,j],lo[observed,j],hi[observed,j]);weights['native_adme'][j,:2]=two;weights['three_experts'][j]=three;receipts[e]={'native_adme':r2,'three_experts':r3}
  weight_record={'cohort':name,'experts':['original_native','adme600_tabicl','atomjepa256_tabicl'],'weights':{k:v.tolist() for k,v in weights.items()},'training_fit':receipts,'train_ids_sha256':hashlib.sha256('\n'.join(train_ids).encode()).hexdigest(),'query_labels_used_for_weight_fit':False,'no_intercept_or_negative_weights':True,'boundary_control_predeclared':True};weightfile=out/f'{name}-weights.json';weightfile.write_text(json.dumps(weight_record,indent=2)+'\n');all_weights[name]=weight_record
  # Query truth is first selected here, after coefficients have been persisted.
  qtruth=truth.loc[query_ids];qy=qtruth[T].to_numpy(float);ql=qtruth[L].to_numpy(float);qh=qtruth[H].to_numpy(float);query_features=[checked_vector(spec['native_query'],query_ids,truth,T)]+[checked_vector(spec['p9_query'][x],query_ids,truth,EP) for x in ['adme600','atomjepa256']];Q=np.stack(query_features,axis=2);raw={key:np.einsum('ntk,tk->nt',Q,w) for key,w in weights.items()};assert np.array_equal(raw['incumbent'],query_features[0]);served_reference=pd.read_csv(c['files'][name+'_native_served']['path']).set_index('Molecule_Name').loc[query_ids,T].to_numpy();assert np.allclose(fixed_map(raw['incumbent'],ops[name]),served_reference,rtol=0,atol=1e-12)
  groups=np.array([Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(Chem.MolFromSmiles(s))) for s in qtruth.SMILES],dtype=object);strata=[np.where(groups==g)[0] for g in sorted(set(groups))];draws=[np.concatenate([strata[i] for i in rng.integers(0,len(strata),len(strata))]) for _ in range(1000)]
  for lane in ['raw','fixed_original_served_diagnostic']:
   vectors=raw if lane=='raw' else {k:fixed_map(v,ops[name]) for k,v in raw.items()};points={};bootstrap={}
   for arm,P in vectors.items():
    frame=qtruth[['SMILES']].reset_index()
    for j,e in enumerate(EP):frame[e]=P[:,j]
    frame.to_csv(out/f'{name}-{lane}-{arm}.csv',index=False,float_format='%.17g');points[arm]=score(qy,P,ql,qh);bootstrap[arm]=np.array([score(qy[ii],P[ii],ql[ii],qh[ii]) for ii in draws])
    for j,e in enumerate(EP+['macro']):
     for k,met in enumerate(MET):all_metrics.append({'cohort':name,'lane':lane,'arm':arm,'endpoint':e,'metric':met,'value':points[arm][j,k]})
   for candidate,control in [('native_adme','incumbent'),('three_experts','incumbent'),('three_experts','native_adme')]:
    delta=points[candidate]-points[control];low,high=np.quantile(bootstrap[candidate]-bootstrap[control],[.025,.975],axis=0)
    for j,e in enumerate(EP+['macro']):
     for k,met in enumerate(MET):all_deltas.append({'cohort':name,'lane':lane,'contrast':candidate+' minus '+control,'endpoint':e,'metric':met,'delta':delta[j,k],'lower95':low[j,k],'upper95':high[j,k]})
  print(json.dumps({'nested_blend_complete':name,'weights':weight_record['weights'],'raw_macro':{k:score(qy,v,ql,qh)[-1].tolist() for k,v in raw.items()}}),flush=True)
 pd.DataFrame(all_metrics).to_csv(out/'blend-metrics.csv',index=False);pd.DataFrame(all_deltas).to_csv(out/'blend-paired-deltas.csv',index=False);(out/'BLEND_COMPLETE.json').write_text(json.dumps({'status':'complete','weights':all_weights,'inner_prediction_hashes':inputpins,'base_calls':80,'outer_query_route':'previouslyfrozenfullcontextP9vectors;originalnativeunchanged','bootstrap':1000,'bootstrap_seed':20261026,'raw_primary':True,'serving_lane_is_population_mismatched_diagnostic':True,'historical_expert_limits':m['historical_limits'],'no_new_native_fit':True,'no_publication':True,'no_submission':True,'source_sha256':sha(__file__)},indent=2)+'\n')
