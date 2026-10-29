"""Fixed private cached-OOF diagnosis. No fitting or inference."""
import argparse,hashlib,json,importlib.metadata,time,warnings
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr,kendalltau
from rdkit import Chem,DataStructs
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.MolStandardize import rdMolStandardize
import matplotlib.pyplot as plt
from orx_figstyle import use_style,save,PALETTE
EP=['CYP1A2','CYP2C9','CYP2D6','CYP3A4']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def metric(y,p,lo,hi):
 n=len(y)
 if not n:return {'n':0}
 e=p-y;d=np.maximum(lo-p,0)+np.maximum(p-hi,0);sy=float(np.std(y));sp=float(np.std(p));bias=float(e.mean());mse=float(np.mean(e**2));cov=float(np.mean((y-y.mean())*(p-p.mean())));r=cov/(sy*sp) if sy*sp else float('nan')
 den=float(np.mean(np.maximum(lo-y.mean(),0)+np.maximum(y.mean()-hi,0)))
 # Algebraic covariance form is defined even for a constant vector; equal to Pearson form when both SDs are positive.
 terms=[bias*bias,(sp-sy)**2,2*(sp*sy-cov)]
 assert np.isclose(sum(terms),mse,rtol=1e-11,atol=1e-12),(terms,mse)
 with warnings.catch_warnings():
  warnings.simplefilter('ignore');sr=float(spearmanr(y,p).statistic) if n>1 else np.nan;kt=float(kendalltau(y,p).statistic) if n>1 else np.nan
 return dict(n=n,ST_RAE=float(d.mean()/den) if den>0 else np.nan,MAE=float(abs(e).mean()),R2=float(1-mse/sy**2) if sy else np.nan,Spearman=sr,Kendall=kt,Pearson=r,RMSE=mse**.5,MSE=mse,bias=bias,truth_mean=float(y.mean()),prediction_mean=float(p.mean()),truth_sd=sy,prediction_sd=sp,sd_ratio=sp/sy if sy else np.nan,within_2fold=float((abs(e)<=np.log10(2)).mean()),within_10fold=float((abs(e)<=1).mean()),interval_coverage=float((d==0).mean()),interval_miss=float(d.mean()),below_interval=float((p<lo).mean()),above_interval=float((p>hi).mean()),mse_bias2=terms[0],mse_sd_gap2=terms[1],mse_covariance_loss=terms[2],mse_reconstruction_error=sum(terms)-mse)
