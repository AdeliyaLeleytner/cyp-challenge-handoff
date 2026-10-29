"""Last bounded meta-experiment. Existing expert predictions; no base model fits."""
from pathlib import Path
import argparse,hashlib,importlib.metadata,json,time
import numpy as np,pandas as pd
from .admet_full import TARGETS,save,event
from .admet_full_math import primary,blend_weight,place,placement_constants
from .admet500_pilot import scores
from .admet_full_contract import require,digest
from .h7_inputs import load_inputs,read_vector
from .simplex_strae import fit_simplex
ROOT=Path(__file__).resolve().parents[1]
METRICS=['ST_RAE','MAE','R2','Spearman','Kendall']

def run(cfg,preflight=False):
    started=time.time();data,cohorts,base,manifest=load_inputs(cfg)
    event('h7_input_verified',cohorts={k:{'train':len(v['train']),'test':len(v['test'])} for k,v in cohorts.items()},source_experts=cfg['expert_order'],base_fits=0)
    if preflight:return
    out=Path(cfg['output_dir']);require(not out.exists() or not any(out.iterdir()),'H7 output already populated');out.mkdir(parents=True,exist_ok=True)
    packages={k:importlib.metadata.version(k) for k in ['numpy','scipy','pandas','scikit-learn','lightgbm','rdkit']}
    save(out/'run-identity.json',{'config':cfg,'config_sha256':digest(ROOT/'h7_config.json'),'packages':packages,'base_fits':0,'model_input_scope':'official5655 audited, base models supervised by official labels only','snapshot_outcomes':manifest['observed_requests'],'acquisition_goal_complete':manifest['collection_complete'],'source_experts':cfg['expert_order'],'development_caveat':'Both fixed cohorts are reused diagnostics, overlap143 molecules; briford529 reconstructed. No unbiased-test claim.'})
    y=data[TARGETS].to_numpy(float);lo=data[[t+'_conf_low' for t in TARGETS]].to_numpy(float);hi=data[[t+'_conf_high' for t in TARGETS]].to_numpy(float)
    constants=placement_constants(ROOT/'vendor/briford_native/cyp_recalibrate.py');summary=[];per=[];weights={};boot=[]
    def write_predictions(name,indices,p):
        df=data.iloc[indices][['Molecule_Name','SMILES']].copy()
        for j,t in enumerate(TARGETS):df[t]=p[:,j]
        df.to_csv(out/(name+'.csv'),index=False,float_format='%.17g')
    def record(cohort,model,lane,te,p):
        r=scores(y[te],p,lo[te],hi[te]);summary.append({'cohort':cohort,'model':model,'lane':lane,**r['macro']})
        per.extend({'cohort':cohort,'model':model,'lane':lane,'target':t,**v} for t,v in r['per_cyp'].items())
        write_predictions(cohort+'__'+model+'__'+lane,te,p);event('outer_diagnostic',cohort=cohort,model=model,lane=lane,macro=r['macro'])
    for cohort,c in cohorts.items():
        tr,te=c['train'],c['test'];oof=c['oof'];query=c['query']
        # LP sees only this cohort's outer-training targets/bounds/OOF predictions.
        pair,check=fit_simplex(y[tr],oof[:,:,:2],lo[tr],hi[tr]);wm,old=blend_weight(y[tr],oof[:,:,0],oof[:,:,1],lo[tr],hi[tr])
        require(abs(check['training_OOF_ST_RAE']-old['blend_training_OOF_ST_RAE'])<1e-8,'Two-expert LP objective parity failed')
        require(abs(wm-c['primary_weight'])<1e-10,'Pinned primary scalar changed')
        w,meta=fit_simplex(y[tr],oof,lo[tr],hi[tr])
        require(meta['training_OOF_ST_RAE']<=check['training_OOF_ST_RAE']+1e-8,'Three-expert optimum worse than its two-expert subset')
        meta.update({'weights':w.tolist(),'expert_order':cfg['expert_order'],'selected_base_params':c['selected_params'],'training_only':True,'two_expert_parity':{'LP_weights':pair.tolist(),'weighted_median_extra_weight':wm,'objective_difference':check['training_OOF_ST_RAE']-old['blend_training_OOF_ST_RAE']}})
        weights[cohort]=meta;save(out/'weights.json',weights) # before any H7 outer scoring
        trainpred={'native':oof[:,:,0],'primary_global':(1-wm)*oof[:,:,0]+wm*oof[:,:,1],'h7_simplex':oof@w}
        testpred={'native':query[:,:,0],'primary_global':(1-wm)*query[:,:,0]+wm*query[:,:,1],'h7_simplex':query@w}
        for model in ['native','primary_global','h7_simplex']:
            write_predictions(cohort+'__'+model+'__training_OOF',tr,trainpred[model]);record(cohort,model,'raw',te,testpred[model])
            placed,details=place(y[tr],trainpred[model],testpred[model],TARGETS,constants)
            require(placed is not None,'Undefined placement must be explicitly handled')
            if model=='native':
                reference=pd.read_csv(manifest['files'][cohort+'_native_placed']['path']).set_index('Molecule_Name').loc[data.iloc[te].Molecule_Name,TARGETS].to_numpy();require(np.allclose(placed,reference,atol=1e-12,rtol=0),'Native placement parity')
            if model=='primary_global':
                reference=read_vector(cfg['files'][cohort+'_primary_global_placed']['path'],data.iloc[te].Molecule_Name,data.iloc[te].SMILES);require(np.allclose(placed,reference,atol=1e-12,rtol=0),'Primary placement parity')
            record(cohort,model,'native_published_placement_diagnostic',te,placed);save(out/(cohort+'__'+model+'__placement.json'),details)
        from rdkit import Chem,RDLogger
        from rdkit.Chem.Scaffolds import MurckoScaffold
        RDLogger.DisableLog('rdApp.*');groups=[]
        for s in data.iloc[te].SMILES:
            m=Chem.MolFromSmiles(s);groups.append(Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(m),isomericSmiles=False) or 'acyclic:'+Chem.MolToInchiKey(m).split('-')[0])
        groups=np.asarray(groups);members=[np.flatnonzero(groups==g) for g in np.unique(groups)];rng=np.random.default_rng(cfg['bootstrap_seed']);values={ref:{k:[] for k in METRICS} for ref in ['native','primary_global']}
        points={k:scores(y[te],p,lo[te],hi[te])['macro'] for k,p in testpred.items()}
        for repeat in range(cfg['bootstrap_samples']):
            ix=np.concatenate([members[k] for k in rng.integers(0,len(members),len(members))]);rs={k:scores(y[te][ix],p[ix],lo[te][ix],hi[te][ix])['macro'] for k,p in testpred.items()}
            for ref in values:
                for metric in METRICS:
                    d=rs['h7_simplex'][metric]-rs[ref][metric]
                    if np.isfinite(d):values[ref][metric].append(d)
        for ref in values:
            for metric,arr in values[ref].items():
                require(len(arr)==cfg['bootstrap_samples'],'Undefined bootstrap values')
                boot.append({'cohort':cohort,'model':'h7_simplex','reference':ref,'lane':'raw','metric':metric,'delta_point':points['h7_simplex'][metric]-points[ref][metric],'lower95':float(np.quantile(arr,.025)),'upper95':float(np.quantile(arr,.975)),'valid_samples':len(arr),'requested_samples':cfg['bootstrap_samples'],'note':'Paired scaffold bootstrap conditional on fitted predictions; reused development cohorts, no selection/multiplicity correction'})
    pd.DataFrame(summary).to_csv(out/'all-metrics.csv',index=False);pd.DataFrame(per).to_csv(out/'per-cyp-metrics.csv',index=False);pd.DataFrame(boot).to_csv(out/'paired-bootstrap.csv',index=False)
    save(out/'complete.json',{'status':'complete','seconds':time.time()-started,'base_fits':0,'simplex_candidate_fits':2,'two_expert_parity_fits':2,'no_full_refit':True,'no_submission':True,'packages':packages,'files_sha256':{p.name:digest(p) for p in out.iterdir() if p.is_file()}})
    event('h7_complete',seconds=time.time()-started,weights={k:v['weights'] for k,v in weights.items()},base_fits=0)

def main():
    p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');a=p.parse_args();cfg=json.loads((ROOT/'h7_config.json').read_text())
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):run(cfg,a.preflight)
if __name__=='__main__':main()
