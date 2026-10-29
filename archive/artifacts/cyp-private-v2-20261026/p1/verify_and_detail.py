from pathlib import Path
import os,json,hashlib,ast
import numpy as np,pandas as pd
from scipy.stats import spearmanr,kendalltau
from rdkit import Chem,RDLogger
from rdkit.Chem.Scaffolds import MurckoScaffold
os.umask(0o077);RDLogger.DisableLog('rdApp.*');R=Path(__file__).resolve().parent;O=R/'results';V=R/'verification';V.mkdir(exist_ok=True);T=[f'{x}_pIC50_direct_inhibition' for x in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']];K=['ST_RAE','MAE','R2','Spearman','Kendall'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();cfg=json.loads((R/'worktree/private_p1_config.json').read_text());done=json.loads((O/'complete.json').read_text())
for n,h in done['files_sha256'].items():assert sha(O/n)==h
for k,v in cfg['files'].items():assert sha(v['path'])==v['sha256']
truth=pd.read_csv(cfg['files']['official_train']['path']).set_index('Molecule_Name');blind=pd.read_csv(cfg['files']['official_blind']['path']);coh=json.loads(Path(cfg['files']['cohorts']['path']).read_text())['cohorts'];metrics=pd.read_csv(O/'all-metrics.csv');per=pd.read_csv(O/'per-cyp-metrics.csv');bootstrap=pd.read_csv(O/'paired-bootstrap.csv')
def score(t,p):
 values=[]
 for j,c in enumerate(T):
  mask=t[c].notna();y=t.loc[mask,c].to_numpy();z=p[mask,j];l=t.loc[mask,c+'_conf_low'].to_numpy();h=t.loc[mask,c+'_conf_high'].to_numpy();den=np.where(y.mean()<l,l-y.mean(),np.where(y.mean()>h,y.mean()-h,0)).sum();e=np.where(z<l,l-z,np.where(z>h,z-h,0));values.append([e.sum()/den,np.abs(z-y).mean(),1-np.sum((z-y)**2)/np.sum((y-y.mean())**2),spearmanr(y,z).statistic,kendalltau(y,z).statistic])
 return np.asarray(values)
def read(path,ids,smiles):
 f=pd.read_csv(path);assert f.Molecule_Name.tolist()==list(ids) and f.SMILES.tolist()==list(smiles);return f[T].to_numpy()
maxerr=0;controls=0;count=0;detail=[];population=[]
for context in ['own750','briford529','blind750']:
 ids=blind.Molecule_Name if context=='blind750' else coh[context]['test_ids'];frame=blind if context=='blind750' else truth.loc[ids].reset_index();isblind=context=='blind750'
 for lane in ['served','raw']:
  base=read(cfg['files'][context+'_'+lane+'_original']['path'],ids,frame.SMILES);vectors={}
  for model in ['original','corrected','H6']:
   candidate=read(cfg['files'][context+'_'+lane+'_'+model]['path'],ids,frame.SMILES)
   for op in ['identity','moment','quantile']:
    z=read(O/f'{context}__{lane}__{model}__{op}.csv',ids,frame.SMILES);count+=1
    if op=='identity' or model=='original':expected=candidate
    elif op=='moment':expected=candidate*(base.std(0,ddof=1)/candidate.std(0,ddof=1))+(base.mean(0)-candidate.mean(0)*base.std(0,ddof=1)/candidate.std(0,ddof=1))
    else:
     cols=[]
     for j in range(4):
      unique,inv,n=np.unique(candidate[:,j],return_inverse=True,return_counts=True);mid=np.cumsum(n)-(n+1)/2;cols.append(np.interp(mid[inv],np.arange(len(base)),np.sort(base[:,j])))
     expected=np.column_stack(cols)
    assert np.allclose(z,expected,atol=1e-12,rtol=0)
    if model=='original':assert np.array_equal(z,base);assert sha(O/f'{context}__{lane}__{model}__{op}.csv')==cfg['files'][context+'_'+lane+'_original']['sha256'];controls+=1
    vectors[model+'__'+op]=z
    if not isblind:
     s=score(frame,z);reported=metrics[(metrics.cohort==context)&(metrics.lane==lane)&(metrics.model==model)&(metrics.operator==op)].iloc[0];maxerr=max(maxerr,float(np.max(np.abs(s.mean(0)-reported[K].to_numpy(float)))))
     for j,c in enumerate(T):
      r=per[(per.cohort==context)&(per.lane==lane)&(per.model==model)&(per.operator==op)&(per.target==c)].iloc[0];assert np.allclose(s[j],r[K].to_numpy(float),atol=1e-12,rtol=0)
  if isblind:continue
  groups=[]
  for smi in frame.SMILES:
   mol=Chem.MolFromSmiles(smi);groups.append(Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(mol),isomericSmiles=False) or 'acyclic:'+Chem.MolToInchiKey(mol).split('-')[0])
  groups=np.asarray(groups);members=[np.flatnonzero(groups==g) for g in np.unique(groups)];rng=np.random.default_rng(cfg['bootstrap_seed']);keys=['original__identity','H6__identity','H6__moment','H6__quantile'];draws={k:[] for k in keys}
  for _ in range(1000):
   ix=np.concatenate([members[k] for k in rng.integers(0,len(members),len(members))]);t=frame.iloc[ix]
   for k in keys:draws[k].append(score(t,vectors[k][ix]))
  for op,ref in [('identity','original__identity'),('moment','original__identity'),('quantile','original__identity'),('moment','H6__identity'),('quantile','H6__identity')]:
   key='H6__'+op;d=np.asarray(draws[key])-np.asarray(draws[ref]);point=score(frame,vectors[key])-score(frame,vectors[ref]);assert np.isfinite(d).all()
   for j,c in enumerate(T):
    for k,metric in enumerate(K):detail.append({'cohort':context,'lane':lane,'model':'H6','operator':op,'reference':ref,'target':c,'metric':metric,'delta':point[j,k],'lower95':np.quantile(d[:,j,k],.025),'upper95':np.quantile(d[:,j,k],.975),'valid_samples':1000,'diagnostic_only':True})
   macro=d.mean(1)
   for k,metric in enumerate(K):
    r=bootstrap[(bootstrap.cohort==context)&(bootstrap.lane==lane)&(bootstrap.model=='H6')&(bootstrap.operator==op)&(bootstrap.reference==ref)&(bootstrap.metric==metric)].iloc[0];assert abs(np.quantile(macro[:,k],.025)-r.lower95)<1e-12 and abs(np.quantile(macro[:,k],.975)-r.upper95)<1e-12