def dump(obj,p):
 def clean(x):
  if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
  if isinstance(x,list):return [clean(v) for v in x]
  if isinstance(x,(np.floating,float)) and not np.isfinite(x):return None
  if isinstance(x,np.generic):return x.item()
  return x
 Path(p).write_text(json.dumps(clean(obj),indent=2,allow_nan=False)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args();cfg=json.loads(Path(args.config).read_text());out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=False);t=time.monotonic()
 paths={}
 for key,r in cfg['files'].items():
  assert sha(r['path'])==r['sha256'],key;paths[key]=Path(r['path'])
 df=pd.read_csv(paths['table'],float_precision='round_trip');f=json.loads(paths['folds'].read_text());assert sha(paths['table'])==f['data_sha256'];targets=f['targets'][:4]
 official=pd.read_csv(paths['official'],float_precision='round_trip');official.columns=official.columns.str.lower();assert len(official)==4905 and official.molecule_name.is_unique
 oi=df.set_index('molecule_name').loc[official.molecule_name];assert oi.smiles.tolist()==official.smiles.tolist();indices=df.reset_index().set_index('molecule_name').loc[official.molecule_name,'index'].to_numpy(int)
 y=oi[targets].to_numpy(float);lo=oi[[f'low_{j}' for j in range(4)]].to_numpy(float);hi=oi[[f'high_{j}' for j in range(4)]].to_numpy(float);assert np.allclose(y,official[targets],equal_nan=True,atol=1e-12,rtol=0)
 mask=np.isfinite(y);assert np.isfinite(lo[mask]).all() and np.isfinite(hi[mask]).all() and (lo[mask]<=hi[mask]).all();assert set(df.loc[df[targets].notna().any(axis=1),'molecule_name'])==set(official.molecule_name)
 full_fold=np.full(len(df),-1);seen=[]
 for k,fold in enumerate(f['folds']):
  assert not(set(fold['train'])&set(fold['stop']) or set(fold['train'])&set(fold['test']) or set(fold['stop'])&set(fold['test']));full_fold[fold['test']]=k;seen+=fold['test']
 assert sorted(seen)==list(range(len(df)));fold_of=full_fold[indices];pred={};inits={}
 for cell in ['zero','fusion']:
  whole=np.full((len(df),4),np.nan);inits[cell]=[]
  for k,fold in enumerate(f['folds']):
   d=json.loads(paths[f'{cell}_{k}_complete.json'].read_text());ip=paths[f'{cell}_{k}_initial.json'];p=paths[f'{cell}_{k}_test_raw.csv'];assert d['status']=='complete' and d['test_not_selection'] and d['prediction_sha256']==sha(p) and d['initial_sha256']==sha(ip)
   a=pd.read_csv(p,float_precision='round_trip');assert a.molecule_name.tolist()==df.molecule_name.iloc[fold['test']].tolist();whole[fold['test']]=a[targets];inits[cell].append(json.loads(ip.read_text()))
  assert np.isfinite(whole).all();pred[cell]=whole[indices]
 for k in range(5):
  assert inits['zero'][k]['parameter_sha256']==inits['fusion'][k]['parameter_sha256'];assert inits['zero'][k]['initial_batchnorm_buffers']==inits['fusion'][k]['initial_batchnorm_buffers']
 sim=np.load(paths['geometry'])['train_train'];assert sim.shape==(4905,4905)
 # Fresh deterministic chemistry spot-check guards matrix ordering and representation.
 gen=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048,includeChirality=False);spots=np.unique(np.linspace(0,4904,24,dtype=int));fps=[]
 for i in spots:
  m=Chem.MolFromSmiles(official.smiles.iloc[i]);assert m;fps.append(gen.GetFingerprint(rdMolStandardize.FragmentParent(rdMolStandardize.Cleanup(m))))
 for ii,i in enumerate(spots):
  for jj,j in enumerate(spots):assert np.isclose(sim[i,j],DataStructs.TanimotoSimilarity(fps[ii],fps[jj]),atol=1e-7)
 single=set(pd.read_csv(paths['single'],usecols=['Molecule_Name']).Molecule_Name);has_single=official.molecule_name.isin(single).to_numpy();label_count=mask.sum(1);patterns=np.array([''.join(map(str,r.astype(int))) for r in mask]);support=np.full_like(y,np.nan);neighbor=np.full(y.shape,-1,int)
 for k,fold in enumerate(f['folds']):
  train=np.isin(indices,fold['train']);query=fold_of==k
  for j in range(4):
   tr=np.where(train&mask[:,j])[0];qu=np.where(query&mask[:,j])[0];assert len(tr);m=sim[np.ix_(qu,tr)];best=m.argmax(1);support[qu,j]=m[np.arange(len(qu)),best];neighbor[qu,j]=tr[best]
 pairs=[]
 for k in range(5):
  for j,ep in enumerate(EP):
   ix=np.where((fold_of==k)&mask[:,j])[0];ii,jj=np.where(np.triu(sim[np.ix_(ix,ix)]>=.7,k=1))
   for ai,bi in zip(ix[ii],ix[jj]):
    dy=y[bi,j]-y[ai,j];gap=max(lo[bi,j]-hi[ai,j],lo[ai,j]-hi[bi,j],0);order=int(lo[bi,j]>hi[ai,j])-int(lo[ai,j]>hi[bi,j]);r=dict(endpoint=ep,fold=k,id_a=official.molecule_name.iloc[ai],id_b=official.molecule_name.iloc[bi],smiles_a=official.smiles.iloc[ai],smiles_b=official.smiles.iloc[bi],similarity=float(sim[ai,bi]),truth_a=y[ai,j],truth_b=y[bi,j],low_a=lo[ai,j],high_a=hi[ai,j],low_b=lo[bi,j],high_b=hi[bi,j],truth_delta_b_minus_a=dy,ci_gap=gap,ci_order=order,point_10fold=bool(abs(dy)>=1),ci_supported_10fold=bool(gap>=1))
    for c in pred:r[f'{c}_a']=pred[c][ai,j];r[f'{c}_b']=pred[c][bi,j];r[f'{c}_delta_b_minus_a']=pred[c][bi,j]-pred[c][ai,j]
    pairs.append(r)
 pair=pd.DataFrame(pairs);pair.to_csv(out/'close-pairs.csv',index=False,float_format='%.17g');print(json.dumps({'close_pair_csv':str(out/'close-pairs.csv'),'pairs':len(pair)}),flush=True)
 # Continuous row diagnostics, retaining exact chemical identity and contrary cases.
 rows=[]
 for j,ep in enumerate(EP):
  for i in np.where(mask[:,j])[0]:
   r=dict(endpoint=ep,fold=int(fold_of[i]),molecule_name=official.molecule_name.iloc[i],smiles=official.smiles.iloc[i],truth=y[i,j],low=lo[i,j],high=hi[i,j],has_released_single=bool(has_single[i]),primary_label_count=int(label_count[i]),label_pattern=patterns[i],nearest_labeled_train_similarity=support[i,j],nearest_labeled_train_id=official.molecule_name.iloc[neighbor[i,j]])
   for c in pred:r[c]=pred[c][i,j];r[c+'_error']=pred[c][i,j]-y[i,j];r[c+'_abs_error']=abs(r[c+'_error']);r[c+'_interval_miss']=max(lo[i,j]-pred[c][i,j],pred[c][i,j]-hi[i,j],0)
   r['delta_abs_error']=r['fusion_abs_error']-r['zero_abs_error'];r['delta_interval_miss']=r['fusion_interval_miss']-r['zero_interval_miss'];rows.append(r)
 rr=pd.DataFrame(rows);rr.to_csv(out/'measured-row-diagnostics.csv',index=False,float_format='%.17g');metrics=[]
 for j,ep in enumerate(EP):
  valid=mask[:,j];strata={'pooled':np.ones(len(y),bool)}
  strata.update({f'fold={k}':fold_of==k for k in range(5)});strata.update({f'released_single={b}':has_single==b for b in [False,True]});strata.update({f'primary_labels={n}':label_count==n for n in range(1,5)});strata.update({f'label_pattern={s}':patterns==s for s in sorted(set(patterns))})
  for left,right in [(0,.4),(.4,.6),(.6,.7),(.7,.8),(.8,1.000001)]:strata[f'labeled_support=[{left},{min(right,1)}'+(']' if right>1 else ')')]=(support[:,j]>=left)&(support[:,j]<right)
  for label,m in strata.items():
   use=valid&m
   for c in pred:metrics.append(dict(endpoint=ep,scope=label,cell=c,**metric(y[use,j],pred[c][use,j],lo[use,j],hi[use,j])))
 met=pd.DataFrame(metrics);met.to_csv(out/'metrics-by-stratum.csv',index=False,float_format='%.17g')
 # Official metric parity against separately audited completed P7 readout.
 prior=pd.read_csv(paths['prior_metrics']);mapping={'ST-RAE':'ST_RAE','MAE':'MAE','R2':'R2','Spearman':'Spearman','Kendall':'Kendall','Pearson':'Pearson'}
 for r in prior.itertuples():
  if r.endpoint=='macro':continue
  value=met[(met.endpoint==r.endpoint)&(met.scope=='pooled')&(met.cell==r.cell)].iloc[0][mapping[r.metric]];assert abs(value-r.value)<1e-12
 pair_s=[]
 for ep,g in pair.groupby('endpoint'):
  for label,q in [('all_close',g),('interval_ordered',g[g.ci_order!=0]),('point_10fold',g[g.point_10fold]),('ci_supported_10fold',g[g.ci_supported_10fold])]:
   for c in pred:
    a=q.truth_delta_b_minus_a.to_numpy();b=q[c+'_delta_b_minus_a'].to_numpy();nonzero=a!=0
    pair_s.append(dict(endpoint=ep,stratum=label,cell=c,pairs=len(q),unique_molecules=len(set(q.id_a)|set(q.id_b)),mean_abs_delta_error=float(np.mean(abs(a-b))) if len(q) else np.nan,sign_concordance=float(np.mean(np.sign(a[nonzero])==np.sign(b[nonzero]))) if nonzero.any() else np.nan,prediction_ties=int((b==0).sum()),truth_ties=int((a==0).sum()),delta_spearman=float(spearmanr(a,b).statistic) if len(q)>1 else np.nan))
 pd.DataFrame(pair_s).to_csv(out/'close-pair-metrics.csv',index=False)
 examples=[]
 for ep,g in rr.groupby('endpoint'):
  for direction,q in [('improved',g.nsmallest(8,'delta_abs_error')),('worsened',g.nlargest(8,'delta_abs_error'))]:
   q=q.copy();q['selection']=direction;examples.append(q)
 pd.concat(examples).to_csv(out/'paired-error-examples.csv',index=False,float_format='%.17g')
 use_style();fig,axs=plt.subplots(2,4,figsize=(9,5.0),sharex='row',sharey='row')
 for j,ep in enumerate(EP):
  g=rr[rr.endpoint==ep];ax=axs[0,j];ax.scatter(g.truth,g.zero,s=4,alpha=.28,color=PALETTE['blue'],label='Zero features',rasterized=True);ax.scatter(g.truth,g.fusion,s=4,alpha=.28,color=PALETTE['orange'],label='ADMET fusion',rasterized=True);lims=[min(g.truth.min(),g.zero.min(),g.fusion.min()),max(g.truth.max(),g.zero.max(),g.fusion.max())];ax.plot(lims,lims,color='.55',lw=.7);ax.set_title(ep);ax.set_xlabel('Measured pIC50');ax=axs[1,j];ax.scatter(g.zero_abs_error,g.fusion_abs_error,s=5,alpha=.35,color=PALETTE['blue'],rasterized=True);v=max(g.zero_abs_error.max(),g.fusion_abs_error.max());ax.plot([0,v],[0,v],color='.55',lw=.7);ax.set_xlabel('Zero absolute error')
 axs[0,0].set_ylabel('OOF prediction');axs[1,0].set_ylabel('Fusion absolute error');axs[0,0].legend(fontsize=6);fig.tight_layout();save(fig,out/'paired-predictions-errors');plt.close(fig)
 fig,axs=plt.subplots(1,4,figsize=(9,2.6),sharey=True)
 for j,ep in enumerate(EP):
  g=rr[rr.endpoint==ep];axs[j].scatter(g.nearest_labeled_train_similarity,g.delta_abs_error,s=5,alpha=.35,color=PALETTE['blue'],rasterized=True);axs[j].axhline(0,color='.55',lw=.7);axs[j].set_title(ep);axs[j].set_xlabel('Nearest labeled train Tanimoto')
 axs[0].set_ylabel('Fusion − zero absolute error');fig.tight_layout();save(fig,out/'support-error-change');plt.close(fig)
 (out/'FIGURE_CAPTIONS.md').write_text('Paired predictions/errors: raw out-of-fold predictions from one fixed matched5fold experiment, against measured pIC50. Top: both cells; bottom: points above diagonal worsen with fusion. No calibration or new fits. Support/error: actual training-fold same-CYP labeled neighbors only; stopping rows excluded. Points are dependent chemical observations; examples are post-fit diagnostic extremes, not selection evidence.\n')
 pooled=met[met.scope=='pooled'];dump({'status':'verified','official_molecules':len(official),'measured_cells':int(mask.sum()),'close_pairs':len(pair),'population_mse_identity_max_error':float(met.mse_reconstruction_error.abs().max()),'all5_metric_parity':True,'exact_ID_SMILES_and_initial_state_checks':True,'fingerprint_spot_checks':len(spots)**2,'no_fits':True,'no_inference':True,'no_calibration':True,'source_sha256':sha(__file__),'config_sha256':sha(args.config),'packages':{x:importlib.metadata.version(x) for x in ['numpy','pandas','scipy','rdkit','matplotlib']},'runtime_seconds':time.monotonic()-t,'pooled_metrics':pooled.to_dict('records')},out/'COMPLETE.json');print(json.dumps({'status':'verified','measured_cells':int(mask.sum()),'close_pairs':len(pair),'macro_ST':pooled.groupby('cell').ST_RAE.mean().to_dict(),'output':str(out)}),flush=True)
if __name__=='__main__':main()
