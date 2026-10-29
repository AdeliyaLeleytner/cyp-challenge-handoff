"""Score recovered fixed models; no fitting or model selection."""
from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'worktree'))
from night.strict_reference_runner import metrics
from night.evaluation import _truth_arrays,_score_arrays
cert=json.loads((ROOT/'recovery-certificate.json').read_text());assert cert['complete_run'] and cert['all_remote_hashes_match']
oldroot=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-briford-holdouts-20261024/remote/holdouts')
remote_scores=json.loads((ROOT/'recovered-output/scores.json').read_text());result={}
def scaffold(s):
 m=Chem.MolFromSmiles(s);key=MurckoScaffold.MurckoScaffoldSmiles(mol=m,includeChirality=False)
 if key:return key
 Chem.RemoveStereochemistry(m);return 'ACYCLIC:'+Chem.MolToSmiles(m,isomericSmiles=True)
for cohort in ['own750','briford529']:
 truth=pd.read_csv(ROOT/'stage/corrected'/cohort/'truth.csv');result[cohort]={}
 for variant,filename in [('raw','cyp-ensemble_activity_submission_native_raw.csv'),('native_published_placement','cyp-ensemble_activity_submission_native_raw_native_strae.csv')]:
  path=ROOT/'recovered-output'/cohort/'results'/filename;pred=pd.read_csv(path);old=pd.read_csv(oldroot/cohort/'results'/filename)
  fresh=metrics(truth,pred);reference=metrics(truth,old)
  assert set(pred.Molecule_Name)==set(truth.Molecule_Name) and not pred.Molecule_Name.duplicated().any()
  for key,value in fresh['macro_metrics'].items():assert abs(value-remote_scores[cohort][variant]['macro_metrics'][key])<1e-12
  entry={'corrected':fresh,'historical':reference,'delta_corrected_minus_historical':{k:fresh['macro_metrics'][k]-reference['macro_metrics'][k] for k in fresh['macro_metrics']},'prediction_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  if variant=='raw':
   targets=list(fresh['endpoints']);y,lo,hi,_=_truth_arrays(truth,targets)
   a=pred.set_index('Molecule_Name').loc[truth.Molecule_Name,targets].to_numpy(float);b=old.set_index('Molecule_Name').loc[truth.Molecule_Name,targets].to_numpy(float)
   group=np.array([scaffold(x) for x in truth.SMILES]);keys=np.unique(group);indices={key:np.flatnonzero(group==key) for key in keys};rng=np.random.default_rng(20261026);deltas=[];undefined=0
   for _ in range(1000):
    rows=np.concatenate([indices[key] for key in rng.choice(keys,size=len(keys),replace=True)])
    ca=_score_arrays(y[rows],lo[rows],hi[rows],a[rows],targets);cb=_score_arrays(y[rows],lo[rows],hi[rows],b[rows],targets)
    if not ca['defined'] or not cb['defined']:undefined+=1;continue
    deltas.append(ca['macro_ST_RAE']-cb['macro_ST_RAE'])
   entry['paired_scaffold_bootstrap']={'seed':20261026,'groups':len(keys),'valid_replicates':len(deltas),'undefined_replicates':undefined,'delta_ST_RAE_95pct_interval':np.quantile(deltas,[.025,.975]).tolist(),'interpretation':'Conditional on these fitted single-seed models; not training-seed uncertainty or an acceptance threshold.'}
  result[cohort][variant]=entry
result['limits']=['This is the corrected native reference, not an ADMETlab-feature candidate.','Outer cohorts remain frozen and overlap; results are not independent replications.','Broader stereo-related analogs and incomplete tautomer enumerations were not silently equated.','Native published placement is retained separately and is not a held-out-fitted calibrator.']
(ROOT/'verified-scoring.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps({c:{v:r['corrected']['macro_metrics'] for v,r in result[c].items()} for c in ['own750','briford529']},indent=2))
