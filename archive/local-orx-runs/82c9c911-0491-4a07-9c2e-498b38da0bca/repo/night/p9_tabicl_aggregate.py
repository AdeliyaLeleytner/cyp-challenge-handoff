"""Locked post-readout aggregation; no fits, no selection or calibration."""
import json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr,kendalltau
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
MET=['ST-RAE','MAE','R2','Spearman','Kendall','RMSE'];EP=['CYP1A2','CYP2C9','CYP2D6','CYP3A4']
def score(y,p,l,h):
 out=[]
 for j in range(4):
  m=np.isfinite(y[:,j]);a=y[m,j];b=p[m,j];lo=l[m,j];hi=h[m,j];den=np.mean(np.maximum(lo-a.mean(),0)+np.maximum(a.mean()-hi,0));mse=np.mean((b-a)**2);out.append([float(np.mean(np.maximum(lo-b,0)+np.maximum(b-hi,0))/den),float(abs(b-a).mean()),float(1-mse/np.var(a)),float(spearmanr(a,b).statistic),float(kendalltau(a,b).statistic),float(np.sqrt(mse))])
 a=np.array(out);return np.vstack([a,a.mean(0)])
def aggregate(c):
 out=Path(c['output']);orig=pd.read_csv(c['files']['official']['path']);df=pd.read_csv(c['files']['table']['path']);f=json.load(open(c['files']['folds']['path']));ids=orig.Molecule_Name.tolist();idx=df.reset_index().set_index('molecule_name').loc[ids,'index'].to_numpy();Y=df.loc[idx,f['targets'][:4]].to_numpy(float);L=df.loc[idx,[f'low_{j}' for j in range(4)]].to_numpy(float);H=df.loc[idx,[f'high_{j}' for j in range(4)]].to_numpy(float);co=json.load(open(c['files']['outer_manifest']['path']))['cohorts'];groups=np.array([Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(Chem.MolFromSmiles(s))) for s in orig.SMILES],dtype=object);fold_of=np.full(len(ids),-1)
 for k,fold in enumerate(f['folds']):fold_of[np.isin(idx,fold['test'])]=k
 assert (fold_of>=0).all();collections={};pins={};points=[];deltas=[];complement=[];rng=np.random.default_rng(20261026)
 for cohort in ['OOF','own750','briford529']:
  use=np.ones(len(ids),bool) if cohort=='OOF' else orig.Molecule_Name.isin(co[cohort]['test_ids']).to_numpy();ix=np.where(use)[0];collection={}
  for rep in ['adme600','atomjepa256']:
   full=np.full((len(ids),4),np.nan)
   jobs=[str(k) for k in range(5)] if cohort=='OOF' else [cohort]
   for k in jobs:
    expected=np.where(fold_of==int(k))[0] if cohort=='OOF' else ix
    for j in range(4):
     path=out/f'{rep}-f{k}-target{j}.csv';a=pd.read_csv(path);assert a.molecule_name.tolist()==orig.Molecule_Name.iloc[expected].tolist() and a.smiles.tolist()==orig.SMILES.iloc[expected].tolist();full[expected,j]=a.prediction.to_numpy();pins[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
   assert np.isfinite(full[ix]).all();collection[rep]=full[ix];o=pd.DataFrame(full[ix],columns=EP);o.insert(0,'Molecule_Name',orig.Molecule_Name.iloc[ix].to_numpy());o.insert(1,'SMILES',orig.SMILES.iloc[ix].to_numpy());o.to_csv(out/f'{cohort}-{rep}-raw.csv',index=False,float_format='%.17g');sc=score(Y[ix],full[ix],L[ix],H[ix])
   for j,ep in enumerate(EP+['macro']):
    for k,met in enumerate(MET):points.append({'cohort':cohort,'representation':rep,'endpoint':ep,'metric':met,'value':sc[j,k]})
  strata=[]
  for fold in (range(5) if cohort=='OOF' else [None]):
   local=np.where(fold_of[ix]==fold)[0] if fold is not None else np.arange(len(ix));gg=groups[ix[local]];strata.append([local[gg==v] for v in sorted(set(gg))])
  draws=[]
  for b in range(1000):
   ii=np.concatenate([np.concatenate([s[z] for z in rng.integers(0,len(s),len(s))]) for s in strata]);draws.append(score(Y[ix[ii]],collection['atomjepa256'][ii],L[ix[ii]],H[ix[ii]])-score(Y[ix[ii]],collection['adme600'][ii],L[ix[ii]],H[ix[ii]]))
  draws=np.array(draws);point=score(Y[ix],collection['atomjepa256'],L[ix],H[ix])-score(Y[ix],collection['adme600'],L[ix],H[ix]);low,high=np.quantile(draws,[.025,.975],axis=0)
  for j,ep in enumerate(EP+['macro']):
   for k,met in enumerate(MET):deltas.append({'cohort':cohort,'endpoint':ep,'metric':met,'atom_minus_adme':point[j,k],'lower95':low[j,k],'upper95':high[j,k]})
  for j,ep in enumerate(EP):
   q=np.isfinite(Y[ix,j]);a=collection['adme600'][q,j]-Y[ix[q],j];b=collection['atomjepa256'][q,j]-Y[ix[q],j];complement.append({'cohort':cohort,'endpoint':ep,'observed':int(q.sum()),'residual_Pearson':float(np.corrcoef(a,b)[0,1]),'prediction_Pearson':float(np.corrcoef(collection['adme600'][q,j],collection['atomjepa256'][q,j])[0,1])})
  print(json.dumps({'aggregation_finished':cohort,'bootstrap':1000}),flush=True)
 pd.DataFrame(points).to_csv(out/'aggregate-metrics.csv',index=False);pd.DataFrame(deltas).to_csv(out/'paired-deltas.csv',index=False);pd.DataFrame(complement).to_csv(out/'complementarity.csv',index=False);(out/'AGGREGATE.json').write_text(json.dumps({'status':'verified','prediction_files':pins,'bootstrap':1000,'seed':20261026,'unit':'nativeBemisMurcko groups, withinfold forOOF; pairedsamegroups acrossrepresentations','limits':'OOF overlappingtraining andtwo repeatedlyuseddevelopmentholdouts; notprospectiveblindvalidation','no_calibration':True,'no_ensemble_weights_fit':True,'no_hidden_labels_loaded':True},indent=2)+'\n')
