"""Seal an evaluation BEFORE a future leaderboard result. No fits or submission.

Inputs must be genuine outer predictions on the existing complete cohorts.
Local raw/recipe-output pIC50 must not include blind-population moment placement.
This tool cannot establish training exclusion provenance from a CSV alone.
"""
import argparse,json,hashlib,datetime
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import pearsonr,spearmanr,kendalltau
ROOT=Path(__file__).resolve().parent
T=[f'{x}_pIC50_direct_inhibition' for x in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def evaluate(y,p,l,h):
    per={}
    for j,t in enumerate(T):
        m=np.isfinite(y[:,j]);a=y[m,j];q=p[m,j];ll=l[m,j];hh=h[m,j]
        den=np.mean(abs(a.mean()-np.clip(a.mean(),ll,hh)))
        per[t]={'n':len(a),'MAE':float(np.mean(abs(a-q))),'RMSE':float(np.sqrt(np.mean((a-q)**2))),
                'ST_RAE':float(np.mean(abs(q-np.clip(q,ll,hh)))/den),'R2':float(1-np.mean((a-q)**2)/np.var(a)),
                'Pearson':float(pearsonr(a,q).statistic),'Spearman':float(spearmanr(a,q).statistic),'Kendall':float(kendalltau(a,q).statistic)}
    return {'macro':{k:float(np.mean([v[k] for v in per.values()])) for k in ['MAE','RMSE','ST_RAE','R2','Pearson','Spearman','Kendall']},'per_CYP':per}
def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--own',required=True,type=Path);a.add_argument('--briford',required=True,type=Path);a.add_argument('--blind',required=True,type=Path);a.add_argument('--output',required=True,type=Path);a.add_argument('--provenance',required=True,type=Path,help='Saved scientific provenance confirming whole outer exclusion and recipe/final correspondence');v=a.parse_args()
    assert not v.output.exists(),'Never overwrite a pre-result evaluation'
    cfg=json.loads((ROOT/'INPUT_MANIFEST.json').read_text());truthspec=cfg['files']['official_train'];cohortspec=cfg['files']['cohorts'];blindsp=cfg['files']['official_blind']
    for r in [truthspec,cohortspec,blindsp]:assert sha(r['path'])==r['sha256']
    truth=pd.read_csv(truthspec['path']).set_index('Molecule_Name');cohorts=json.loads(Path(cohortspec['path']).read_text())['cohorts'];results={};input_hashes={}
    for name,path in [('own750',v.own),('briford529',v.briford)]:
        q=pd.read_csv(path).set_index('Molecule_Name');ids=cohorts[name]['test_ids'];assert q.index.is_unique and set(q.index)==set(ids);q=q.loc[ids];f=truth.loc[ids];assert q.SMILES.tolist()==f.SMILES.tolist();pred=q[T].to_numpy(float);assert np.isfinite(pred).all()
        result=evaluate(f[T].to_numpy(float),pred,f[[t+'_conf_low' for t in T]].to_numpy(float),f[[t+'_conf_high' for t in T]].to_numpy(float));results[name]=result;input_hashes[name]={'path':str(path.resolve()),'sha256':sha(path)}
    blind=pd.read_csv(blindsp['path']);q=pd.read_csv(v.blind);assert q.Molecule_Name.tolist()==blind.Molecule_Name.tolist() and q.SMILES.tolist()==blind.SMILES.tolist();z=q[T].to_numpy(float);assert np.isfinite(z).all()
    ref=pd.read_csv(cfg['submissions']['native']['csv']['path'])[T].to_numpy(float);assert sha(cfg['submissions']['native']['csv']['path'])==cfg['submissions']['native']['sha256']
    local=pd.read_csv(ROOT/'results/local-metrics.csv');base=local[(local.model=='native')&(local.cohort=='own750')&(local.lane=='raw')].iloc[0]
    result={'sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'metric_protocol':'P11-provisional-v1','provisional_primary_metric':'macro_MAE_own750_before_blind_population_placement','value':results['own750']['macro']['MAE'],'delta_vs_exact_original_recipe':results['own750']['macro']['MAE']-float(base.MAE),'all_metrics':results,
        'blind_distribution_diagnostics':{t:{'mean_shift_vs_incumbent':float(z[:,j].mean()-ref[:,j].mean()),'SD_ratio_vs_incumbent':float(z[:,j].std(ddof=1)/ref[:,j].std(ddof=1)),'floor1_count':int((z[:,j]<=1+1e-12).sum())} for j,t in enumerate(T)},
        'inputs':{**input_hashes,'blind':{'path':str(v.blind.resolve()),'sha256':sha(v.blind)},'provenance':{'path':str(v.provenance.resolve()),'sha256':sha(v.provenance)}},'numeric_leaderboard_forecast':None,'automatic_promotion_or_submission':False,
        'limitations':['Metric chosen retrospectively from four related submissions; future forecast validity unestablished.','CSV identity does not verify model training provenance; human review of provided provenance remains necessary.','No arbitrary distribution-drift cutoff; report changes and test calibration policy separately.','Do not replace missing labels or count overlapping cohorts as independent evidence.']}
    v.output.parent.mkdir(parents=True,exist_ok=True);v.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({'file':str(v.output),'primary_macro_MAE':result['value'],'delta':result['delta_vs_exact_original_recipe'],'leaderboard_forecast':None}))
if __name__=='__main__':main()
