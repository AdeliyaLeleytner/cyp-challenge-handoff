from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from scipy.stats import spearmanr,kendalltau,pearsonr
from sklearn.metrics import r2_score
p=Path(__file__).parent;stage=p.parent/'p7/stage';f=json.load(open(stage/'fold-manifest.json'));df=pd.read_csv(stage/'table.csv');assert hashlib.sha256((stage/'table.csv').read_bytes()).hexdigest()==f['data_sha256'];targets=f['targets'][:4];y=df[targets].to_numpy();lo=df[[f'low_{j}' for j in range(4)]].to_numpy();hi=df[[f'high_{j}' for j in range(4)]].to_numpy();mask=np.isfinite(y);assert mask.any(1).sum()==4905 and mask.sum()==6525;reported=json.load(open(p/'readout/READOUT.json'));EP=['CYP1A2','CYP2C9','CYP2D6','CYP3A4'];MET=['ST-RAE','MAE','R2','Spearman','Kendall','Pearson','RMSE','bias','prediction_SD','truth_SD'];assert reported['metrics']==MET;rows=[];pins={};maxerr=0.;perfold_error=0.;initial={}
def metrics(a,b,l,h):
 d=abs(b-np.clip(b,l,h));den=abs(a.mean()-np.clip(a.mean(),l,h)).mean();return np.array([d.mean()/den,abs(b-a).mean(),r2_score(a,b),spearmanr(a,b).statistic,kendalltau(a,b).statistic,pearsonr(a,b).statistic,np.sqrt(np.mean((b-a)**2)),np.mean(b-a),np.std(b,ddof=0),np.std(a,ddof=0)])
for cell in ['zero','original','masked','repaired']:
 full=np.full((len(df),4),np.nan);seen=[];initial[cell]=[]
 for k,fold in enumerate(f['folds']):
  directory=p/'recovered/metric-snapshot'/f'{cell}_f{k}';path=directory/'test_raw.csv';pred=pd.read_csv(path);done=json.load(open(directory/'complete.json'));init=json.load(open(directory/'initial.json'));assert hashlib.sha256((directory/'initial.json').read_bytes()).hexdigest()==done['initial_sha256'];sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==done['prediction_sha256'];assert pred.molecule_name.tolist()==df.molecule_name.iloc[fold['test']].tolist();assert done['status']=='complete' and done['test_not_selection'];full[fold['test']]=pred[targets];seen+=fold['test'];pins[f'{cell}_f{k}']=sha;initial[cell].append(init)
  for j in range(4):
   ix=np.asarray(fold['test']);ix=ix[mask[ix,j]];value=metrics(y[ix,j],full[ix,j],lo[ix,j],hi[ix,j]);worker=done['raw_per_target_metrics'][j]
   for n,met in enumerate(MET):
    error=abs(value[n]-worker[met]);tol=8*np.finfo(np.float32).eps*max(1.,abs(value[n])) if met=='prediction_SD' else 1e-10;assert error<=tol;(None);perfold_error=max(perfold_error,error)
 assert sorted(seen)==list(range(len(df))) and np.isfinite(full).all();vals=[]
 for j,e in enumerate(EP):
  ix=np.where(mask[:,j])[0];vals.append(metrics(y[ix,j],full[ix,j],lo[ix,j],hi[ix,j]))
 vals=np.vstack([vals,np.mean(vals,axis=0)]);error=float(np.max(abs(vals-np.array(reported['point'][cell]))));maxerr=max(maxerr,error);assert error<1e-11
 for j,e in enumerate(EP+['macro']):
  for k,met in enumerate(MET):rows.append({'cell':cell,'endpoint':e,'metric':met,'independent_value':vals[j,k]})
for k in range(5):
 assert len({initial[c][k]['parameter_sha256'] for c in initial})==1;assert all(initial[c][k]['initial_batchnorm_buffers']==initial['zero'][k]['initial_batchnorm_buffers'] for c in initial)
pd.DataFrame(rows).to_csv(p/'independent-model-agent-metrics.csv',index=False);record={'status':'pass','pooled_max_absolute_difference':maxerr,'perfold_max_absolute_difference_including_SD':perfold_error,'SD_only_tolerance':'8float32eps*max(1,abs(value)); float32worker vsfloat64CSVaccumulation','all_other_worker_metrics_tolerance':1e-10,'official_rows':4905,'observed_target_cells':6525,'all20_ID_hash_membership_checks':True,'initial_parameter_and_BN_parity':True,'all5_and_extended_metrics_independently_recomputed':True,'prediction_hashes':pins,'readout_source_sha256':hashlib.sha256((p/'readout.py').read_bytes()).hexdigest(),'verification_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'no_fit_or_calibration':True};(p/'INDEPENDENT_MODEL_AGENT_CHECK.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='prediction_hashes'}));print(pd.DataFrame(rows).query('endpoint=="macro"').pivot(index='cell',columns='metric',values='independent_value').round(6).to_string())
