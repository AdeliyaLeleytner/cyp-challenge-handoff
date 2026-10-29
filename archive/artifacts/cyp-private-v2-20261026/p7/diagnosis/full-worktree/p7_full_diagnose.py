from p7_diagnose import *
from scipy.stats import spearmanr,kendalltau,pearsonr
from sklearn.metrics import r2_score
EP=['CYP1A2','CYP2C9','CYP2D6','CYP3A4']
def metrics(y,p,lo,hi):
 rows=[]
 for j,e in enumerate(EP):
  m=np.isfinite(y[:,j]);a=y[m,j];b=p[m,j];l=lo[m,j];h=hi[m,j];assert np.isfinite(l).all() and np.isfinite(h).all();err=b-a;den=(np.maximum(l-a.mean(),0)+np.maximum(a.mean()-h,0)).sum();assert den>0
  rows.append({'endpoint':e,'n':int(m.sum()),'ST-RAE':float((np.maximum(l-b,0)+np.maximum(b-h,0)).sum()/den),'MAE':float(np.abs(err).mean()),'R2':float(r2_score(a,b)),'Spearman':float(spearmanr(a,b).statistic),'Kendall':float(kendalltau(a,b).statistic),'Pearson':float(pearsonr(a,b).statistic),'RMSE':float(np.sqrt((err**2).mean())),'bias':float(err.mean()),'prediction_SD':float(b.std()),'truth_SD':float(a.std())})
 macro={'endpoint':'macro','n':sum(x['n'] for x in rows)};macro.update({k:float(np.mean([x[k] for x in rows])) for k in rows[0] if k not in ['endpoint','n']});return rows+[macro]
