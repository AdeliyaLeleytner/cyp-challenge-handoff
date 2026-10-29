from pathlib import Path
import json,hashlib,sqlite3
import numpy as np,pandas as pd
from scipy.optimize import linprog
from scipy.sparse import hstack,vstack,eye,csr_matrix
from scipy.stats import spearmanr,kendalltau
from sklearn.metrics import r2_score
p=Path(__file__).parent;out=p/'results';m=json.load(open(p/'stage/manifest.json'));truth=pd.read_csv(m['files']['official_train']['path']).set_index('Molecule_Name');T=[f'{e}_pIC50_direct_inhibition' for e in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']];EP=[x.split('_')[0] for x in T];metrics=pd.read_csv(out/'metrics.csv');per=pd.read_csv(out/'per-cyp-metrics.csv');maxerr=0.;lp_errors=[];native_hashes=[]
def score(y,p,l,h):return {'ST_RAE':float(abs(p-np.clip(p,l,h)).sum()/abs(y.mean()-np.clip(y.mean(),l,h)).sum()),'MAE':float(abs(p-y).mean()),'R2':float(r2_score(y,p)),'Spearman':float(spearmanr(y,p).statistic),'Kendall':float(kendalltau(y,p).statistic)}
for name,spec in m['cohorts'].items():
 tr=spec['train_ids'];qu=spec['query_ids'];wr=json.load(open(out/f'{name}-weights.json'));N=pd.read_csv(spec['native_oof']['path']).set_index('Molecule_Name').loc[tr,EP].to_numpy();H=pd.read_csv(spec['h6_oof']['path']).set_index('Molecule_Name').loc[tr,T].to_numpy();weights=np.asarray(wr['refit_original_OOF']);assert np.isfinite(weights).all() and ((weights>=0)&(weights<=1)).all()
 for j,t in enumerate(T):
  observed=truth.loc[tr,t].notna();y=truth.loc[tr,t][observed].to_numpy();lo=truth.loc[tr,t+'_conf_low'][observed].to_numpy();hi=truth.loc[tr,t+'_conf_high'][observed].to_numpy();base=N[observed,j];extra=H[observed,j];d=extra-base;n=len(y);A=vstack([hstack([-csr_matrix(d[:,None]),-eye(n)]),hstack([csr_matrix(d[:,None]),-eye(n)])],format='csr');res=linprog(np.r_[0.,np.ones(n)/n],A_ub=A,b_ub=np.r_[base-lo,hi-base],bounds=[(0,1)]+[(0,None)]*n,method='highs');assert res.success;pred=base+weights[j]*d;loss=abs(pred-np.clip(pred,lo,hi)).mean();lp_errors.append(abs(loss-res.fun));assert abs(loss-res.fun)<1e-8
  value=score(y,pred,lo,hi)['ST_RAE'];assert abs(value-wr['training_fit'][t]['blend_training_OOF_ST_RAE'])<1e-12;assert int(observed.sum())==spec['label_masks'][t]['observed']
 qN=pd.read_csv(spec['native_query']['path']).set_index('Molecule_Name').loc[qu,T].to_numpy();qH=pd.read_csv(spec['h6_query']['path']).set_index('Molecule_Name').loc[qu,T].to_numpy();new=pd.read_csv(out/f'{name}-raw-refit_original_OOF.csv').set_index('Molecule_Name').loc[qu];assert np.allclose(new[T],(1-weights)*qN+weights*qH,rtol=0,atol=1e-12)
 for lane in ['raw','fixed_original_served_diagnostic']:
  for arm in ['incumbent','fixed_P5','refit_original_OOF']:
   path=out/f'{name}-{lane}-{arm}.csv';df=pd.read_csv(path).set_index('Molecule_Name');assert df.index.tolist()==qu and df.SMILES.tolist()==truth.loc[qu,'SMILES'].tolist();vals=[]
   if arm in ['incumbent','fixed_P5']:
    key=('native_query' if lane=='raw' else 'native_served') if arm=='incumbent' else ('fixed_P5_raw' if lane=='raw' else 'fixed_P5_fixed_original_served');assert path.read_bytes()==Path(spec[key]['path']).read_bytes();native_hashes.append({'cohort':name,'lane':lane,'arm':arm,'byte_identical':True})
   for j,t in enumerate(T):
    q=truth.loc[qu,t].notna();y=truth.loc[qu,t][q].to_numpy();z=df.loc[q,t].to_numpy();lo=truth.loc[qu,t+'_conf_low'][q].to_numpy();hi=truth.loc[qu,t+'_conf_high'][q].to_numpy();v=score(y,z,lo,hi);vals.append(v);rr=per[(per.cohort==name)&(per.lane==lane)&(per.arm==arm)&(per.target==t)].iloc[0]
    for metric,value in v.items():maxerr=max(maxerr,abs(value-rr[metric]));assert abs(value-rr[metric])<1e-11
   rr=metrics[(metrics.cohort==name)&(metrics.lane==lane)&(metrics.arm==arm)].iloc[0]
   for metric in vals[0]:value=np.mean([v[metric] for v in vals]);maxerr=max(maxerr,abs(value-rr[metric]));assert abs(value-rr[metric])<1e-11
inc=p.parent/'model-audit/frozen-predictions/incumbent_placed.csv';assert hashlib.sha256(inc.read_bytes()).hexdigest()=='349165ecf50906e43a27f12dee97891a92cda59e798db614ef27a7c920c38a37';con=sqlite3.connect('file:/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/orx.db?mode=ro',uri=True);status,source=con.execute('select status,commit_sha from runs where id=?',('f77263cb-82ef-47ff-8ecd-0767aaf881dd',)).fetchone();assert status=='done';result={'status':'pass','run':'f77263cb-82ef-47ff-8ecd-0767aaf881dd','source':source,'independent_LP_objective_max_difference':max(lp_errors),'independent_all5_metric_max_difference':maxerr,'all_coefficient_bounds':True,'matching_training_label_masks':True,'query_prediction_reconstruction':True,'controls':native_hashes,'incumbent_349165_untouched':True,'no_base_fit_or_calibration':True,'verification_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(p/'VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='controls'}))
