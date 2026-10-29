"""Four-submission retrospective audit. No training, network, or dispatch."""
from pathlib import Path
from itertools import combinations
import json,time,signal,hashlib
import numpy as np,pandas as pd
from scipy.stats import pearsonr,spearmanr,kendalltau
from .private_p1 import scores,T,sha

ROOT=Path(__file__).resolve().parents[1]
NAMES=['adapted','native','H6','anchored']
MET=['ST_RAE','MAE','RMSE','R2','Pearson','Spearman','Kendall']
SIGN={m:(1 if m in ['ST_RAE','MAE','RMSE'] else -1) for m in MET}
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def verify_tree(x):
    if isinstance(x,dict):
        if 'path' in x and 'sha256' in x:assert sha(x['path'])==x['sha256'],x['path']
        else:
            for v in x.values():verify_tree(v)
    elif isinstance(x,list):
        for v in x:verify_tree(v)
def extended(y,p,l,h):
    d=scores(y,p,l,h)
    for j,t in enumerate(T):
        m=np.isfinite(y[:,j]);a=y[m,j];b=p[m,j]
        d['per_cyp'][t].update(RMSE=float(np.sqrt(np.mean((a-b)**2))),Pearson=float(pearsonr(a,b).statistic))
    for k in ['RMSE','Pearson']:d['macro'][k]=float(np.mean([d['per_cyp'][t][k] for t in T]))
    return d
def read(record,ids,smiles=None):
    d=pd.read_csv(record['path']).set_index('Molecule_Name');assert d.index.is_unique and set(d.index)==set(ids)
    d=d.loc[ids]
    if smiles is not None and 'SMILES' in d:assert d.SMILES.tolist()==list(smiles)
    a=d[T].to_numpy(float);assert np.isfinite(a).all();return a
def affinity_order(x,y,indices):
    pairs=list(combinations(indices,2));v=[float(np.sign(x[a]-x[b])==np.sign(y[a]-y[b])) if x[a]!=x[b] else .5 for a,b in pairs]
    return float(np.mean(v))

