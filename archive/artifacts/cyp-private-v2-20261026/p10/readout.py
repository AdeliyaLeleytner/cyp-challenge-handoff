"""P10 selected-procedure readout with immutable parent references; no fits."""
import argparse,json,hashlib,importlib.util
from pathlib import Path
import numpy as np,pandas as pd
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
sp=importlib.util.spec_from_file_location('base',Path(__file__).with_name('readout_base.py'));base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
EP=base.EP;MET=base.MET;score=base.score

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--bootstrap',type=int,default=1000);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);manifest=json.loads((a.stage/'manifest.json').read_text());cfg=json.loads((a.stage/'common/manifest.json').read_text());df=pd.read_csv(a.stage/'common/table.csv',float_precision='round_trip');assert sha(a.stage/'common/table.csv')==cfg['data_sha256'];targets=cfg['targets'];Y=df[targets[:4]].to_numpy(float);L=df[[f'low_{j}' for j in range(4)]].to_numpy(float);H=df[[f'high_{j}' for j in range(4)]].to_numpy(float);official=np.isfinite(Y).any(1);assert official.sum()==4905;observed=np.isfinite(Y);assert np.isfinite(L[observed]).all() and np.isfinite(H[observed]).all() and (L[observed]<=H[observed]).all();fold_of=np.full(len(df),-1)
 for f,x in enumerate(cfg['folds']):fold_of[x['test']]=f
 cells=['zero__all18','zero__primary4','repaired__all18','repaired__primary4'];allpred={};selections=[];init={};batch_rng={};perfold=[]
 for parent in ['zero','repaired']:
  out=np.full((len(df),4),np.nan)
  for f,x in enumerate(cfg['folds']):
   path=a.stage/'parents'/f'{parent}_f{f}';record=next(r for r in manifest['parents'] if r['parent']==parent and r['fold']==f);assert sha(path/'test_raw.csv')==record['files']['test_raw.csv'];v=pd.read_csv(path/'test_raw.csv',float_precision='round_trip');assert v.molecule_name.tolist()==df.molecule_name.iloc[x['test']].tolist();out[x['test']]=v[targets[:4]].to_numpy()
  assert np.isfinite(out).all();allpred[parent+'__parent']=out[official]
 for cell in cells:
  parent,objective=cell.split('__');out=np.full((len(df),4),np.nan);init[cell]=[];batch_rng[cell]=[]
  for f,x in enumerate(cfg['folds']):
   path=a.results/f'{cell}_f{f}';d=json.loads((path/'complete.json').read_text());z=json.loads((path/'initial.json').read_text());e=json.loads((path/'epoch0.json').read_text());record=next(r for r in manifest['parents'] if r['parent']==parent and r['fold']==f)
   assert d['status']=='complete' and d['parent']==parent and d['objective']==objective and d['test_not_selection'] and not d['selection_uses_test_outcomes'];assert sha(path/'initial.json')==d['initial_sha256'] and sha(path/'test_raw.csv')==d['prediction_sha256'];assert z['prediction_tensor_sha256']==record['prediction_tensor_sha256']==e['parent_prediction_hash'];assert e['no_BN_or_predictive_state_mutation'] and z['epoch0_eligible'] and not z['skip_no_primary_batches']
   assert d['parent_selected']==(not(d['best_continuation_stop_score']<d['epoch0_stop_score']));assert (d['best_epoch']==0)==d['parent_selected'];assert d['global_optimizer_steps']==d['training_batches'];assert d['epochs_run']<=50
   v=pd.read_csv(path/'test_raw.csv',float_precision='round_trip');assert list(v.columns)==['molecule_name']+targets and v.molecule_name.tolist()==df.molecule_name.iloc[x['test']].tolist();pred=v[targets].to_numpy();assert np.isfinite(pred).all()
   if d['parent_selected']:
    expected=pd.read_csv(a.stage/'parents'/f'{parent}_f{f}'/'test_raw.csv',float_precision='round_trip');assert np.array_equal(pred,expected[targets].to_numpy())
   for role in ['epoch0','selected']:
    fit=pd.read_csv(path/f'{role}-primary-predictions.csv',float_precision='round_trip')
    for part in ['train','stop']:
     idx=[i for i in x[part] if official[i]];assert fit[fit.role==part].molecule_name.tolist()==df.molecule_name.iloc[idx].tolist()
   log=(a.results/f'{cell}_f{f}.log').read_text().splitlines();events=[json.loads(line) for line in log if line.startswith('{')];opt=[q for q in events if q.get('event')=='optimizer_reset_verified'];assert len(opt)==1 and opt[0]['state_entries']==0 and opt[0]['scheduler_count']==0 and opt[0]['lr']==1e-4;epochs=[q for q in events if q.get('event')=='epoch_timing'];assert all(q['lr']==[1e-4] for q in epochs);rng={q['continuation_epoch']:q['CPU_RNG_sha256'] for q in events if q.get('event')=='epoch_batch_rng'};batch_rng[cell].append(rng);init[cell].append(z)
   sc=score(Y[x['test']],pred[:,:4],L[x['test']],H[x['test']]);assert abs(sc[-1,0]-d['raw_strae'])<1e-10
   for j in range(4):
    for k,m in enumerate(MET):
     old=d['raw_per_target_metrics'][j][m];tol=8*np.finfo(np.float32).eps*max(1,abs(old)) if m=='prediction_SD' else 1e-10;assert abs(sc[j,k]-old)<tol,(cell,f,m)
   out[x['test']]=pred[:,:4];selections.append({k:d[k] for k in ['cell','parent','objective','fold','parent_selected','best_epoch','epoch0_stop_score','best_continuation_stop_score','selected_stop_score','epochs_run','global_optimizer_steps','training_batches','no_primary_batches']});perfold.append({'cell':cell,'fold':f,'metrics':sc.tolist()})
  assert np.isfinite(out).all();allpred[cell]=out[official]
 for parent in ['zero','repaired']:
  A=parent+'__all18';B=parent+'__primary4'
  for f in range(5):
   assert init[A][f]['prediction_tensor_sha256']==init[B][f]['prediction_tensor_sha256'];assert init[A][f]['feature_transform_sha256']==init[B][f]['feature_transform_sha256'];common=set(batch_rng[A][f])&set(batch_rng[B][f]);assert common and all(batch_rng[A][f][k]==batch_rng[B][f][k] for k in common)
 yy,ll,hh=Y[official],L[official],H[official];rows=df[official].copy();folds=fold_of[official];groups=[Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(Chem.MolFromSmiles(s))) for s in rows.smiles];strata=[]
 for f in range(5):
  idx=np.where(folds==f)[0];g=np.array(groups,dtype=object)[idx];strata.append([idx[g==v] for v in sorted(set(g))])
 point={c:score(yy,v,ll,hh) for c,v in allpred.items()};draws={c:[] for c in allpred};gen=np.random.default_rng(20261026)
 for b in range(a.bootstrap):
  ix=np.concatenate([np.concatenate([st[j] for j in gen.integers(0,len(st),len(st))]) for st in strata])
  for c,v in allpred.items():draws[c].append(score(yy[ix],v[ix],ll[ix],hh[ix]))
  if (b+1)%100==0:print(json.dumps({'bootstrap_completed':b+1}),flush=True)
 points=[]
 for c,v in point.items():
  for j,e in enumerate(EP+['macro']):
   for k,m in enumerate(MET):points.append({'cell':c,'endpoint':e,'metric':m,'value':v[j,k]})
 contrasts=[]
 for parent in ['zero','repaired']:
  contrasts += [(parent+'__primary4',parent+'__all18'),(parent+'__all18',parent+'__parent'),(parent+'__primary4',parent+'__parent')]
 delta=[]
 for c,ref in contrasts:
  dist=np.array(draws[c])-np.array(draws[ref]);pt=point[c]-point[ref]
  for j,e in enumerate(EP+['macro']):
   for k,m in enumerate(MET):
    low,high=np.quantile(dist[:,j,k],[.025,.975]);delta.append({'contrast':c+' minus '+ref,'endpoint':e,'metric':m,'delta':pt[j,k],'lower95':low,'upper95':high})
 pd.DataFrame(points).to_csv(a.output/'point-metrics.csv',index=False);pd.DataFrame(delta).to_csv(a.output/'paired-deltas.csv',index=False);pd.DataFrame(selections).to_csv(a.output/'selection-audit.csv',index=False)
 receipt={'status':'verified','parent_initialization_and_feature_transform_parity':True,'common_epoch_CPU_RNG_parity':True,'constant_LR_fresh_optimizer_verified':True,'epoch0_selection_verified':True,'official_rows':4905,'metrics':MET,'perfold':perfold,'point':{k:v.tolist() for k,v in point.items()},'bootstrap':{'seed':20261026,'replicates':a.bootstrap,'unit':'pairednative-scaffoldgroupswithinoriginalfolds','interpretation':'conditionaldevelopmentOOF;notindependentprospectiveoralltrainingseeduncertainty'},'serving_calibration_applied':False,'source_sha256':sha(__file__),'stage_manifest_sha256':sha(a.stage/'manifest.json')};(a.output/'READOUT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'status':'verified','macro':{k:v[-1].tolist() for k,v in point.items()}}),flush=True)
if __name__=='__main__':main()
