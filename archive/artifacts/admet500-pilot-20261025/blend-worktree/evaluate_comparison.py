from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error,r2_score
from official_scoring_functions import rae_soft_threshold_absolute_error as official
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'outputs';CACHE=ROOT/'prepared'
df=pd.read_csv(ROOT/'data/official-train.csv').set_index('Molecule_Name')
cols=json.loads((CACHE/'target-columns.json').read_text())['primary'];roles=json.loads((CACHE/'roles.json').read_text())
parent=json.loads((CACHE/'parent-keys.json').read_text());idkeys=dict(zip(df.index,parent))
def load(path,ids):
    p=pd.read_csv(path).set_index('Molecule_Name');assert p.index.is_unique and set(p.index)==set(ids),(path,len(p),len(ids))
    a=p.loc[ids,cols].to_numpy();assert np.isfinite(a).all();return a

def score(y,p,lo,hi):
    den=np.maximum(lo-y.mean(),0).sum()+np.maximum(y.mean()-hi,0).sum();assert den>0
    return float((np.maximum(lo-p,0).sum()+np.maximum(p-hi,0).sum())/den)
def evaluate(ids,preds):
    d=df.loc[ids];y=d[cols].to_numpy();lo=d[[c+'_conf_low' for c in cols]].to_numpy();hi=d[[c+'_conf_high' for c in cols]].to_numpy();scores={}
    group={}
    for i,id in enumerate(ids):group.setdefault(idkeys[id],[]).append(i)
    members=list(group.values());rng=np.random.default_rng(20261024)
    samples=[np.concatenate([members[j] for j in rng.integers(len(members),size=len(members))]) for _ in range(1000)]
    bs={}
    for name,p in preds.items():
        per={}
        for k,c in enumerate(cols):
            m=np.isfinite(y[:,k]);yt=y[m,k];pt=p[m,k];l=lo[m,k];h=hi[m,k]
            st=score(yt,pt,l,h);assert abs(st-float(official(yt,pt,h,l)))<1e-6
            per[c]={'n':int(m.sum()),'ST_RAE':st,'MAE':float(mean_absolute_error(yt,pt)),'R2':float(r2_score(yt,pt)),'Spearman':float(spearmanr(yt,pt).statistic) if np.ptp(pt)>0 and np.ptp(yt)>0 else None}
        b=[]
        for ii in samples:
            vv=[]
            for k in range(4):
                idx=ii[np.isfinite(y[ii,k])];vv.append(score(y[idx,k],p[idx,k],lo[idx,k],hi[idx,k]))
            b.append(np.mean(vv))
        b=np.asarray(b);bs[name]=b;scores[name]={'macro_ST_RAE':float(np.mean([v['ST_RAE'] for v in per.values()])),'macro_MAE':float(np.mean([v['MAE'] for v in per.values()])),'paired_parent_bootstrap_mean':float(b.mean()),'paired_parent_bootstrap_95CI':np.quantile(b,[.025,.975]).tolist(),'endpoints':per}
    differences={}
    for name in preds:
        if name=='our_chemeleon':continue
        delta=bs[name]-bs['our_chemeleon'];differences[name+' minus our_chemeleon']={'point_difference':scores[name]['macro_ST_RAE']-scores['our_chemeleon']['macro_ST_RAE'],'paired_bootstrap_95CI':np.quantile(delta,[.025,.975]).tolist()}
    return {'n_molecules':len(ids),'bootstrap_unit':'normalized parent without stereochemistry','n_parent_groups':len(members),'models':scores,'paired_differences':differences},bs

results={};pool={};poolids=[];boot={}
models=['jeremy_ensemble','lgb_matched','lgb','tabpfn_adme_pretrain','tabpfn_chemeleon','chemprop_multitask']
for split,r in roles.items():
    ids=df.index[r['test']].tolist();preds={m:load(OUT/split/(m+'.csv'),ids) for m in models}
    own=ROOT/'data/our-existing-predictions.csv' if split=='our_fixed_750' else OUT/split/'chemeleon/outputs/holdout_predictions.csv'
    preds['our_chemeleon']=load(own,ids)
    trainmean=df.iloc[r['fit']][cols].mean().to_numpy();preds['train_mean']=np.repeat(trainmean[None,:],len(ids),axis=0)
    results[split],bb=evaluate(ids,preds)
    for k,b in bb.items():boot[split+'__'+k]=b
    if split.startswith('jeremy_'):
        poolids.extend(ids)
        for m,p in preds.items():pool.setdefault(m,[]).append(p)
    print('COMPARISON_SPLIT',split,json.dumps({m:v['macro_ST_RAE'] for m,v in results[split]['models'].items()}),flush=True)
assert len(poolids)==len(df) and len(set(poolids))==len(df)
results['jeremy_pooled_oof'],bb=evaluate(poolids,{m:np.concatenate(ps) for m,ps in pool.items()})
for k,b in bb.items():boot['jeremy_pooled_oof__'+k]=b
np.savez_compressed(OUT/'paired_bootstrap.npz',**boot)
res={'protocol':json.loads((ROOT/'protocol.json').read_text()),'results':results,'bootstrap_note':'Conditional on these fitted models and assignments. PooledOOF bootstrap does not estimate training-seed variation or fold dependence. Our original750 already inspected in previous baseline; no new selection in this run.'}
(OUT/'comparison.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
rows=[]
for split,r in results.items():
    for m,v in r['models'].items():rows.append({'split':split,'model':m,'macro_ST_RAE':v['macro_ST_RAE'],'macro_MAE':v['macro_MAE'],'ci_low':v['paired_parent_bootstrap_95CI'][0],'ci_high':v['paired_parent_bootstrap_95CI'][1]})
pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
files=[p for p in OUT.rglob('*') if p.is_file() and p.suffix in ['.csv','.json','.pt','.ckpt','.npz']]
(OUT/'sha256.json').write_text(json.dumps({str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))
print('POOLED_RESULT',json.dumps({m:v['macro_ST_RAE'] for m,v in results['jeremy_pooled_oof']['models'].items()}),flush=True)