def main():
    start=time.time();signal.signal(signal.SIGALRM,lambda *a:(_ for _ in ()).throw(TimeoutError('P11 bounded analysis')));signal.alarm(600)
    c=json.loads((ROOT/'p11_config.json').read_text());verify_tree(c);out=Path(c['output']);out.mkdir(exist_ok=False,parents=True)
    tr=pd.read_csv(c['files']['official_train']['path']).set_index('Molecule_Name');blind=pd.read_csv(c['files']['official_blind']['path']);assert set(blind)=={'Molecule_Name','SMILES'}
    cohorts=json.loads(Path(c['files']['cohorts']['path']).read_text())['cohorts'];geom=pd.read_csv(c['files']['geometry']['path'])
    names=NAMES;lb=[];local=[];per=[];mom=[];affine=[];support=[];weighted=[];lossrows=[];banks={};label_summary=[]
    for name,s in c['submissions'].items():
        r=json.loads(Path(s['result']['path']).read_text());row=r['matches'][0] if 'matches' in r else r['public_entry'];assert row['Username']=='AdeliyaLL-CYP'
        lb.append({'model':name,'sent':s['sent'],'sha256':s['sha256'],'rank_at_observation':int(row['Rank']),**{k:float(row[v]) for k,v in {'ST_RAE':'MA-ST-RAE','MAE':'MA-MAE','R2':'MA-R²','Spearman':"MA-Spearman's ρ",'Kendall':"MA-Kendall's τ"}.items()}})
    board=pd.DataFrame(lb).set_index('model').loc[names];board.to_csv(out/'submission-history.csv');target=board.ST_RAE.to_numpy()
    for cohort in ['own750','briford529','blind750']:
        isblind=cohort=='blind750';frame=blind.set_index('Molecule_Name') if isblind else tr.loc[cohorts[cohort]['test_ids']];ids=frame.index.tolist()
        if not isblind:
            y=frame[T].to_numpy(float);lo=frame[[t+'_conf_low' for t in T]].to_numpy(float);hi=frame[[t+'_conf_high' for t in T]].to_numpy(float)
            for j,t in enumerate(T):
                m=np.isfinite(y[:,j]);label_summary.append({'cohort':cohort,'target':t,'query_rows':len(ids),'observed':int(m.sum()),'truth_mean':y[m,j].mean(),'truth_sd':y[m,j].std(),'CI_median_width':np.median(hi[m,j]-lo[m,j]),'ST_denominator_mean':np.mean(abs(y[m,j].mean()-np.clip(y[m,j].mean(),lo[m,j],hi[m,j]))),'fully_labeled_rows':int(np.isfinite(y).all(1).sum())})
        vectors={}
        for name in names:
            spec=c['submissions'][name] if isblind else c['local'][cohort][name]
            if isblind:vectors[name]={'served':read(spec['csv'],ids,frame.SMILES)};vectors[name].update({'raw':read(spec['raw'],ids,frame.SMILES)} if 'raw' in spec else {})
            elif name=='adapted':vectors[name]={'raw':(read(spec['seed42'],ids)+read(spec['seed142'],ids))/2}
            else:vectors[name]={lane:read(spec[lane],ids,frame.SMILES) for lane in ['raw','served']}
        banks[cohort]=vectors
        for name,lanes in vectors.items():
            for lane,p in lanes.items():
                for j,t in enumerate(T):
                    mom.append({'cohort':cohort,'model':name,'lane':lane,'target':t,'mean':p[:,j].mean(),'sd':p[:,j].std(ddof=1),'min':p[:,j].min(),'max':p[:,j].max(),'floor1_count':int((p[:,j]<=1+1e-12).sum()),'unique':len(np.unique(p[:,j]))})
                if isblind:continue
                sc=extended(y,p,lo,hi);local.append({'cohort':cohort,'model':name,'lane':lane,**sc['macro']});per.extend({'cohort':cohort,'model':name,'lane':lane,'target':t,**v} for t,v in sc['per_cyp'].items())
                for j,t in enumerate(T):
                    m=np.isfinite(y[:,j]);a=y[m,j];q=p[m,j];den=np.mean(abs(a.mean()-np.clip(a.mean(),lo[m,j],hi[m,j])))
                    for ident,yy,pp,ll,hh in zip(np.array(ids)[m],a,q,lo[m,j],hi[m,j]):lossrows.append({'cohort':cohort,'model':name,'lane':lane,'target':t,'Molecule_Name':ident,'y':yy,'prediction':pp,'lower':ll,'upper':hh,'soft_error':abs(pp-np.clip(pp,ll,hh)),'abs_error':abs(pp-yy),'squared_error':(pp-yy)**2,'ST_denominator_mean':den})
            if 'raw' in lanes and 'served' in lanes:
                for j,t in enumerate(T):
                    a=lanes['raw'][:,j];b=lanes['served'][:,j];m=b>1+1e-10
                    scale=np.cov(a[m],b[m],ddof=0)[0,1]/np.var(a[m]);offset=b[m].mean()-scale*a[m].mean();err=np.max(abs(np.maximum(scale*a+offset,1)-b))
                    assert err<1e-8,(cohort,name,t,err)
                    affine.append({'cohort':cohort,'model':name,'target':t,'slope':scale,'intercept':offset,'reconstruction_error':err,'raw_served_spearman':spearmanr(a,b).statistic})
        if isblind:continue
        # Single fixed structural-support reweighting diagnostic. No outcome-derived bins.
        bins=np.array([0,.2,.4,.6,.8,1.000001]);ws=[]
        for j,t in enumerate(T):
            ep=t.split('_')[0];obs=np.isfinite(y[:,j]);validids=np.array(ids)[obs]
            g=geom[(geom.context==cohort)&(geom.pool==ep)].set_index('Molecule_Name').loc[validids]
            ref=geom[(geom.context=='blind750_full_train')&(geom.pool==ep)]
            a=np.clip(np.digitize(g.nearest_similarity,bins)-1,0,4);b=np.clip(np.digitize(ref.nearest_similarity,bins)-1,0,4)
            ca=np.bincount(a,minlength=5);cb=np.bincount(b,minlength=5);mass=cb/cb.sum();w=np.array([mass[k]/(ca[k]/ca.sum()) for k in a]);w/=w.sum();ws.append(w)
            support.append({'cohort':cohort,'target':t,'n':len(a),'ESS':1/np.sum(w*w),'test_mass_covered':mass[ca>0].sum(),'max_weight':w.max(),'bins':json.dumps(bins.tolist()),'holdout_counts':json.dumps(ca.tolist()),'blind_counts':json.dumps(cb.tolist())})
        for name,lanes in vectors.items():
            p=lanes['raw'];sc=[];ma=[]
            for j in range(4):
                m=np.isfinite(y[:,j]);w=ws[j];a=y[m,j];q=p[m,j];l=lo[m,j];h=hi[m,j];mean=w@a;den=w@abs(mean-np.clip(mean,l,h));sc.append(w@abs(q-np.clip(q,l,h))/den);ma.append(w@abs(a-q))
            weighted.append({'cohort':cohort,'model':name,'support_weighted_ST_RAE':np.mean(sc),'support_weighted_MAE':np.mean(ma)})
    df=pd.DataFrame(local);df.to_csv(out/'local-metrics.csv',index=False);pd.DataFrame(per).to_csv(out/'per-CYP-local-metrics.csv',index=False);pd.DataFrame(mom).to_csv(out/'prediction-moments.csv',index=False);pd.DataFrame(affine).to_csv(out/'effective-affine.csv',index=False);pd.DataFrame(lossrows).to_csv(out/'paired-loss-bank.csv',index=False);pd.DataFrame(support).to_csv(out/'support-reweighting-coverage.csv',index=False);pd.DataFrame(weighted).to_csv(out/'support-reweighted-metrics.csv',index=False);pd.DataFrame(label_summary).to_csv(out/'label-support.csv',index=False)
    candidates={}
    for metric in MET:
        a=df[(df.cohort=='own750')&(df.lane=='raw')].set_index('model').loc[names,metric].to_numpy()*SIGN[metric]
        b=df[(df.cohort=='briford529')&(df.lane=='raw')].set_index('model').loc[names,metric].to_numpy()*SIGN[metric]
        for agg,v in [('own',a),('briford',b),('mean',(a+b)/2),('worst',np.maximum(a,b))]:candidates[metric+'__'+agg]=v
    assoc=[]
    for key,v in candidates.items():
        assoc.append({'candidate_metric':key,'rank_spearman_all4':spearmanr(v,target).statistic,'pair_accuracy_all6':affinity_order(v,target,range(4)),'pair_accuracy_first3':affinity_order(v,target,range(3)),'fourth_vs_native_correct':bool(np.sign(v[3]-v[1])==np.sign(target[3]-target[1])),'first_vs_native_correct':bool(np.sign(v[0]-v[1])==np.sign(target[0]-target[1])),'scores':json.dumps(dict(zip(names,v)))})
    ad=pd.DataFrame(assoc);ad.to_csv(out/'metric-association-retrospective.csv',index=False)
    best=ad.pair_accuracy_first3.max();sel=ad[ad.pair_accuracy_first3==best]
    chronological={'first_three_best_pair_accuracy':float(best),'tied_metric_count':len(sel),'tied_metrics':sel.candidate_metric.tolist(),'fourth_vs_native_correct_fraction':float(sel.fourth_vs_native_correct.mean()),'honesty':'Metric menu and analysis created after all four outcomes. Chronological replay is diagnostic, NOT a prospective validation or reliable metric-selection estimate.'}
    loo=[]
    for held in range(4):
        train=[i for i in range(4) if i!=held];acc={k:affinity_order(v,target,train) for k,v in candidates.items()};best=max(acc.values());keys=[k for k,v in acc.items() if v==best]
        aa=[float(np.sign(candidates[k][held]-candidates[k][i])==np.sign(target[held]-target[i])) for k in keys for i in train]
        loo.append({'held_submission':names[held],'best_training_pair_accuracy':best,'tied_metrics':len(keys),'held_pair_accuracy_over_ties':float(np.mean(aa))})
    # P1 and P5b exact old metrics are required arithmetic regression controls.
    prior=pd.read_csv(c['files']['p5b']['path']);errs=[]
    for cohort in ['own750','briford529']:
        for name,arm in [('native','incumbent'),('anchored','refit_original_OOF')]:
            old=prior[(prior.cohort==cohort)&(prior.lane=='raw')&(prior.arm==arm)].iloc[0];new=df[(df.cohort==cohort)&(df.lane=='raw')&(df.model==name)].iloc[0]
            errs.extend(abs(old[k]-new[k]) for k in ['ST_RAE','MAE','R2','Spearman','Kendall'])
    assert max(errs)<1e-12
    summary={'status':'complete','seconds':time.time()-start,'submissions':4,'matched_outer_cohorts':2,'outer_ID_overlap':len(set(cohorts['own750']['test_ids'])&set(cohorts['briford529']['test_ids'])),'metric_candidates':28,'no_new_base_models':True,'no_calibrator_or_metric_weight_fit':True,'new_blind_score_estimated':False,'old_metric_max_error':max(errs),'chronological_replay':chronological,'leave_one_submission_out':loo,'best_all4_retrospective_metrics':ad.sort_values(['pair_accuracy_all6','rank_spearman_all4'],ascending=False).head(8).to_dict('records'),'limitations':['Four submissions are dependent, not four independent tests; correlated metrics and overlapping reused cohorts.', 'First adapted candidate local output already contains OOF-affine mapping; raw lane label means recipe output for it.','Blind file has750 rows; live score uses unknown chemical-series subset. No subset labels or membership reconstructed.','No local served diagnostic with published blind moments is an unbiased hidden-score estimate.','Support weighting corrects only one observed covariate, not missing-not-at-random labels or lack of target support.','External ensemble/source/pretraining overlap limitations retained.'],'input_manifest_sha256':sha(ROOT/'p11_config.json'),'source_sha256':sha(__file__)}
    save(out/'SUMMARY.json',summary);save(out/'INPUT_MANIFEST.json',c);print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
