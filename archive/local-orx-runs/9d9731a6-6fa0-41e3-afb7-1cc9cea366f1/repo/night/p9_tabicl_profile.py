import json,sys,time,hashlib,importlib.metadata
from pathlib import Path
import numpy as np,pandas as pd,torch,psutil
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from scipy.stats import spearmanr,kendalltau
from tabicl import TabICLRegressor
c=json.loads(Path(sys.argv[1]).read_text());assert importlib.metadata.version('tabicl')=='2.2.0' and importlib.metadata.version('einops')=='0.8.2' and torch.__version__.startswith('2.8.');out=Path(c['output']);torch.set_num_threads(c['threads']);torch.manual_seed(c['seed']);np.random.seed(c['seed']);start=time.monotonic()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for k,r in {**c['files'],**{k:c[k] for k in ['bank_complete','bank_rows','bank_features','bank_audit']}}.items():assert r and sha(r['path'])==r['sha256'],k
audit=json.load(open(c['bank_audit']['path']));assert audit['status']=='complete_pass' and audit['persisted_coordinate_rows']==5655 and not audit['flagged'];bankrec=json.load(open(c['bank_complete']['path']));assert bankrec['source_sha256']==c['bank_expected_worker_sha256'] and bankrec['config_sha256']==c['files']['bank_config']['sha256'];assert bankrec['status']=='complete' and bankrec['requested']==5655 and bankrec['successful']==5655 and bankrec['failed']==0
rows=pd.read_csv(c['bank_rows']['path']);bank=np.load(c['bank_features']['path']);assert bank.shape==(5655,256) and np.isfinite(bank).all() and rows.Molecule_Name.is_unique
orig=pd.read_csv(c['files']['official']['path']);ad=pd.read_csv(c['files']['adme_rows']['path']);adbank=np.load(c['files']['adme']['path']);assert adbank.shape==(4905,600) and np.isfinite(adbank).all();assert ad.Molecule_Name.tolist()==orig.Molecule_Name.tolist() and ad.SMILES.tolist()==orig.SMILES.tolist();lookup=rows.set_index('Molecule_Name');assert lookup.loc[orig.Molecule_Name,'SMILES'].tolist()==orig.SMILES.tolist();bank_ix=pd.Series(np.arange(len(rows)),index=rows.Molecule_Name).loc[orig.Molecule_Name].to_numpy();features={'adme600':adbank,'atomjepa256':bank[bank_ix]}
df=pd.read_csv(c['files']['table']['path']);folds=json.load(open(c['files']['folds']['path']));assert sha(c['files']['table']['path'])==folds['data_sha256'];targets=folds['targets'][:4];indices=df.reset_index().set_index('molecule_name').loc[orig.Molecule_Name,'index'].to_numpy(int);Y=df.loc[indices,targets].to_numpy(float);assert np.allclose(Y,orig[[x.split('_')[0].upper()+'_pIC50_direct_inhibition' for x in targets]],atol=1e-12,rtol=0,equal_nan=True)
Lo=df.loc[indices,[f'low_{j}' for j in range(4)]].to_numpy(float);Hi=df.loc[indices,[f'high_{j}' for j in range(4)]].to_numpy(float);assert np.isfinite(Lo[np.isfinite(Y)]).all() and np.isfinite(Hi[np.isfinite(Y)]).all() and (Lo[np.isfinite(Y)]<=Hi[np.isfinite(Y)]).all();results=[]
jobs=[]
for k in c['folds']:
 f=folds['folds'][k];train=np.isin(indices,f['train']);test=np.isin(indices,f['test']);stop=np.isin(indices,f['stop']);assert (train.astype(int)+test+stop<=1).all();jobs.append((str(k),train,test))
if c.get('outer_cohorts'):
 oc=json.load(open(c['files']['outer_manifest']['path']))['cohorts']
 for name in c['outer_cohorts']:
  spec=oc[name];train=orig.Molecule_Name.isin(spec['train_ids']).to_numpy();test=orig.Molecule_Name.isin(spec['test_ids']).to_numpy();assert train.sum()==len(spec['train_ids']) and test.sum()==len(spec['test_ids']);jobs.append((name,train,test))