assert maxerr<1e-12
pd.DataFrame(detail).to_csv(V/'H6-paired-per-cyp-bootstrap.csv',index=False)
constants={}
for n in ast.parse((R/'worktree/vendor/briford_native/cyp_recalibrate.py').read_text()).body:
 if isinstance(n,ast.Assign):
  for t in n.targets:
   if isinstance(t,ast.Name) and t.id in ['BLIND_MOMENTS','STRAE_MOMENTS','OOF_TO_BLIND','FLOOR']:constants[t.id]=ast.literal_eval(n.value)
(R/'calibration-constants-and-scope.json').write_text(json.dumps({'constants':constants,'source_sha256':sha(R/'worktree/vendor/briford_native/cyp_recalibrate.py'),'source_scope':'Published briford live-half inferred moments and empirical2D6ST target; not local-cohort moments. One-model OOF-to-blind ratios are not universal.','scored_subset_warning':'Placement moments use all query predictions; local labels are sparse per target. Compare scored-subset predictions, not destination means directly to observed-label means.'},indent=2)+'\n')
(V/'certificate.json').write_text(json.dumps({'status':'verified','vectors':count,'exact_B_to_B_controls':controls,'max_macro_error':maxerr,'per_cyp_paired_CI_rows':len(detail),'H6_macro_CIs_independently_reproduced':True,'new_model_fits':0,'blind_scored':False,'publication':False},indent=2)+'\n');print(json.dumps({'vectors':count,'controls':controls,'max_macro_error':maxerr,'per_cyp_CIs':len(detail)}))
