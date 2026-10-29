"""Actual frozen cohort geometry and released-label regimes. No model fit or hidden labels."""
from pathlib import Path
import os,json,hashlib
from collections import Counter
import numpy as np,pandas as pd
from scipy.stats import wasserstein_distance
from rdkit import Chem,DataStructs,RDLogger
from rdkit.Chem import rdMolDescriptors,rdFingerprintGenerator,Descriptors
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.ML.Cluster import Butina
RDLogger.DisableLog('rdApp.*');os.umask(0o077)
ROOT=Path(__file__).resolve().parent;WORK=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition');G=WORK/'artifacts/goal-20261026';OLD=WORK/'artifacts/chemical-space-audit-20261023';TARGETS=[f'{c}_pIC50_direct_inhibition' for c in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,v):(ROOT/name).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
m=json.loads((G/'model-audit/official-snapshot-18460/manifest.json').read_text())
for k in ['official_train','official_test','cohorts']:assert sha(m['files'][k]['path'])==m['files'][k]['sha256']
train=pd.read_csv(m['files']['official_train']['path']);blind=pd.read_csv(m['files']['official_test']['path']);assert set(blind)=={'Molecule_Name','SMILES'};cohorts=json.loads(Path(m['files']['cohorts']['path']).read_text())['cohorts'];lookup={n:i for i,n in enumerate(train.Molecule_Name)}
cache_manifest=json.loads((OLD/'manifest.json').read_text());assert cache_manifest['source_sha256']['cyp-challenge-TRAIN_inhibition.csv']==sha(m['files']['official_train']['path']) and cache_manifest['source_sha256']['cyp-challenge-TEST-BLINDED.csv']==sha(m['files']['official_test']['path'])
cache=np.load(OLD/'similarity_matrices.npz');tt=cache['train_train'];bt=cache['test_train'];bb=cache['test_test'];assert tt.shape==(4905,4905) and bt.shape==(750,4905) and bb.shape==(750,750)
gen=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048,includeChirality=False);molcache={}
def features(smi):
 if smi not in molcache:
  mol=Chem.MolFromSmiles(smi);assert mol is not None
  parent=rdMolStandardize.FragmentParent(rdMolStandardize.Cleanup(mol),skipStandardize=True);sc=MurckoScaffold.GetScaffoldForMol(parent);scs=Chem.MolToSmiles(sc,isomericSmiles=False);generic=Chem.MolToSmiles(MurckoScaffold.MakeScaffoldGeneric(sc),isomericSmiles=False) if scs else ''
  molcache[smi]={'fp':gen.GetFingerprint(parent),'murcko':scs,'generic':generic,'MW':Descriptors.MolWt(parent),'cLogP':Descriptors.MolLogP(parent),'TPSA':Descriptors.TPSA(parent),'fraction_CSP3':rdMolDescriptors.CalcFractionCSP3(parent),'canonical_isomeric':Chem.MolToSmiles(mol)}
 return molcache[smi]
tf=[features(s) for s in train.SMILES];bf=[features(s) for s in blind.SMILES]
for i in [0,321,749]:assert np.max(np.abs(np.asarray(DataStructs.BulkTanimotoSimilarity(bf[i]['fp'],[f['fp'] for f in tf]))-bt[i]))<1e-7
observed=train[TARGETS].notna().to_numpy();contexts={'blind750_full_train':(np.arange(750),np.arange(4905),True)}
for name,c in cohorts.items():
 if name not in ['own750','briford529']:continue
 tr=np.array([lookup[x] for x in c['train_ids']]);te=np.array([lookup[x] for x in c['test_ids']]);assert not set(tr)&set(te);contexts[name]=(te,tr,False);contexts['blind750_vs_'+name+'_train']=(np.arange(750),tr,True)
