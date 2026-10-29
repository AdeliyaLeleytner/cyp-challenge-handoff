from pathlib import Path
import json,hashlib,sqlite3
import numpy as np,pandas as pd
from scipy.stats import spearmanr,kendalltau
from sklearn.metrics import r2_score
p=Path(__file__).parent;out=p/'results';c=json.load(open(p/'worktree/p9_tabicl_config.json'));m=json.load(open(c['files']['nested_manifest']['path']))['cohorts'];truth=pd.read_csv(c['files']['official']['path']).set_index('Molecule_Name');ep=['CYP1A2','CYP2C9','CYP2D6','CYP3A4'];T=[e+'_pIC50_direct_inhibition' for e in ep];point=pd.read_csv(out/'blend-metrics.csv');maxerr=0.;weightschecks=[];nativechecks=[]
def calc(y,v,lo,hi):
 den=abs(y.mean()-np.clip(y.mean(),lo,hi)).mean();return {'ST-RAE':float(abs(v-np.clip(v,lo,hi)).mean()/den),'MAE':float(abs(v-y).mean()),'R2':float(r2_score(y,v)),'Spearman':float(spearmanr(y,v).statistic),'Kendall':float(kendalltau(y,v).statistic),'RMSE':float(np.sqrt(np.mean((v-y)**2)))}
for name,spec in m.items():
 tr=spec['train_ids'];qu=spec['query_ids'];wr=json.load(open(out/f'{name}-weights.json'));N=pd.read_csv(spec['native_oof']['path']).set_index('Molecule_Name').loc[tr,ep].to_numpy();A=pd.read_csv(out/f'{name}-adme600-inner-OOF.csv').set_index('Molecule_Name').loc[tr,ep].to_numpy();J=pd.read_csv(out/f'{name}-atomjepa256-inner-OOF.csv').set_index('Molecule_Name').loc[tr,ep].to_numpy();P=np.stack([N,A,J],axis=2)
 for fold in spec['inner_folds']:
  for rep in ['adme600','atomjepa256']:
   z=np.load(out/f'{rep}-f{name}_inner{fold["fold"]}-preprocessing.npz');assert set(z['train_ids'])==set(fold['train_ids']) and set(z['test_ids'])==set(fold['val_ids']);assert not (set(z['train_ids'])&set(qu) or set(z['test_ids'])&set(qu))
 for j,e in enumerate(ep):
  valid=truth.loc[tr,T[j]].notna().to_numpy();y=truth.loc[tr,T[j]].to_numpy()[valid];lo=truth.loc[tr,T[j]+'_conf_low'].to_numpy()[valid];hi=truth.loc[tr,T[j]+'_conf_high'].to_numpy()[valid];pp=P[valid,j];loss={}
  for arm in ['incumbent','native_adme','three_experts']:
   w=np.array(wr['weights'][arm][j]);assert w.min()>=0 and abs(w.sum()-1)<1e-12;pred=pp@w;loss[arm]=abs(pred-np.clip(pred,lo,hi)).mean()
   if arm!='incumbent':assert abs(loss[arm]-wr['training_fit'][e][arm]['mean_CI_distance'])<1e-12
  assert loss['three_experts']<=loss['native_adme']+1e-8<=loss['incumbent']+2e-8
  d=pp[:,1]-pp[:,0];ok=abs(d)>1e-12;ends=np.r_[(lo[ok]-pp[ok,0])/d[ok],(hi[ok]-pp[ok,0])/d[ok]];weight=np.r_[abs(d[ok]),abs(d[ok])];order=np.argsort(ends);alpha=float(np.clip(ends[order][np.searchsorted(weight[order].cumsum(),weight.sum()/2)],0,1));pred=pp[:,0]+alpha*d;assert abs(abs(pred-np.clip(pred,lo,hi)).mean()-loss['native_adme'])<1e-8;weightschecks.append({'cohort':name,'target':e,'weighted_median_objective_parity':True,'simplex_and_training_objective_order':True})
  # Queries are used only after all training-objective checks.
 Q=np.stack([pd.read_csv(spec['native_query']['path']).set_index('Molecule_Name').loc[qu,T].to_numpy()]+[pd.read_csv(spec['p9_query'][x]['path']).set_index('Molecule_Name').loc[qu,ep].to_numpy() for x in ['adme600','atomjepa256']],axis=2)
 for arm in ['incumbent','native_adme','three_experts']:
  r=pd.read_csv(out/f'{name}-raw-{arm}.csv').set_index('Molecule_Name');assert r.index.tolist()==qu and r.SMILES.tolist()==truth.loc[qu,'SMILES'].tolist();w=np.array(wr['weights'][arm]);reconstructed=(Q*w[None,:,:]).sum(axis=2);assert np.allclose(reconstructed,r[ep],rtol=0,atol=1e-12)
  if arm=='incumbent':assert np.allclose(r[ep],Q[:,:,0],rtol=0,atol=1e-12);nativechecks.append(name)
  for lane in ['raw','fixed_original_served_diagnostic']:
   r=pd.read_csv(out/f'{name}-{lane}-{arm}.csv').set_index('Molecule_Name').loc[qu];values=[]
   for j,e in enumerate(ep):
    q=truth.loc[qu,T[j]].notna();y=truth.loc[qu,T[j]][q].to_numpy();v=r.loc[q,e].to_numpy();lo=truth.loc[qu,T[j]+'_conf_low'][q].to_numpy();hi=truth.loc[qu,T[j]+'_conf_high'][q].to_numpy();v=calc(y,v,lo,hi);values.append(v)
    for metric,value in v.items():
     expected=point[(point.cohort==name)&(point.lane==lane)&(point.arm==arm)&(point.endpoint==e)&(point.metric==metric)].value.item();maxerr=max(maxerr,abs(value-expected));assert abs(value-expected)<1e-11
   for metric in values[0]:
    value=np.mean([x[metric] for x in values]);expected=point[(point.cohort==name)&(point.lane==lane)&(point.arm==arm)&(point.endpoint=='macro')&(point.metric==metric)].value.item();maxerr=max(maxerr,abs(value-expected));assert abs(value-expected)<1e-11
con=sqlite3.connect('file:/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/orx.db?mode=ro',uri=True);status,source=con.execute('select status,commit_sha from runs where id=?',('f23c6d16-ebcb-47e4-aaf0-43feb78f69df',)).fetchone();assert status=='done';sup=json.load(open(out/'supervisor.json'));assert sup['returncode']==0 and sup['stop_reason'] is None;receipt={'status':'pass','run':'f23c6d16-ebcb-47e4-aaf0-43feb78f69df','source':source,'native_unchanged_cohorts':nativechecks,'actual_inner_PCA_membership_checked':20,'outer_query_absent_from_all_new_inner_contexts':True,'real_LP_weighted_median_parity_and_simplex_checks':weightschecks,'all5_plus_RMSE_raw_and_diagnostic_served_rescored':True,'max_metric_difference':maxerr,'supervisor':sup,'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(p/'VERIFICATION.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='real_LP_weighted_median_parity_and_simplex_checks'}))
