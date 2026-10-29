from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from scipy.stats import spearmanr,kendalltau
from sklearn.metrics import mean_absolute_error,r2_score
from rdkit import Chem,RDLogger
from rdkit.Chem.Scaffolds import MurckoScaffold
RDLogger.DisableLog('rdApp.*')
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';DEST=ROOT/'verification';DEST.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
cfg=json.loads((ROOT/'worktree/h7_config.json').read_text());done=json.loads((OUT/'complete.json').read_text())
assert done['status']=='complete' and done['base_fits']==0
for n,h in done['files_sha256'].items():assert sha(OUT/n)==h
for n,v in cfg['files'].items():assert sha(v['path'])==v['sha256']
base=json.loads(Path(cfg['files']['base_config']['path']).read_text());manifest=json.loads(Path(base['snapshot_manifest']).read_text());assert sha(base['snapshot_manifest'])==base['snapshot_manifest_sha256']
for n,v in manifest['files'].items():assert sha(v['path'])==v['sha256']
for n,v in base['embedding_assets'].items():assert sha(v['path'])==v['sha256']
targets=[f'{c}_pIC50_direct_inhibition' for c in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']];metrics=['ST_RAE','MAE','R2','Spearman','Kendall']
truth=pd.read_csv(manifest['files']['official_train']['path']).set_index('Molecule_Name');cohorts=json.loads(Path(manifest['files']['cohorts']['path']).read_text())['cohorts'];weights=json.loads((OUT/'weights.json').read_text())
def score(ids,p):
 t=truth.loc[ids];values=[]
 for j,c in enumerate(targets):
  m=t[c].notna();y=t.loc[m,c].to_numpy();z=p[m,j];lo=t.loc[m,c+'_conf_low'].to_numpy();hi=t.loc[m,c+'_conf_high'].to_numpy();d=np.where(y.mean()<lo,lo-y.mean(),np.where(y.mean()>hi,y.mean()-hi,0)).sum();e=np.where(z<lo,lo-z,np.where(z>hi,z-hi,0))
  values.append([e.sum()/d,mean_absolute_error(y,z),r2_score(y,z),spearmanr(y,z).statistic,kendalltau(y,z).statistic])
 return np.array(values)
def read(path,ids):
 f=pd.read_csv(path);assert f.Molecule_Name.is_unique and f.Molecule_Name.tolist()==list(ids);assert f.SMILES.tolist()==truth.loc[ids].SMILES.tolist();p=f[targets].to_numpy();assert np.isfinite(p).all();return p
reported=pd.read_csv(OUT/'all-metrics.csv');per=pd.read_csv(OUT/'per-cyp-metrics.csv');recomputed=[];maxerr=0
for row in reported.to_dict('records'):
 ids=cohorts[row['cohort']]['test_ids'];p=read(OUT/f"{row['cohort']}__{row['model']}__{row['lane']}.csv",ids);s=score(ids,p);mean=s.mean(0);maxerr=max(maxerr,float(np.max(np.abs(mean-[row[k] for k in metrics]))));assert maxerr<1e-12
 for j,t in enumerate(targets):
  q=per[(per.cohort==row['cohort'])&(per.model==row['model'])&(per.lane==row['lane'])&(per.target==t)].iloc[0];assert np.allclose(s[j],[q[k] for k in metrics],atol=1e-12,rtol=0)
 recomputed.append({**{k:row[k] for k in ['cohort','model','lane']},**dict(zip(metrics,mean))})
cert={};boot=[]
primary=json.loads(Path(cfg['files']['primary_inner']['path']).read_text())
for cohort in ['own750','briford529']:
 tr=cohorts[cohort]['train_ids'];te=cohorts[cohort]['test_ids'];total=np.zeros((len(tr),4));count=np.zeros_like(total)
 for member in ['union18','mtaux8','2d6isoform6','2d6single']:
  f=pd.read_csv(manifest['files'][cohort+'_'+member+'_oof']['path']).set_index('molecule_name');assert f.index.is_unique
  for j,t in enumerate(targets):
   col=t.lower()+'_pred'
   if col not in f:continue
   v=f[col].reindex(tr).to_numpy();m=np.isfinite(v);total[m,j]+=v[m];count[m,j]+=1
 native=total/count;oof=np.stack([native,read(cfg['files'][cohort+'_primary_oof']['path'],tr),read(cfg['files'][cohort+'_h6_oof']['path'],tr)],-1)
 query=np.stack([read(cfg['files'][cohort+'_native_query']['path'],te),read(cfg['files'][cohort+'_primary_query']['path'],te),read(cfg['files'][cohort+'_h6_query']['path'],te)],-1)
 w=np.array(weights[cohort]['weights']);assert w.shape==(3,) and (w>=0).all() and (w<=1).all() and abs(w.sum()-1)<1e-12 and weights[cohort]['solver_status']==0
 assert weights[cohort]['maximum_constraint_violation']<1e-9
 wp=primary[cohort]['lightgbm__admet']['blends']['global']['weight'];wvec={'native':np.array([1.,0,0]),'primary_global':np.array([1-wp,wp,0]),'h7_simplex':w}
 for model,wm in wvec.items():
  assert np.allclose(read(OUT/f'{cohort}__{model}__training_OOF.csv',tr),oof@wm,atol=1e-12,rtol=0)
  assert np.allclose(read(OUT/f'{cohort}__{model}__raw.csv',te),query@wm,atol=1e-12,rtol=0)
 st=score(tr,oof@w).mean(0)[0];assert abs(st-weights[cohort]['training_OOF_ST_RAE'])<1e-12
 assert abs(weights[cohort]['two_expert_parity']['objective_difference'])<1e-8
 cert[cohort]={'weights':w.tolist(),'independent_training_OOF_ST_RAE':st,'all_three_output_combinations_verified':True}
 arrays={m:query@wm for m,wm in wvec.items()};groups=[]
 for smi in truth.loc[te].SMILES:
  m=Chem.MolFromSmiles(smi);groups.append(Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(m),isomericSmiles=False) or 'acyclic:'+Chem.MolToInchiKey(m).split('-')[0])
 groups=np.array(groups);members=[np.flatnonzero(groups==g) for g in np.unique(groups)];rng=np.random.default_rng(20261026);deltas={r:[] for r in ['native','primary_global']}
 for _ in range(1000):
  ix=np.concatenate([members[k] for k in rng.integers(0,len(members),len(members))]);ii=np.array(te)[ix];ss={m:score(ii,p[ix]).mean(0) for m,p in arrays.items()}
  for r in deltas:deltas[r].append(ss['h7_simplex']-ss[r])
 for ref,d in deltas.items():
  arr=np.array(d);assert np.isfinite(arr).all()
  for j,k in enumerate(metrics):
   q=np.quantile(arr[:,j],[.025,.975]);boot.append({'cohort':cohort,'reference':ref,'metric':k,'lower95':q[0],'upper95':q[1],'valid':1000})
