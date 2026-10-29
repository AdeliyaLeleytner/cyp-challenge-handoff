"""Rescore only saved outer predictions and catalog previous results; never fit models."""
from pathlib import Path
import os,json,hashlib
import pandas as pd,numpy as np
from scipy.stats import spearmanr,kendalltau
os.umask(0o077);R=Path(__file__).resolve().parent;W=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition');G=W/'artifacts/goal-20261026';T=[f'{x}_pIC50_direct_inhibition' for x in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();manifest=json.loads((G/'model-audit/official-snapshot-18460/manifest.json').read_text());truth=pd.read_csv(manifest['files']['official_train']['path']).set_index('Molecule_Name');cohorts=json.loads(Path(manifest['files']['cohorts']['path']).read_text())['cohorts'];single=set(pd.read_csv(W/'artifacts/cyp-review/sources/cyp-challenge-single-concentration-TRAIN.csv').Molecule_Name)
reports={};rows=[];strata=[]
for cohort in ['own750','briford529']:
 ids=cohorts[cohort]['test_ids'];t=truth.loc[ids];paths={'original_native':W/'artifacts/briford-native-holdouts-20261024/remote/holdouts'/cohort/'results/cyp-ensemble_activity_submission_native_raw.csv','corrected_native':G/'h6-lightgbm/results'/f'{cohort}__native__raw.csv','H6':G/'h6-lightgbm/results'/f'{cohort}__lightgbm__adme720__native_blend_per_target__raw.csv'};arrays={}
 for model,p in paths.items():
  f=pd.read_csv(p);assert f.Molecule_Name.is_unique;f=f.set_index('Molecule_Name').loc[ids];assert f.SMILES.tolist()==t.SMILES.tolist();z=f[T].to_numpy();assert np.isfinite(z).all();arrays[model]=z;reports[str(p)]={'sha256':sha(p),'rows':len(f)}
  for j,target in enumerate(T):
   mask=t[target].notna();y=t.loc[mask,target].to_numpy();pred=z[mask,j];lo=t.loc[mask,target+'_conf_low'].to_numpy();hi=t.loc[mask,target+'_conf_high'].to_numpy();soft=np.maximum(lo-pred,0)+np.maximum(pred-hi,0);den=(np.maximum(lo-y.mean(),0)+np.maximum(y.mean()-hi,0)).sum()
   rows.append({'cohort':cohort,'model':model,'target':target.split('_')[0],'n':len(y),'ST_RAE':soft.sum()/den,'MAE':np.abs(y-pred).mean(),'R2':1-np.sum((y-pred)**2)/np.sum((y-y.mean())**2),'Spearman':spearmanr(y,pred).statistic,'Kendall':kendalltau(y,pred).statistic})
 for j,target in enumerate(T):
  mask=t[target].notna().to_numpy();y=t[target].to_numpy();lo=t[target+'_conf_low'].to_numpy();hi=t[target+'_conf_high'].to_numpy();b=arrays['corrected_native'][:,j];p=arrays['H6'][:,j];err0=np.maximum(lo-b,0)+np.maximum(b-hi,0);err1=np.maximum(lo-p,0)+np.maximum(p-hi,0);yy=y[mask];den=(np.maximum(lo[mask]-yy.mean(),0)+np.maximum(yy.mean()-hi[mask],0)).sum()
  for kind,indicator in [('released_single',np.array([n in single for n in ids])),('no_released_single',np.array([n not in single for n in ids]))]:
   use=mask&indicator;n=use.sum()
   strata.append({'cohort':cohort,'target':target.split('_')[0],'coverage':kind,'n_observed':int(n),'mean_soft_error_delta_pIC50':float((err1[use]-err0[use]).mean()) if n else None,'mean_abs_error_delta_pIC50':float((np.abs(y[use]-p[use])-np.abs(y[use]-b[use])).mean()) if n else None,'contribution_to_full_cohort_macro_ST_delta':float((err1[use]-err0[use]).sum()/den/4),'denominator_scope':'whole target cohort; contributions add without changing score normalization'})
df=pd.DataFrame(rows);df.to_csv(R/'saved_outer_metrics_per_cyp.csv',index=False);macro=df.groupby(['cohort','model'])[['ST_RAE','MAE','R2','Spearman','Kendall']].mean().reset_index();macro.to_csv(R/'saved_outer_metrics_macro.csv',index=False);pd.DataFrame(strata).to_csv(R/'H6_outer_gain_by_released_assay_coverage.csv',index=False)
all_results=[]
paths={'CPU_ADMET_portfolio':G/'full-feature-evaluation/all-metrics.csv','H6_LightGBM_ADME':G/'h6-lightgbm/results/all-metrics.csv','H7_fixed_simplex':G/'h7-simplex/results/all-metrics.csv','TabPFN_ADMET120':G/'challenge-audit/tabpfn-feasibility/execution/recovered/results/all-metrics.csv','H5_TabPFN_ADME':G/'challenge-audit/tabpfn-feasibility/h5/recovered/h5-results/all-metrics.csv'}
for campaign,p in paths.items():
 x=pd.read_csv(p);x.insert(0,'campaign',campaign);x['source_file']=str(p);x['source_sha256']=sha(p);all_results.append(x)
pd.concat(all_results,ignore_index=True).to_csv(R/'all_prior_readout_metrics.csv',index=False)
old=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-briford-reproduction-20261024/remote/finalized');new=G/'model-audit/corrected-fullfit-native/recovered-output/results';conditions=[]
for member in ['union18','mtaux8','2d6isoform6','2d6single']:
 for fold in range(5):
  a=json.loads((old/member/f'fold{fold}/metadata.json').read_text());b=json.loads((new/member/f'fold{fold}/metadata.json').read_text());conditions.append({'member':member,'fold':fold,'old_train_rows':a['training_rows'],'new_train_rows':b['training_rows'],'same_validation_rows':a['validation_rows']==b['validation_rows'],'same_hyperparameters':a['model_hyperparameters']==b['model_hyperparameters'],'same_recorded_packages':a['packages']==b['packages'],'old_best_epoch':a['best_epoch'],'new_best_epoch':b['best_epoch']})
pd.DataFrame(conditions).to_csv(R/'native_refit_conditions.csv',index=False)
(R/'saved_result_verification.json').write_text(json.dumps({'saved_prediction_sources':reports,'macro_score_rows':len(macro),'no_model_fit':True,'no_hidden_labels':True,'no_network':True},indent=2)+'\n');print(macro.round(6).to_string(index=False))