def main():
 cfg=json.loads(Path('p7full_config.json').read_text());assert cfg['stage']=='full' and cfg['auxiliary_absolute_training_SD_bound']==1e-5;out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4);torch.set_float32_matmul_precision('highest');start=time.time()
 for p,h in cfg['input_hashes'].items():assert sha(p)==h,p
 df=pd.read_csv(cfg['table'],float_precision='round_trip');manifest=json.loads(Path(cfg['folds']).read_text());targets=manifest['targets'];raw=np.load(cfg['feature_matrix']);blocks=json.loads(Path(cfg['blocks']).read_text())['blocks'];rows=pd.read_csv(cfg['feature_rows']);assert rows.molecule_name.tolist()==df.molecule_name.tolist() and rows.request_id.tolist()==df.request_id.tolist()
 Y=df[targets[:4]].to_numpy(float);LO=df[[f'low_{j}' for j in range(4)]].to_numpy(float);HI=df[[f'high_{j}' for j in range(4)]].to_numpy(float);observed=np.isfinite(Y).any(1);records=[];parity=[];meta=[];components=[];all_frames=[]
 saved_oof(cfg,df,manifest['folds'],targets,out)
 for fold,f in enumerate(manifest['folds']):
  roles={role:[i for i in f[role] if observed[i]] for role in ['train','stop','test']};ix=[i for role in roles for i in roles[role]];rolelist=[role for role in roles for _ in roles[role]];assert len(set(ix))==len(ix)
  for cell in ['zero','fusion']:
   model,ini,metadata=load_model(cfg,cell,fold);X=features(cfg,cell,fold,raw);variants=['baseline'] if cell=='zero' else cfg['fusion_interventions'];pred,timing,comp=predict(model,df,ix,X,variants,blocks);meta.append({**metadata,'timing':timing})
   testpos=np.array([i for i,r in enumerate(rolelist) if r=='test']);testids=df.molecule_name.iloc[np.array(ix)[testpos]].tolist();saved=pd.read_csv(Path(cfg['results'])/f'{cell}_f{fold}'/'test_raw.csv',float_precision='round_trip').set_index('molecule_name').loc[testids,targets].to_numpy();actual=pred['baseline'][testpos];err=np.abs(actual-saved);sd=np.array(ini['scaler_scale'])[:18];primary=np.isclose(actual[:,:4],saved[:,:4],atol=cfg['atol'],rtol=cfg['rtol']);aux=err[:,4:]/sd[4:]<=cfg['auxiliary_absolute_training_SD_bound']
   gate={'fold':fold,'cell':cell,'n_test':len(testids),'primary_original_gate_pass':bool(primary.all()),'auxiliary_unit_gate_pass':bool(aux.all()),'max_primary_raw_error':float(err[:,:4].max()),'max_auxiliary_error_in_training_SD':float((err[:,4:]/sd[4:]).max()),'original_all18_raw_gate_pass':bool(np.isclose(actual,saved,atol=cfg['atol'],rtol=cfg['rtol']).all())};parity.append(gate);save(out/'parity-progress.json',parity);assert primary.all() and aux.all(),gate
   cf=pd.DataFrame(comp,columns=['graph_l2','descriptor_l2','graph_firstlinear_contribution_l2','descriptor_firstlinear_contribution_l2']);cf['fold']=fold;cf['cell']=cell;cf['role']=rolelist;cf['molecule_name']=df.molecule_name.iloc[ix].tolist();components.append(cf)
   for variant,p in pred.items():
    table=pd.DataFrame(p,columns=targets);table['fold']=fold;table['cell']=cell;table['intervention']=variant;table['role']=rolelist;table['molecule_name']=df.molecule_name.iloc[ix].tolist();table['row_index']=ix;table.to_csv(out/f'{cell}_f{fold}_{variant}.csv',index=False,float_format='%.17g');all_frames.append(table[['fold','cell','intervention','role','molecule_name','row_index']+targets[:4]])
    for role in roles:
     pos=np.array([i for i,r in enumerate(rolelist) if r==role]);src=np.array(ix)[pos]
     for r in metrics(Y[src],p[pos,:4],LO[src],HI[src]):records.append({'fold':fold,'cell':cell,'intervention':variant,'role':role,**r})
   print(json.dumps({'event':'checkpoint_diagnostic_complete','fold':fold,'cell':cell,'rows':len(ix),'timing':timing,'parity':gate}),flush=True);del model;gc.collect()
 pd.DataFrame(records).to_csv(out/'metrics-byfold.csv',index=False);pd.concat(components).to_csv(out/'branch-contributions.csv',index=False);allp=pd.concat(all_frames,ignore_index=True);pooled=[]
 for (cell,variant,role),g in allp.groupby(['cell','intervention','role']):
  src=g.row_index.to_numpy(int);v=g[targets[:4]].to_numpy(float)
  if role=='test':assert g.molecule_name.is_unique and len(g)==4905
  for r in metrics(Y[src],v,LO[src],HI[src]):pooled.append({'cell':cell,'intervention':variant,'role':role,'unique_molecules':int(g.molecule_name.nunique()),'evaluated_occurrences':len(g),'training_and_stopping_occurrences_repeat_across_models':role!='test',**r})
 pd.DataFrame(pooled).to_csv(out/'metrics-pooled.csv',index=False);save(out/'checkpoint-metadata.json',meta);receipt={'status':'complete','seconds':time.time()-start,'model_checkpoints':10,'fits':0,'optimizer_steps':0,'same_IDs_and_masks_per_arm':True,'original_all18_raw_gate_failure_preserved':True,'primary_tolerance':{'atol':cfg['atol'],'rtol':cfg['rtol']},'auxiliary_absolute_training_SD_bound':cfg['auxiliary_absolute_training_SD_bound'],'all_primary_and_unit_aware_aux_gates_pass':True,'input_shift_caveat':'Mean-zero intervention probes frozen dependence, not causal proof or a retrained repair','overfitting_not_assumed':True,'source_sha256':sha(__file__),'config_sha256':sha('p7full_config.json'),'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()}};save(out/'complete.json',receipt);print(json.dumps({'event':'final_summary','receipt':receipt,'pooled_macro':[x for x in pooled if x['endpoint']=='macro']}),flush=True)
if __name__=='__main__':main()
