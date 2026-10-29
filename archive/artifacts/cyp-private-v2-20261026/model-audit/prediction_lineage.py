"""Private read-only source audit and unlabeled prediction drift; no model fitting."""
from pathlib import Path
import os,json,hashlib,shutil,sqlite3
import numpy as np,pandas as pd
from scipy.stats import pearsonr,spearmanr,kendalltau
os.umask(0o077)
ROOT=Path(__file__).resolve().parent;ROOT.chmod(0o700);FROZEN=ROOT/'frozen-predictions';FROZEN.mkdir(exist_ok=True)
WORK=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition');GOAL=WORK/'artifacts/goal-20261026'
OLD=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-briford-reproduction-20261024/remote/finalized');NEW=GOAL/'model-audit/corrected-fullfit-native/recovered-output/results';H6=GOAL/'final-locked-h6-output'
TARGETS=[f'{c}_pIC50_direct_inhibition' for c in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']];MEMBERS=['union18','mtaux8','2d6isoform6','2d6single']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rec(p):p=Path(p).resolve();return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def preserve(src,name):
 p=FROZEN/name
 if p.exists():assert sha(p)==sha(src)
 else:shutil.copy2(src,p);p.chmod(0o600)
 return rec(p)
manifest=json.loads((GOAL/'model-audit/official-snapshot-18460/manifest.json').read_text());train=pd.read_csv(manifest['files']['official_train']['path']);blind=pd.read_csv(manifest['files']['official_test']['path']);assert len(train)==4905 and len(blind)==750
paths={'incumbent':{'raw':OLD/'cyp-ensemble_activity_submission_native_raw.csv','placed':OLD/'cyp-ensemble_activity_submission_native_raw_native_strae.csv'},'corrected_native':{'raw':NEW/'cyp-ensemble_activity_submission_native_raw.csv','placed':NEW/'cyp-ensemble_activity_submission_native_raw_native_strae.csv'},'H6':{'raw':H6/'final-test-raw.csv','placed':H6/'final-test-placed.csv'}}
expected={'incumbent':'349165ecf50906e43a27f12dee97891a92cda59e798db614ef27a7c920c38a37','corrected_native':'95897f449e10899abc24c4c9c432a72b29e9a890b3208112e97cd9aa3006eaa8','H6':'91fa8bf0870f68071b04183166b1507c20001d04f3ae3fb5f4d055618fff98c7'}
pred={};lineage={'predictions':{},'official_train':rec(manifest['files']['official_train']['path']),'official_test':rec(manifest['files']['official_test']['path']),'native_components':{},'no_fits':True,'no_hidden_labels_loaded':True,'no_external_calls':True}
for model,lanes in paths.items():
 assert sha(lanes['placed'])==expected[model];lineage['predictions'][model]={}
 for lane,p in lanes.items():
  df=pd.read_csv(p);assert df.Molecule_Name.is_unique and set(df.Molecule_Name)==set(blind.Molecule_Name);df=df.set_index('Molecule_Name').loc[blind.Molecule_Name];assert df.SMILES.tolist()==blind.SMILES.tolist();a=df[TARGETS].to_numpy();assert np.isfinite(a).all();pred[(model,lane)]=a
  lineage['predictions'][model][lane]={'original':rec(p),'private_frozen_copy':preserve(p,model+'_'+lane+'.csv')}
# Preserve the exact incumbent model artifacts, not just a recipe that may retrain differently.
archive=ROOT/'incumbent-artifact-copy';archive.mkdir(exist_ok=True)
for model,root in [('incumbent',OLD),('corrected_native',NEW)]:
 detail={}
 for member in MEMBERS:
  folds=[]
  for k in range(5):
   d=root/member/f'fold{k}';done=json.loads((d/'complete.json').read_text());assert done['status']=='complete';files={}
   for rel,h in done['files'].items():
    p=d/rel;assert sha(p)==h,(model,member,k,rel);files[rel]=rec(p)
    if model=='incumbent':
     dst=archive/member/f'fold{k}'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
     if not dst.exists():shutil.copy2(p,dst);dst.chmod(0o600)
     assert sha(dst)==h
   if model=='incumbent':
    dst=archive/member/f'fold{k}'/'complete.json';shutil.copy2(d/'complete.json',dst);dst.chmod(0o600)
   folds.append({'fold':k,'complete':rec(d/'complete.json'),'files':files})
  detail[member]={'folds':folds,'oof':rec(root/member/'oof.csv'),'query':rec(root/member/'test_raw.csv')}
  if model=='incumbent':
   for fn in ['oof.csv','test_raw.csv']:
    dst=archive/member/fn;shutil.copy2(root/member/fn,dst);dst.chmod(0o600)
 lineage['native_components'][model]=detail
lineage['incumbent_exact_artifact_copy']=str(archive)
comparison=[]
for member in MEMBERS:
 for k in range(5):
  a=lineage['native_components']['incumbent'][member]['folds'][k]['files'];b=lineage['native_components']['corrected_native'][member]['folds'][k]['files'];ka=next(x for x in a if x.endswith('.ckpt'));kb=next(x for x in b if x.endswith('.ckpt'));comparison.append({'member':member,'fold':k,'same_checkpoint':a[ka]['sha256']==b[kb]['sha256'],'same_oof':a['oof.csv']['sha256']==b['oof.csv']['sha256'],'same_query':a['test.csv']['sha256']==b['test.csv']['sha256']})
pd.DataFrame(comparison).to_csv(ROOT/'checkpoint_reuse.csv',index=False)
lineage['H6_heads']={t:{n:rec(H6/'final-models'/t/n) for n in ['head.joblib','receipt.json','feature-order.json','query-predictions.npy','booster.txt']} for t in TARGETS}
lineage['evidence']={name:rec(p) for name,p in {'original_final_complete':OLD/'final_complete.json','original_placement':OLD/'placement.json','corrected_certificate':GOAL/'model-audit/corrected-fullfit-native/FULLFIT_REFERENCE_CERTIFICATE.json','corrected_purge':GOAL/'model-audit/corrected-fullfit-native/stage/purge-and-reuse-manifest.json','H6_complete':H6/'complete.json','H6_selection':H6/'full-data-selection.json','H6_placement':H6/'final-placement.json','H6_actual_run':GOAL/'model-audit/submission-transport/final-run.json','published_score_receipt':GOAL/'model-audit/submission-transport/processed-result.json'}.items()}
c=sqlite3.connect('file:/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/orx.db?mode=ro',uri=True);c.row_factory=sqlite3.Row
lineage['orx_runs']=[dict(r) for r in c.execute("select id,experiment_id,status,command,commit_sha,created_at,ended_at from runs where experiment_id in (?,?,?)",('3218eedb-29ef-4af5-8c82-c166279d0bf3','8421e31b-790d-4c13-9f29-d3b9bdc1ee59','b64f3a0f-3bb5-4e17-95c1-3fff9342a6a9'))]
lineage['original_training_source']='d4c1a31c2952f8d933ce035a1cab04417f46cb76';lineage['original_finalized_serving_source']='38fe110e5a8d17a7bfb48ac78fe12e425da8deeb'
placements={m:json.loads((root/'placement.json').read_text()) for m,root in [('incumbent',OLD),('corrected_native',NEW)]};placements['H6']=json.loads((H6/'final-placement.json').read_text());cal={};stats=[]
for m in paths:
 cal[m]={}
 for j,t in enumerate(TARGETS):
  iso=t.split('_')[0];r=pred[(m,'raw')][:,j];p=pred[(m,'placed')][:,j]
  cc=placements[m]['per_cyp'][t] if m=='H6' else placements[m]['calibration'][iso];cal[m][t]={'mean':float(r.mean()),'offset':cc['offset'],'scale':cc['scale']};expected_values=np.maximum(r.mean()+cc['scale']*(r-r.mean())+cc['offset'],1.);assert np.max(np.abs(p-expected_values))<1e-12
  rho=cc['oof_to_blind_pearson'] if m=='H6' else placements[m]['estimated_blind_pearson'][iso]
  stats.append({'model':m,'target':iso,'raw_mean':r.mean(),'raw_sd':r.std(ddof=1),'placed_mean':p.mean(),'placed_sd':p.std(ddof=1),'placement_scale':cc['scale'],'placement_offset':cc['offset'],'estimated_blind_pearson':rho,'floor_count':int(np.sum(p==1)),'raw_below4':np.mean(r<4),'placed_below4':np.mean(p<4)})
pd.DataFrame(stats).to_csv(ROOT/'prediction_and_placement_statistics.csv',index=False)
def drift(a,b):
 d=b-a;absolute=np.abs(d);return {'mean_signed_delta':float(d.mean()),'mean_abs_delta':float(absolute.mean()),'RMSE_delta':float(np.sqrt((d*d).mean())),'median_abs_delta':float(np.median(absolute)),'q90_abs_delta':float(np.quantile(absolute,.9)),'max_abs_delta':float(absolute.max()),'Pearson_between_predictions':float(pearsonr(a,b).statistic),'Spearman_between_predictions':float(spearmanr(a,b).statistic),'Kendall_between_predictions':float(kendalltau(a,b).statistic),'fraction_over_2fold_potency_change':float(np.mean(absolute>np.log10(2))),'fraction_over_10fold_potency_change':float(np.mean(absolute>1)),'fraction_crossing_pIC50_4':float(np.mean((a<4)!=(b<4)))}
changes=[];decomposition=[];molecule=[]
for start,end in [('incumbent','corrected_native'),('corrected_native','H6'),('incumbent','H6')]:
 for j,t in enumerate(TARGETS):
  iso=t.split('_')[0]
  for lane in ['raw','placed']:
   a=pred[(start,lane)][:,j];b=pred[(end,lane)][:,j];changes.append({'from':start,'to':end,'lane':lane,'target':iso,**drift(a,b)})
   for i in range(len(blind)):molecule.append({'transition':start+'->'+end,'lane':lane,'target':iso,'Molecule_Name':blind.Molecule_Name.iloc[i],'before':a[i],'after':b[i],'delta':b[i]-a[i],'abs_delta':abs(b[i]-a[i])})
  c0=cal[start][t];counter=np.maximum(c0['mean']+c0['scale']*(pred[(end,'raw')][:,j]-c0['mean'])+c0['offset'],1.)
  first=counter-pred[(start,'placed')][:,j];second=pred[(end,'placed')][:,j]-counter;total=pred[(end,'placed')][:,j]-pred[(start,'placed')][:,j];assert np.max(np.abs(first+second-total))<1e-12
  decomposition.append({'from':start,'to':end,'target':iso,'raw_change_under_frozen_old_map_mean':first.mean(),'raw_change_under_frozen_old_map_MAD':np.abs(first).mean(),'map_change_at_new_raw_mean':second.mean(),'map_change_at_new_raw_MAD':np.abs(second).mean(),'total_mean':total.mean(),'total_MAD':np.abs(total).mean(),'limitation':'Path-specific arithmetic decomposition, not error or causal attribution; absolute components need not add.'})
pd.DataFrame(changes).to_csv(ROOT/'unlabeled_prediction_drift.csv',index=False);pd.DataFrame(decomposition).to_csv(ROOT/'placement_path_decomposition.csv',index=False);pd.DataFrame(molecule).to_csv(ROOT/'per_molecule_prediction_drift.csv',index=False)
# Component drift explains exactly which saved experts changed, without labels.
component=[]
for member in MEMBERS:
 a=pd.read_csv(OLD/member/'test_raw.csv').set_index('molecule_name').loc[blind.Molecule_Name];b=pd.read_csv(NEW/member/'test_raw.csv').set_index('molecule_name').loc[blind.Molecule_Name]
 for t in TARGETS:
  k=t.lower()+'_pred'
  if k in a:component.append({'member':member,'target':t.split('_')[0],**drift(a[k].to_numpy(),b[k].to_numpy())})
pd.DataFrame(component).to_csv(ROOT/'native_component_drift.csv',index=False)
# Inspect exactly which of32 train-side removals carried official primary labels.
proof=json.loads((GOAL/'model-audit/corrected-fullfit-native/stage/purge-and-reuse-manifest.json').read_text());removed=[]
for x in proof['inner_train_removed_rows']:
 frame=pd.read_csv(GOAL/'model-audit/corrected-fullfit-native/stage/prepared'/(x['member']+'.csv'));r=frame.iloc[x['row_index']];primary=[t for t in TARGETS if t.lower() in r.index and pd.notna(r[t.lower()])];removed.append({**x,'official_primary_labels_present':','.join(primary),'n_primary_labels':len(primary)})
pd.DataFrame(removed).to_csv(ROOT/'strict_inner_exclusion_label_support.csv',index=False)
score=json.loads((GOAL/'model-audit/submission-transport/processed-result.json').read_text());lineage['observed_live_scores']={'incumbent':{k:v for k,v in score['previous_public_entry'].items() if k.startswith('MA-') or k=='Rank'},'H6':{k:v for k,v in score['public_entry'].items() if k.startswith('MA-') or k=='Rank'},'corrected_native_alone':'not submitted/scored; outcome unknown'}
lineage['files']= {p.name:rec(p) for p in ROOT.glob('*.csv')};save(ROOT/'lineage_manifest.json',lineage)
print(json.dumps({'preserved_csvs':6,'incumbent_checkpoints_preserved':20,'same_native_checkpoints':sum(x['same_checkpoint'] for x in comparison),'changed_native_checkpoints':sum(not x['same_checkpoint'] for x in comparison),'strict_inner_removal_entries':len(removed),'entries_with_primary_labels':sum(x['n_primary_labels']>0 for x in removed),'drift_rows':len(changes),'no_hidden_labels_or_fits':True},indent=2))
