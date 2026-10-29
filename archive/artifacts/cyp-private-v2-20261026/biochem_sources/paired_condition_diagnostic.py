"""Read-only paired-condition description; no fit, inferred bounds or network."""
from pathlib import Path
import hashlib, json, os
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'p6'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def summarize(frame):
    return {'n': len(frame), 'shift_median': float(frame['shift'].median()),
            'shift_q10': float(frame['shift'].quantile(.1)),
            'shift_q90': float(frame['shift'].quantile(.9)),
            'negative_n': int((frame['shift'] < 0).sum()),
            'negative_nonoverlap_n': int(frame['negative_nonoverlap'].sum()),
            'positive_nonoverlap_n': int(frame['positive_nonoverlap'].sum()),
            'direct_median': float(frame['direct'].median()),
            'direct_width_median': float(frame['direct_width'].median()),
            'active_width_median': float(frame['active_width'].median())}

def main():
    os.umask(0o077)
    src = json.loads((ROOT/'biochem_sources/official-table-audit.json').read_text())['source_files']
    for key in ('inhibition','tdi','single_concentration'):
        assert digest(src[key]['path']) == src[key]['sha256'], key
    direct = pd.read_csv(src['inhibition']['path']).set_index('molecule_name')
    active = pd.read_csv(src['tdi']['path']).set_index('molecule_name')
    single = pd.read_csv(src['single_concentration']['path'])
    assert direct.index.is_unique and active.index.is_unique
    common = direct.index.intersection(active.index)
    assert direct.loc[common,'smiles'].equals(active.loc[common,'smiles'])
    rows, groups, corrs, pairs = [], [], [], []
    for target in ('cyp1a2','cyp2c9','cyp2d6','cyp3a4'):
        dc = target+'_pic50_direct_inhibition'
        ac = target+'_pic50_tdi_condition'
        assert np.allclose(direct.loc[common,dc], active.loc[common,dc], equal_nan=True)
        x = pd.DataFrame({'molecule_name':common, 'direct':direct.loc[common,dc].to_numpy(),
                         'active':active.loc[common,ac].to_numpy(),
                         'direct_lo':direct.loc[common,dc+'_ci_lower'].to_numpy(),
                         'direct_hi':direct.loc[common,dc+'_ci_upper'].to_numpy(),
                         'active_lo':active.loc[common,ac+'_ci_lower'].to_numpy(),
                         'active_hi':active.loc[common,ac+'_ci_upper'].to_numpy()})
        x = x.dropna().copy()
        assert np.isfinite(x.select_dtypes('number')).all().all()
        assert (x.direct_hi>=x.direct_lo).all() and (x.active_hi>=x.active_lo).all()
        x['shift'] = x.active-x.direct
        x['direct_width'] = x.direct_hi-x.direct_lo
        x['active_width'] = x.active_hi-x.active_lo
        x['negative_nonoverlap'] = x.active_hi < x.direct_lo
        x['positive_nonoverlap'] = x.active_lo > x.direct_hi
        x['target'] = target
        q = single[single.enzyme.str.lower()==target].copy()
        assert q.molecule_name.is_unique
        x = x.merge(q[['molecule_name','plate_id','cohens_d','log2fc_estimate','log2fc_std_error']],
                    on='molecule_name',how='left',validate='1:1')
        rows.append({'target':target, **summarize(x), 'single_observed':int(x.plate_id.notna().sum())})
        for variable in ('direct','direct_width','active_width'):
            x[variable+'_quintile'] = pd.qcut(x[variable],5,labels=False,duplicates='drop')
            for quintile, sub in x.groupby(variable+'_quintile'):
                groups.append({'target':target,'group_variable':variable,'quintile':int(quintile),**summarize(sub)})
        for variable in ('direct','direct_width','active_width','cohens_d','log2fc_estimate','log2fc_std_error'):
            sub=x[['shift',variable]].dropna()
            r = spearmanr(sub['shift'],sub[variable]).statistic if len(sub)>2 and sub[variable].nunique()>1 else None
            corrs.append({'target':target,'variable':variable,'n':len(sub),'spearman':r})
        pairs.append(x)
    OUT.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT/'paired-summary.csv',index=False)
    pd.DataFrame(groups).to_csv(OUT/'quintile-descriptions.csv',index=False)
    pd.DataFrame(corrs).to_csv(OUT/'descriptive-correlations.csv',index=False)
    pd.concat(pairs,ignore_index=True).to_csv(OUT/'paired-source-values.csv',index=False)
    receipt={'source_pins':{k:src[k] for k in ('inhibition','tdi','single_concentration')},
             'script_sha256':digest(__file__), 'fits':0,'network_requests':0,
             'caveats':['Marginal intervals are not the posterior of the paired difference.',
                        'Potency-difference correlation has mathematical coupling.',
                        'Plate covariates are diagnostic only; unavailable for blind queries.',
                        'Quintiles describe the observed cohort and are not new label rules.'],
             'outputs_sha256':{p.name:digest(p) for p in OUT.glob('*.csv')}}
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'event':'paired_condition_description','summary':rows,'fits':0},indent=2))

if __name__=='__main__': main()
