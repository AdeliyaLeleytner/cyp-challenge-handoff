from pathlib import Path
import json,hashlib,ast
import numpy as np,pandas as pd
from scipy.stats import spearmanr,kendalltau
from rdkit import Chem,RDLogger
from rdkit.Chem.Scaffolds import MurckoScaffold
RDLogger.DisableLog('rdApp.*');R=Path(__file__).resolve().parent;O=R/'results';V=R/'verification';V.mkdir(exist_ok=True);T=[f'{c}_pIC50_direct_inhibition' for c in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']];K=['ST_RAE','MAE','R2','Spearman','Kendall'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
# Independent formula used in the P1 post-run verifier, not the experiment's scorer.
a=ast.parse((R.parent/'p1/verify_and_detail.py').read_text());node=next(x for x in a.body if isinstance(x,ast.FunctionDef) and x.name=='score');exec(compile(ast.Module(body=[node],type_ignores=[]),'independent_score','exec'),globals())
cfg=json.loads((R/'worktree/private_p5_config.json').read_text());done=json.loads((O/'complete.json').read_text())
for k,h in done['files_sha256'].items():assert sha(O/k)==h
for k,r in cfg['files'].items():assert sha(r['path'])==r['sha256']
truth=pd.read_csv(cfg['files']['official_train']['path']).set_index('Molecule_Name');blind=pd.read_csv(cfg['files']['official_blind']['path']);coh=json.loads(Path(cfg['files']['cohorts']['path']).read_text())['cohorts'];weights=json.loads(Path(cfg['files']['outer_weights']['path']).read_text());fullw=json.loads(Path(cfg['files']['blind_weights']['path']).read_text())['chosen']['weight'];metrics=pd.read_csv(O/'all-metrics.csv');per=pd.read_csv(O/'per-cyp-metrics.csv');paired=pd.read_csv(O/'paired-contrasts.csv')
def read(path,ids,smiles):
 f=pd.read_csv(path);assert f.Molecule_Name.tolist()==list(ids) and f.SMILES.tolist()==list(smiles);return f[T].to_numpy()
maxerr=0;nvec=0;nci=0
for context in ['own750','briford529','blind750']:
 isblind=context=='blind750';ids=blind.Molecule_Name.tolist() if isblind else coh[context]['test_ids'];frame=blind if isblind else truth.loc[ids].reset_index();b=read(cfg['files'][context+'_original_raw']['path'],ids,frame.SMILES);c=read(cfg['files'][context+'_corrected_raw']['path'],ids,frame.SMILES)
 f=np.column_stack([np.load(cfg['files']['blind_head_'+t]['path'],allow_pickle=False) for t in T]) if isblind else read(cfg['files'][context+'_pure_head']['path'],ids,frame.SMILES);w=np.array(fullw if isblind else weights[context]['lightgbm__adme720']['blends']['per_target']['weight']);cal=json.loads(Path(cfg['files'][context+'_original_calibration']['path']).read_text())['calibration'];sc=np.array([cal[t.split('_')[0]]['scale'] for t in T]);off=np.array([cal[t.split('_')[0]]['offset'] for t in T]);intercept=(1-sc)*b.mean(0)+off
 raw={'original_absent':b,'corrected_absent':c,'original_present':b+w*(f-b),'corrected_present':c+w*(f-c)}
 assert np.allclose(raw['corrected_present'],read(cfg['files'][context+'_H6_raw']['path'],ids,frame.SMILES),atol=1e-12,rtol=0)
 if not isblind:
  groups=[]
  for smi in frame.SMILES:
   mol=Chem.MolFromSmiles(smi);groups.append(Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(mol),isomericSmiles=False) or 'acyclic:'+Chem.MolToInchiKey(mol).split('-')[0])
  groups=np.array(groups);members=[np.flatnonzero(groups==g) for g in np.unique(groups)];rng=np.random.default_rng(cfg['bootstrap_seed']);draws_indices=[np.concatenate([members[k] for k in rng.integers(0,len(members),len(members))]) for _ in range(1000)]
 for lane in ['fixed_original_served','raw']:
  vectors={}
  for arm,x in raw.items():
   expected=np.maximum(x*sc+intercept,1) if lane=='fixed_original_served' else x;p=read(O/f'{context}__{lane}__{arm}.csv',ids,frame.SMILES);assert np.allclose(p,expected,atol=1e-12,rtol=0);vectors[arm]=p;nvec+=1
   if arm=='original_absent':assert sha(O/f'{context}__{lane}__{arm}.csv')==cfg['files'][context+'_original_'+('served' if lane=='fixed_original_served' else 'raw')]['sha256']
   if not isblind:
    s=score(frame,p);r=metrics[(metrics.cohort==context)&(metrics.lane==lane)&(metrics.arm==arm)].iloc[0];maxerr=max(maxerr,float(np.max(np.abs(s.mean(0)-r[K].to_numpy(float)))))
    for j,t in enumerate(T):
     r=per[(per.cohort==context)&(per.lane==lane)&(per.arm==arm)&(per.target==t)].iloc[0];assert np.allclose(s[j],r[K].to_numpy(float),atol=1e-12,rtol=0)
  if isblind:continue
  draws={k:[] for k in vectors}
  for ix in draws_indices:
   for k,p in vectors.items():draws[k].append(score(frame.iloc[ix],p[ix]))
  draws={k:np.asarray(v) for k,v in draws.items()};contrasts={'feature_on_original':{'original_present':1,'original_absent':-1},'feature_on_corrected':{'corrected_present':1,'corrected_absent':-1},'base_without_feature':{'corrected_absent':1,'original_absent':-1},'base_with_feature':{'corrected_present':1,'original_present':-1},'base_by_feature_interaction':{'corrected_present':1,'corrected_absent':-1,'original_present':-1,'original_absent':1}}
  for name,coef in contrasts.items():
   d=sum(v*draws[k] for k,v in coef.items());assert np.isfinite(d).all()
   for target,a in [('macro',d.mean(1))]+[(t,d[:,j,:]) for j,t in enumerate(T)]:
    for j,k in enumerate(K):
     row=paired[(paired.cohort==context)&(paired.lane==lane)&(paired.contrast==name)&(paired.target==target)&(paired.metric==k)].iloc[0];assert abs(np.quantile(a[:,j],.025)-row.lower95)<1e-12 and abs(np.quantile(a[:,j],.975)-row.upper95)<1e-12;nci+=1
assert maxerr<1e-12
v={'status':'verified','vectors_independently_reconstructed':nvec,'all_point_metrics_reproduced':True,'max_macro_error':maxerr,'paired_CI_rows_reproduced':nci,'baseline_CSVs_byte_identical':True,'corrected_plus_pure_head_reproduces_H6_raw':True,'coefficients_not_refit':True,'hidden_labels_not_loaded':True,'no_new_fits_or_public_actions':True};(V/'certificate.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v,indent=2))
