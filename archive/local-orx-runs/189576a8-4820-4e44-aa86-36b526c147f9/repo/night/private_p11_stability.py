"""Conditional paired uncertainty of the predeclared simple metric. No fits."""
from pathlib import Path
import json,time,hashlib
import numpy as np,pandas as pd
from rdkit import Chem,RDLogger
from rdkit.Chem.Scaffolds import MurckoScaffold
from .private_p1 import sha,T
RDLogger.DisableLog('rdApp.*')
ROOT=Path(__file__).resolve().parents[1]
def main():
    c=json.loads((ROOT/'p11_stability_config.json').read_text());out=Path(c['output']);out.mkdir(parents=True,exist_ok=False)
    for r in c['inputs'].values():assert sha(r['path'])==r['sha256']
    d=pd.read_csv(c['inputs']['losses']['path']);truth=pd.read_csv(c['inputs']['truth']['path']).set_index('Molecule_Name');v=d[(d.cohort=='own750')&(d.lane=='raw')];names=['adapted','native','H6','anchored'];ids=sorted(v.Molecule_Name.unique());groups=[]
    for ident in ids:
        m=Chem.MolFromSmiles(truth.loc[ident,'SMILES']);groups.append(Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(m),isomericSmiles=False) or 'acyclic:'+Chem.MolToInchiKey(m).split('-')[0])
    uniq=sorted(set(groups));gmap={g:i for i,g in enumerate(uniq)};ix=np.array([gmap[g] for g in groups]);loss=np.zeros((len(names),len(ids),4));mask=np.zeros((len(ids),4))
    for k,name in enumerate(names):
        for j,t in enumerate(T):
            a=v[(v.model==name)&(v.target==t)].set_index('Molecule_Name');positions=np.array([ids.index(i) for i in a.index]);loss[k,positions,j]=a.abs_error.to_numpy();mask[positions,j]=1
    sums=np.zeros((len(names),len(uniq),4));counts=np.zeros((len(uniq),4))
    for g in range(len(uniq)):sums[:,g]=loss[:,ix==g].sum(1);counts[g]=mask[ix==g].sum(0)
    rng=np.random.default_rng(20261027);multiplicity=rng.multinomial(len(uniq),np.repeat(1/len(uniq),len(uniq)),size=1000);den=multiplicity@counts;assert (den>0).all()
    vals=np.stack([(multiplicity@sums[k]/den).mean(1) for k in range(4)],axis=1);point=(loss.sum(1)/mask.sum(0)).mean(1);expected=np.argsort(point);rows=[]
    for k in [0,2,3]:
        delta=vals[:,k]-vals[:,1];lo,hi=np.quantile(delta,[.025,.975]);rows.append({'candidate':names[k],'reference':'native','MAE_delta':float(point[k]-point[1]),'lower95':float(lo),'upper95':float(hi),'bootstrap_fraction_delta_positive':float((delta>0).mean())})
    decomposition=[]
    for (cohort,model),g in d[d.lane=='raw'].groupby(['cohort','model']):
        x=g.groupby('target').apply(lambda z:pd.Series({'normalized_MAE':z.abs_error.mean()/z.ST_denominator_mean.iloc[0],'ST_RAE':z.soft_error.mean()/z.ST_denominator_mean.iloc[0],'interval_credit':(z.abs_error-z.soft_error).mean()/z.ST_denominator_mean.iloc[0]}),include_groups=False).mean();decomposition.append({'cohort':cohort,'model':model,**x.to_dict()})
    pd.DataFrame(decomposition).to_csv(out/'interval-credit-decomposition.csv',index=False);pd.DataFrame(rows).to_csv(out/'MAE-paired-uncertainty.csv',index=False)
    report={'status':'complete','replicates':1000,'seed':20261027,'scaffold_groups':len(uniq),'own750_observed_union_rows':len(ids),'point_MAE':dict(zip(names,point.tolist())),'full_four_order_retained_fraction':float(np.all(np.argsort(vals,axis=1)==expected,axis=1).mean()),'paired_deltas':rows,'caveats':['Conditional scaffold bootstrap of existing predictions, not all training-seed or leaderboard-subset uncertainty.','Retrospectively selected metric: intervals do not correct metric or model selection.','Fraction positive is a bootstrap description, not posterior probability or proof of future gain.'],'base_model_fits':0,'calibrator_fits':0,'source_sha256':sha(__file__)}
    (out/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
