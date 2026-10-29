"""Private post-fit audit; no fitting, no serving calibration, fixed paired bootstrap."""
import argparse,json,hashlib,importlib.util,importlib.metadata
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr,kendalltau,pearsonr
from sklearn.metrics import r2_score,mean_absolute_error
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold

EP=['CYP1A2','CYP2C9','CYP2D6','CYP3A4'];MET=['ST-RAE','MAE','R2','Spearman','Kendall','Pearson','RMSE','bias','prediction_SD','truth_SD']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def score(y,p,l,h):
 out=[]
 for j in range(4):
  m=np.isfinite(y[:,j]);a=y[m,j];b=p[m,j];lo=np.where(np.isfinite(l[m,j]),l[m,j],a);hi=np.where(np.isfinite(h[m,j]),h[m,j],a)
  den=(np.maximum(lo-a.mean(),0)+np.maximum(a.mean()-hi,0)).sum();assert den>0
  out.append([(np.maximum(lo-b,0)+np.maximum(b-hi,0)).sum()/den,mean_absolute_error(a,b),r2_score(a,b),spearmanr(a,b).statistic,kendalltau(a,b).statistic,pearsonr(a,b).statistic,float(np.sqrt(np.mean((b-a)**2))),float(np.mean(b-a)),float(np.std(b)),float(np.std(a))])
 out=np.array(out,float);assert np.isfinite(out).all();return np.vstack([out,out.mean(0)])