rows=[];perquery=[];distributions={}
for context,(qidx,ridx,isblind) in contexts.items():
 qmeta=bf if isblind else tf;matrix=bt if isblind else tt
 for pool,j in [('all',None)]+[(t.split('_')[0],j) for j,t in enumerate(TARGETS)]:
  refs=ridx if j is None else ridx[observed[ridx,j]];query=qidx if isblind or j is None else qidx[observed[qidx,j]];a=matrix[np.ix_(query,refs)];nearest=a.max(1);arg=refs[a.argmax(1)];top5=np.sort(a,axis=1)[:,-min(5,len(refs)):].mean(1);known={tf[i]['murcko'] for i in refs if tf[i]['murcko']};seen=np.array([bool(qmeta[i]['murcko']) and qmeta[i]['murcko'] in known for i in query]);gknown={tf[i]['generic'] for i in refs if tf[i]['generic']};gseen=np.array([bool(qmeta[i]['generic']) and qmeta[i]['generic'] in gknown for i in query]);anchors=Counter(arg.tolist());fractions=np.array(list(anchors.values()))/len(query)
  distributions[(context,pool)]=nearest
  rows.append({'context':context,'pool':pool,'query_rows':len(query),'reference_rows':len(refs),'median_NN':np.median(nearest),'mean_NN':nearest.mean(),'q10_NN':np.quantile(nearest,.1),'q90_NN':np.quantile(nearest,.9),'mean_top5':top5.mean(),'fraction_NN_ge_0.7':np.mean(nearest>=.7),'exact_Murcko_seen_fraction':seen.mean(),'generic_Murcko_seen_fraction':gseen.mean(),'distinct_nearest_training_anchors':len(anchors),'effective_nearest_training_anchors':1/np.sum(fractions**2),'top10_anchor_share':sum(sorted(anchors.values(),reverse=True)[:10])/len(query)})
  for k,i in enumerate(query):perquery.append({'context':context,'pool':pool,'Molecule_Name':blind.Molecule_Name.iloc[i] if isblind else train.Molecule_Name.iloc[i],'nearest_similarity':nearest[k],'mean_top5':top5[k],'nearest_training_id':train.Molecule_Name.iloc[arg[k]],'murcko_seen':bool(seen[k])})
pd.DataFrame(rows).to_csv(ROOT/'actual_reference_geometry.csv',index=False);pd.DataFrame(perquery).to_csv(ROOT/'geometry_per_query.csv',index=False)
comparisons=[]
for name in ['own750','briford529']:
 for pool in ['all']+[t.split('_')[0] for t in TARGETS]:
  a=distributions[(name,pool)];b=distributions[('blind750_full_train',pool)];matched=distributions[('blind750_vs_'+name+'_train',pool)];comparisons.append({'holdout':name,'pool':pool,'W1_to_actual_full_train_test':wasserstein_distance(a,b),'W1_to_same_reference_pool_test':wasserstein_distance(a,matched)})
pd.DataFrame(comparisons).to_csv(ROOT/'geometry_distance_to_blind.csv',index=False)
# Query-query series proxies, explicitly not the organizer's unreleased parent-series labels.
series=[]
for context in ['blind750_full_train','own750','briford529']:
 qidx,_,isblind=contexts[context];qmeta=bf if isblind else tf;matrix=bb if isblind else tt;all_a=matrix[np.ix_(qidx,qidx)].copy();np.fill_diagonal(all_a,-1)
 for pool,j in [('all',None)]+([] if isblind else [(t.split('_')[0],j) for j,t in enumerate(TARGETS)]):
  ids=qidx if j is None else qidx[observed[qidx,j]];a=matrix[np.ix_(ids,ids)].copy();np.fill_diagonal(a,-1);n=len(ids);nearest=a.max(1);dist=[float(1-a[i,j]) for i in range(1,n) for j in range(i)]
  for cutoff in [.6,.7,.8]:
   clusters=Butina.ClusterData(dist,n,1-cutoff,isDistData=True,reordering=True);sizes=np.array([len(x) for x in clusters]);series.append({'context':context,'observed_pool':pool,'n':n,'Tanimoto_cutoff':cutoff,'median_within_query_NN':np.median(nearest),'fraction_within_query_NN_ge_cutoff':np.mean(nearest>=cutoff),'Butina_proxy_clusters':len(sizes),'singleton_compound_fraction':np.sum(sizes==1)/n,'largest_proxy_cluster':int(sizes.max()),'effective_proxy_clusters':float(1/np.sum((sizes/n)**2))})