for k,train,test in jobs:
 assert not (train&test).any()
 for name,X in features.items():
  t=time.monotonic();scaler=StandardScaler().fit(X[train]);pca=PCA(n_components=c['pca'],svd_solver='full',whiten=False).fit(scaler.transform(X[train]));tr=pca.transform(scaler.transform(X[train])).astype(np.float32);te=pca.transform(scaler.transform(X[test])).astype(np.float32);prep_seconds=time.monotonic()-t;assert np.isfinite(tr).all() and np.isfinite(te).all();np.savez_compressed(out/f'{name}-f{k}-preprocessing.npz',mean=scaler.mean_,scale=scaler.scale_,pca_mean=pca.mean_,components=pca.components_,train_ids=orig.Molecule_Name[train].to_numpy(str),test_ids=orig.Molecule_Name[test].to_numpy(str))
  for j in c['targets']:
   t=time.monotonic();observed=np.isfinite(Y[train,j]);params=dict(n_estimators=2,norm_methods=['none','power'],feat_shuffle_method='latin',outlier_threshold=4.,batch_size=2,kv_cache=False,model_path=c['files']['tabicl_weight']['path'],allow_auto_download=False,checkpoint_version='tabicl-regressor-v2-20260212.ckpt',device='cpu',use_amp=False,use_fa3=False,offload_mode=False,random_state=c['seed'],n_jobs=1,verbose=False)
   model=TabICLRegressor(**params);model.fit(tr[observed],Y[train,j][observed]);fit_seconds=time.monotonic()-t;t=time.monotonic();pred=model.predict(te);predict_seconds=time.monotonic()-t;assert pred.shape==(test.sum(),) and np.isfinite(pred).all();q=np.isfinite(Y[test,j]);y=Y[test,j][q];v=pred[q];lo=Lo[test,j][q];hi=Hi[test,j][q];distance=np.maximum(lo-v,0)+np.maximum(v-hi,0);den=np.mean(np.maximum(lo-y.mean(),0)+np.maximum(y.mean()-hi,0));scores={'ST-RAE':float(distance.mean()/den),'MAE':float(abs(v-y).mean()),'R2':float(1-np.mean((v-y)**2)/np.var(y)),'Spearman':float(spearmanr(v,y).statistic),'Kendall':float(kendalltau(v,y).statistic),'RMSE':float(np.sqrt(np.mean((v-y)**2)))};output=pd.DataFrame({'molecule_name':orig.Molecule_Name[test].to_numpy(),'smiles':orig.SMILES[test].to_numpy(),'fold':k,'target':targets[j],'prediction':pred});csv=out/f'{name}-f{k}-target{j}.csv';output.to_csv(csv,index=False,float_format='%.17g');r={'representation':name,'fold':k,'target':targets[j],'train_feature_rows':int(train.sum()),'train_observed_labels':int(observed.sum()),'test_rows':int(test.sum()),'test_observed_labels':int(q.sum()),'preprocessing_seconds':prep_seconds,'fit_seconds':fit_seconds,'predict_seconds':predict_seconds,'rss_bytes':psutil.Process().memory_info().rss,'metrics':scores,'prediction_sha256':sha(csv),'params':params,'feature_count':96};results.append(r);(out/f'{name}-f{k}-target{j}.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);del model
assert len(results)==c['expected_calls'];total=time.monotonic()-start;call=max(x['fit_seconds']+x['predict_seconds']+x['preprocessing_seconds'] for x in results)
profile_tokens=max(x['train_observed_labels']+x['test_rows'] for x in results);projection_factors=[]
for fold in folds['folds']:
 trmask=np.isin(indices,fold['train']);temask=np.isin(indices,fold['test'])
 for j in range(4):projection_factors.extend([max(1.,((np.isfinite(Y[trmask,j]).sum()+temask.sum())/profile_tokens)**2)]*2)
outer=json.load(open(c['files']['outer_manifest']['path']))['cohorts']
for spec in outer.values():
 trmask=orig.Molecule_Name.isin(spec['train_ids']).to_numpy()
 for j in range(4):projection_factors.extend([max(1.,((np.isfinite(Y[trmask,j]).sum()+len(spec['test_ids']))/profile_tokens)**2)]*2)
assert len(projection_factors)==56;projection=call*sum(projection_factors)
receipt={'status':'complete','calls':len(results),'runtime_seconds':total,'conservative_56call_projection_seconds':projection,'projection_not_measured_full_runtime':True,'projection_method':'worstpairedprofilecall times56 sequence-length-squared factors flooredat1; countsactualobservedcontexts+queries','projection_sum_factors':sum(projection_factors),'profile_worst_call_seconds':call,'results':results,'packages':{x:importlib.metadata.version(x) for x in ['tabicl','einops','torch','numpy','scikit-learn']},'PCA':96,'PCA_fit_only_actual_train':True,'only_primary_labels_used':True,'no_model_finetuning':True,'no_calibration_or_ensemble':True,'source_sha256':sha(__file__),'config_sha256':sha(sys.argv[1])};(out/'COMPLETE.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='results'}),flush=True)

if c.get("aggregate",False):
 from p9_tabicl_aggregate import aggregate
 aggregate(c)