original=pd.read_csv(OUT/'paired-bootstrap.csv')
for x in boot:
 r=original[(original.cohort==x['cohort'])&(original.reference==x['reference'])&(original.metric==x['metric'])].iloc[0];assert abs(r.lower95-x['lower95'])<1e-12 and abs(r.upper95-x['upper95'])<1e-12 and r.valid_samples==1000
pd.DataFrame(recomputed).to_csv(DEST/'independent-metrics.csv',index=False);pd.DataFrame(boot).to_csv(DEST/'independent-bootstrap.csv',index=False)
result={'run_id':'91b8e4ae-48f9-48e6-91d1-08d1937b280e','source_commit':'e533fd9259bc4e6766ce6f1b8dcfe8f6b29853dc','status':'independently_verified','outer_files':12,'training_OOF_files':6,'outer_metric_cells':300,'max_macro_rescore_error':maxerr,'direct_asset_pins':len(cfg['files']),'snapshot_asset_pins':len(manifest['files']),'embedding_asset_pins':len(base['embedding_assets']),'weights_and_vector_reconstruction':cert,'paired_scaffold_intervals_checked':len(boot),'all_bootstrap_samples_valid':True,'output_sha256':{p.name:sha(p) for p in OUT.iterdir() if p.is_file()},'base_fits':0,'no_new_optimization_during_verification':True,'no_submission':True}
(DEST/'certificate.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='output_sha256'},indent=2))