pd.DataFrame(series).to_csv(ROOT/'query_series_proxies.csv',index=False)
rng=np.random.default_rng(20261026);matched=[]
for _ in range(30):
 idx=rng.choice(750,529,replace=False);a=bb[np.ix_(idx,idx)].copy();np.fill_diagonal(a,-1);near=a.max(1);matched.append({'median_within_query_NN':float(np.median(near)),'fraction_within_query_NN_ge_0.7':float(np.mean(near>=.7))})
save('test_size_matched_529_series.json',{'draws':30,'seed':20261026,'mean':{k:float(np.mean([x[k] for x in matched])) for k in matched[0]},'min_max':{k:[min(x[k] for x in matched),max(x[k] for x in matched)] for k in matched[0]},'purpose':'Query-size control only; no labels, fitting or new model selection.'})
# Released single-concentration coverage: exact IDs first; no inference of unperformed assays.
single_path=WORK/'artifacts/cyp-review/sources/cyp-challenge-single-concentration-TRAIN.csv';single=pd.read_csv(single_path);singleids=set(single.Molecule_Name);directids=set(train.Molecule_Name);no_single=directids-singleids;single_only=singleids-directids
pd.DataFrame({'Molecule_Name':sorted(no_single)}).to_csv(ROOT/'direct_ids_without_released_single.csv',index=False);pd.DataFrame({'Molecule_Name':sorted(single_only)}).to_csv(ROOT/'single_ids_without_direct.csv',index=False)
groups={'full_direct':np.arange(4905),'direct_with_single':np.flatnonzero(train.Molecule_Name.isin(singleids)),'direct_without_single':np.flatnonzero(~train.Molecule_Name.isin(singleids))}
for name in ['own750','briford529']:groups[name]=contexts[name][0];groups[name+'_train']=contexts[name][1]
labels=[];patterns=[];descriptors=[];composition=[]
for name,idx in groups.items():
 f=train.iloc[idx];mask=f[TARGETS].notna().to_numpy();pat=[''.join(str(int(x)) for x in row) for row in mask]
 composition.append({'group':name,'n':len(idx),'with_released_single':int(f.Molecule_Name.isin(singleids).sum()),'without_released_single':int((~f.Molecule_Name.isin(singleids)).sum()),'without_single_fraction':float((~f.Molecule_Name.isin(singleids)).mean()),'all4_labels':int(np.sum(mask.all(1))),'one_label_only':int(np.sum(mask.sum(1)==1))})
 for pattern,n in Counter(pat).items():patterns.append({'group':name,'observed_mask_1A2_2C9_2D6_3A4':pattern,'n':n,'fraction':n/len(idx)})
 for j,t in enumerate(TARGETS):
  z=f.loc[f[t].notna()];y=z[t].to_numpy();lo=z[t+'_conf_low'].to_numpy();hi=z[t+'_conf_high'].to_numpy();width=hi-lo
  if not len(y):
   labels.append({'group':name,'target':t.split('_')[0],'n_molecules':len(idx),'n_observed':0,'observed_fraction':0});continue
  den=np.maximum(lo-y.mean(),0)+np.maximum(y.mean()-hi,0)
  labels.append({'group':name,'target':t.split('_')[0],'n_molecules':len(idx),'n_observed':len(y),'observed_fraction':len(y)/len(idx),'mean_pIC50':np.mean(y),'median_pIC50':np.median(y),'sd_pIC50':np.std(y,ddof=1),'q10_pIC50':np.quantile(y,.1),'q90_pIC50':np.quantile(y,.9),'fraction_pIC50_lt4':np.mean(y<4),'fraction_pIC50_ge6':np.mean(y>=6),'median_CI_width':np.median(width),'q90_CI_width':np.quantile(width,.9),'mean_baseline_soft_error':den.mean(),'fraction_baseline_inside_CI':np.mean(den==0)})
 for k in ['MW','cLogP','TPSA','fraction_CSP3']:
  a=np.array([tf[i][k] for i in idx]);b=np.array([x[k] for x in bf]);descriptors.append({'group':name,'descriptor':k,'median':np.median(a),'q10':np.quantile(a,.1),'q90':np.quantile(a,.9),'blind_median':np.median(b),'W1_to_blind':wasserstein_distance(a,b)})