def main():
 pa=argparse.ArgumentParser();pa.add_argument('--results',type=Path,required=True);pa.add_argument('--stage',type=Path,required=True);pa.add_argument('--output',type=Path,required=True);pa.add_argument('--cells',nargs='+',default=['zero','original','masked','repaired']);pa.add_argument('--official',type=Path,required=True);pa.add_argument('--bootstrap',type=int,default=1000);a=pa.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 cfg=json.loads((a.stage/'fold-manifest.json').read_text());df=pd.read_csv(a.stage/'table.csv',float_precision='round_trip');assert sha(a.stage/'table.csv')==cfg['data_sha256'];targets=cfg['targets'];n=len(df);allpred={};fold_of=np.full(n,-1);perfold={};initial={}
 for k,f in enumerate(cfg['folds']):fold_of[f['test']]=k
 assert (fold_of>=0).all();Y=df[targets[:4]].to_numpy(float);lo=df[[f'low_{j}' for j in range(4)]].to_numpy(float);hi=df[[f'high_{j}' for j in range(4)]].to_numpy(float);official=np.isfinite(Y).any(1);assert official.sum()==4905
 original=pd.read_csv(a.official);expected=[h for path,h in cfg['source_files'].items() if path.endswith('/official-train.csv')];assert len(expected)==1 and sha(a.official)==expected[0]
 assert original.Molecule_Name.is_unique and set(df.loc[official,'molecule_name'])==set(original.Molecule_Name)
 original=original.set_index('Molecule_Name').loc[df.loc[official,'molecule_name']]
 assert np.allclose(Y[official],original[[e+'_pIC50_direct_inhibition' for e in EP]].to_numpy(float),rtol=0,atol=1e-12,equal_nan=True)
 observed=np.isfinite(Y);assert np.isfinite(lo[observed]).all() and np.isfinite(hi[observed]).all() and (lo[observed]<=hi[observed]).all()
 for cell in a.cells:
  full=np.full((n,4),np.nan);seen=[];perfold[cell]=[];initial[cell]=[]
  for k,f in enumerate(cfg['folds']):
   r=a.results/f'{cell}_f{k}';done=json.loads((r/'complete.json').read_text());init=json.loads((r/'initial.json').read_text());assert done['status']=='complete' and done['fold']==k and done['cell']==cell and done['test_not_selection']
   assert sha(r/'initial.json')==done['initial_sha256'] and sha(r/'test_raw.csv')==done['prediction_sha256'];pred=pd.read_csv(r/'test_raw.csv',float_precision='round_trip');assert pred.molecule_name.tolist()==df.molecule_name.iloc[f['test']].tolist();assert list(pred.columns)==['molecule_name']+targets
   assert np.isfinite(pred[targets].to_numpy()).all();full[f['test']]=pred[targets[:4]].to_numpy();seen+=f['test'];initial[cell].append(init);sc=score(Y[f['test']],full[f['test']],lo[f['test']],hi[f['test']]);assert abs(sc[-1,0]-done['raw_strae'])<1e-10
   for j,e in enumerate(EP):
    for q,met in enumerate(MET):
     if 'raw_per_target_metrics' in done:
      saved_value=done['raw_per_target_metrics'][j][met]
      # Worker prediction_SD accumulated float32; independent readout uses float64.
      tolerance=8*np.finfo(np.float32).eps*max(1,abs(saved_value)) if met=='prediction_SD' else 1e-10
      assert abs(sc[j,q]-saved_value)<tolerance,(cell,k,met,sc[j,q],saved_value)
   perfold[cell].append(sc.tolist())
  assert sorted(seen)==list(range(n));assert np.isfinite(full).all();allpred[cell]=full[official]
 for k in range(5):
  assert len({initial[c][k]['parameter_sha256'] for c in a.cells})==1
  assert all('initial_batchnorm_buffers' in initial[c][k] for c in a.cells)
  assert all(initial[c][k]['initial_batchnorm_buffers']==initial[a.cells[0]][k]['initial_batchnorm_buffers'] for c in a.cells)
 yy=Y[official];ll=lo[official];hh=hi[official];oo=df[official].copy();folds=fold_of[official];groups=[]
 for s in oo.smiles:
  mol=Chem.MolFromSmiles(s);assert mol is not None;groups.append(Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(mol)))
 oo['fold']=folds;oo['scaffold']=groups;oo[['molecule_name','request_id','fold','scaffold']].to_csv(a.output/'official-oof-identity.csv',index=False)
 for c,p in allpred.items():
  table=pd.DataFrame(p,columns=EP);table.insert(0,'molecule_name',oo.molecule_name.to_list());table.to_csv(a.output/f'{c}-official-oof.csv',index=False,float_format='%.17g')
 point={c:score(yy,p,ll,hh) for c,p in allpred.items()};draws={c:[] for c in a.cells};rng=np.random.default_rng(20261026);strata=[]
 for k in range(5):
  idx=np.where(folds==k)[0];g=np.array(groups,dtype=object)[idx];strata.append([idx[g==v] for v in sorted(set(g))])
 for b in range(a.bootstrap):
  ix=np.concatenate([np.concatenate([st[j] for j in rng.integers(0,len(st),len(st))]) for st in strata])
  for c in a.cells:draws[c].append(score(yy[ix],allpred[c][ix],ll[ix],hh[ix]))
  if (b+1)%100==0:print(json.dumps({'bootstrap_completed':b+1}),flush=True)
 rows=[]
 for c in a.cells:
  for j,e in enumerate(EP+['macro']):
   for q,met in enumerate(MET):rows.append({'cell':c,'endpoint':e,'metric':met,'value':point[c][j,q]})
 pd.DataFrame(rows).to_csv(a.output/'point-metrics.csv',index=False)
 contrasts=[('original','zero'),('masked','original'),('repaired','original'),('repaired','masked')]
 contrasts_out=[]
 for candidate,control in contrasts:
  dist=np.array(draws[candidate])-np.array(draws[control]);delta=point[candidate]-point[control]
  for j,e in enumerate(EP+['macro']):
   for q,met in enumerate(MET):
    ql,qh=np.quantile(dist[:,j,q],[.025,.975]);contrasts_out.append({'contrast':candidate+' minus '+control,'endpoint':e,'metric':met,'delta':delta[j,q],'lower95':ql,'upper95':qh})
 pd.DataFrame(contrasts_out).to_csv(a.output/'paired-deltas.csv',index=False)
 summary={'status':'verified','official_oof_rows':4905,'all_pool_test_rows':n,'all_fold_ID_order_target_and_hash_checks':True,'initial_parameter_hashes_matched_per_fold':True,'metrics':MET,'Pearson_is_extra_diagnostic':True,'RMSE_bias_SD_are_extended_diagnostics':True,'prediction_SD_parity_note':'Worker float32 SD versus independent float64 SD; numerical check uses8float32eps*max(1,value), officialmetrics retain1e-10checks','four_arms':'freshzero,original,VolDensemasked,VolDenseunitrepaired','only_two_raw_feature_columns_intervened':True,'per_fold':perfold,'point':{k:v.tolist() for k,v in point.items()},'bootstrap':{'replicates':a.bootstrap,'seed':20261026,'unit':'nativeBemisMurcko scaffoldgroup within frozenfold, including sharedempty scaffold','percentile':95,'same_draws_across_cells_and_targets':True,'limitations':'descriptive conditionalOOF uncertainty; overlappingtrainingfolds and reuseddevelopmentdata mean not independentprospectiveconfirmation'},'serving_calibration_applied':False,'analysis_packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn','rdkit']},'official_source_sha256':sha(a.official),'source_sha256':sha(__file__),'stage_manifest_sha256':sha(a.stage/'fold-manifest.json')};(a.output/'READOUT.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n');print(json.dumps({'status':'verified','macro':{k:v[-1].tolist() for k,v in point.items()}}),flush=True)
if __name__=='__main__':main()