pd.DataFrame(labels).to_csv(ROOT/'observed_label_regimes.csv',index=False);pd.DataFrame(patterns).to_csv(ROOT/'label_missingness_patterns.csv',index=False);pd.DataFrame(composition).to_csv(ROOT/'released_assay_composition.csv',index=False);pd.DataFrame(descriptors).to_csv(ROOT/'descriptor_regimes.csv',index=False)
# All-structure native encoder exposure is distinct from primary-labeled support.
full=G/'model-audit/corrected-fullfit-native/stage/prepared/union18.csv';native_contexts={'blind750_full_native':(blind,full)}
for name in ['own750','briford529']:native_contexts[name+'_native']=(train.iloc[contexts[name][0]],G/'chemistry-audit/corrected-native-reference/stage/corrected'/name/'prepared/union18.csv')
native_stats=[]
for context,(queries,path) in native_contexts.items():
 frame=pd.read_csv(path);refs=[features(s)['fp'] for s in frame.smiles];best=[]
 for s in queries.SMILES:best.append(max(DataStructs.BulkTanimotoSimilarity(features(s)['fp'],refs)))
 a=np.array(best);native_stats.append({'context':context,'query_rows':len(queries),'encoder_training_structures':len(frame),'median_NN':float(np.median(a)),'mean_NN':float(a.mean()),'fraction_NN_ge_0.7':float(np.mean(a>=.7)),'fraction_Fingerprint_Tanimoto_1':float(np.mean(a==1)),'reference_note':'All native union encoder structures, not evidence of primary activity label support or exact molecular identity'})
pd.DataFrame(native_stats).to_csv(ROOT/'native_encoder_exposure_geometry.csv',index=False)
summary={'official_train_rows':4905,'blind_rows':750,'observed_primary_cells':int(observed.sum()),'possible_primary_cells':int(observed.size),'holdout_overlap_ids':len(set(cohorts['own750']['test_ids'])&set(cohorts['briford529']['test_ids'])),'single_unique_ids':len(singleids),'single_in_direct':len(singleids&directids),'direct_without_single':len(no_single),'single_only_ids':sorted(single_only),'briford_test_equals_direct_minus_single':set(cohorts['briford529']['test_ids'])==no_single,'briford_without_single':len(set(cohorts['briford529']['test_ids'])&no_single),'own_without_single':len(set(cohorts['own750']['test_ids'])&no_single),'fingerprints':'RDKit Cleanup+FragmentParent, Morgan radius2/2048 bits/chiralityFalse; same convention as prior frozen geometry audit; three recomputed cache rows matched<1e-7','similarity_cache_sha256':sha(OLD/'similarity_matrices.npz'),'single_source_sha256':sha(single_path),'no_hidden_labels_loaded':True,'no_models_fit':True,'no_external_calls':True,'limits':['Butina/scaffold/nearest-anchor groups are proxies, not organizer series IDs.','Missing released single-concentration rows do not prove the assay was never performed.','Blind target label availability/values/intervals remain unknown.','Fingerprint Tanimoto1 is not proof of chemical identity, especially without chirality.']}
save('geometry_manifest.json',summary);print(json.dumps(summary,indent=2))
