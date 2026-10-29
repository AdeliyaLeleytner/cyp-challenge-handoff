"""H6 official-only ADME representation comparison with complete audited model inputs.

Selection uses each outer-training pool's inner OOF only. Outer diagnostics are
not used to choose hyperparameters or blend weights. No submission/refit occurs.
"""
from pathlib import Path
import argparse,json,sys,time
from .admet_full_contract import validate,digest,ContractError,require

ROOT=Path(__file__).resolve().parents[1]
TARGETS=[f'{x}_pIC50_direct_inhibition' for x in ('CYP1A2','CYP2C9','CYP2D6','CYP3A4')]

def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False,default=lambda x:x.item() if hasattr(x,'item') else str(x))+'\n')
def event(name,**kw):print(json.dumps({'event':name,**kw},allow_nan=False),flush=True)

def load_data(cfg,manifest,paths,columns):
    import numpy as np
    import pandas as pd
    from rdkit import Chem,RDLogger
    from rdkit.Chem import Descriptors,rdFingerprintGenerator
    from rdkit.Chem.Scaffolds import MurckoScaffold
    from .public_data import normalize_parent_key
    from .admet_full_models import feature_groups
    RDLogger.DisableLog('rdApp.*')
    train=pd.read_csv(paths['official_train']);blind=pd.read_csv(paths['official_test'])
    require(len(train)==4905 and len(blind)==750,'Official row count mismatch')
    require(train.Molecule_Name.is_unique and blind.Molecule_Name.is_unique,'Duplicate official ID')
    require(not set(train.Molecule_Name)&set(blind.Molecule_Name),'Official train/test ID overlap')
    require(set(TARGETS)<=set(train),'Missing direct-inhibition targets')
    mapping=pd.read_csv(paths['id_map'],dtype=str)
    chosen=mapping[mapping.source=='official-train.csv'].copy()
    require(chosen.Molecule_Name.is_unique and chosen.request_id.is_unique,'Official mapping is not one-to-one')
    chosen=chosen.set_index('Molecule_Name').loc[train.Molecule_Name]
    train=train.copy();train['request_id']=chosen.request_id.to_numpy();train['request_smiles']=chosen.request_smiles.to_numpy()
    blind_map=mapping[mapping.source=='official-test.csv'].copy()
    require(blind_map.Molecule_Name.is_unique and blind_map.request_id.is_unique,'Blind mapping is not one-to-one')
    blind_map=blind_map.set_index('Molecule_Name').loc[blind.Molecule_Name]
    require(not set(chosen.request_id)&set(blind_map.request_id),'Identical request structure in official train and blind test')
    for smi,requested in zip(blind.SMILES,blind_map.request_smiles):
        mol=Chem.MolFromSmiles(smi)
        require(mol is not None and Chem.MolToSmiles(mol)==requested,'Blind request/official graph mismatch')
    features=pd.read_csv(paths['numeric_features']).set_index('request_id')
    require(features.index.is_unique,'Duplicate feature identity')
    require(set(blind_map.request_id)<=set(features.index),'Missing blind features')
    ad=features.loc[train.request_id,columns].to_numpy(float)
    require(np.isfinite(ad).all(),'Nonfinite ADMET features require an explicit audited policy')
    mols=[Chem.MolFromSmiles(s) for s in train.SMILES]
    require(all(m is not None for m in mols),'Invalid official SMILES')
    require(all(Chem.MolToSmiles(m)==s for m,s in zip(mols,train.request_smiles)),'Request/official graph identity mismatch')
    gen=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048)
    fp=np.asarray([gen.GetFingerprintAsNumPy(m) for m in mols],dtype=np.float64)
    rd=np.asarray([[fn(m) for _,fn in Descriptors._descList] for m in mols],dtype=float);rd[~np.isfinite(rd)]=np.nan
    train['connectivity']=[Chem.MolToInchiKey(m).split('-')[0] for m in mols]
    train['parent_key']=[normalize_parent_key(s) for s in train.SMILES]
    require(train.parent_key.notna().all(),'Invalid parent key')
    groups=[]
    for m,key in zip(mols,train.connectivity):
        groups.append(Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(m),isomericSmiles=False) or 'acyclic:'+key)
    y=train[TARGETS].to_numpy(float)
    lo=train[[t+'_conf_low' for t in TARGETS]].to_numpy(float);hi=train[[t+'_conf_high' for t in TARGETS]].to_numpy(float)
    observed=np.isfinite(y)
    require(np.isfinite(lo[observed]).all() and np.isfinite(hi[observed]).all(),'Missing observed-label bounds')
    require(np.all(lo[observed]<=hi[observed]),'Reversed confidence interval')
    cohorts=json.loads(paths['cohorts'].read_text())['cohorts'];lookup={key:i for i,key in enumerate(train.Molecule_Name)}
    frozen={};audits={}
    for name,expected in [('own750',750),('briford529',529)]:
        c=cohorts[name];tr=np.array([lookup[x] for x in c['train_ids']]);te=np.array([lookup[x] for x in c['test_ids']])
        require(len(te)==expected and not set(tr)&set(te),'Outer cohort mismatch')
        for key in ('connectivity','parent_key'):
            require(not set(train.iloc[tr][key])&set(train.iloc[te][key]),'Outer '+key+' overlap; investigate frozen definitions')
        splits=[];seen=[]
        for fold in c['inner_folds']:
            a=np.array([lookup[x] for x in fold['train_ids']]);b=np.array([lookup[x] for x in fold['val_ids']])
            require(set(a)<=set(tr) and set(b)<=set(tr) and not set(a)&set(b),'Inner fold leaked outside training pool')
            require(not set(train.iloc[a].parent_key)&set(train.iloc[b].parent_key),'Inner parent overlap')
            splits.append((a,b));seen.extend(b.tolist())
        require(len(splits)==5 and sorted(seen)==sorted(tr.tolist()),'Inner OOF coverage mismatch')
        frozen[name]=(tr,te,splits)
        audits[name]={'train':len(tr),'test':len(te),'fold_validation_counts':[len(b) for _,b in splits],
                      'outer_train_ids':train.iloc[tr].Molecule_Name.tolist(),'outer_test_ids':train.iloc[te].Molecule_Name.tolist()}
    for key,item in manifest['files'].items():require(digest(paths[key])==item['sha256'],'Asset changed during preparation: '+key)
    groups_by_endpoint=feature_groups(columns)
    audits['prespecified_feature_groups']={name:[columns[i] for i in indices] for name,indices in groups_by_endpoint.items()}
    X={'fp':fp,'rd':rd,'admet':ad,'admet_groups':groups_by_endpoint,'structure':np.column_stack([fp,rd])}
    from .h5_features import build_views
    views,embedding_audit=build_views(train,ad,cfg)
    require(embedding_audit['provenance']['official_train_sha256']==manifest['files']['official_train']['sha256'],'Embedding official source changed')
    X.update(views);audits['adme_embedding_views']=embedding_audit
    return train,X,y,lo,hi,np.array(groups),frozen,audits

def native_predictions(paths,cohort,data):
    import numpy as np
    import pandas as pd
    from .admet500_pilot import old_base_predictions
    aliases={cohort+'_native_test':paths[cohort+'_native_raw']}
    aliases.update({cohort+'_'+m+'_oof':paths[cohort+'_'+m+'_oof'] for m in ('union18','mtaux8','2d6isoform6','2d6single')})
    oof,test=old_base_predictions(aliases,cohort,data)
    return oof,test

def save_predictions(out,name,data,indices,pred):
    frame=data.iloc[indices][['Molecule_Name','SMILES','request_id']].copy()
    for j,t in enumerate(TARGETS):frame[t]=pred[:,j]
    frame.to_csv(out/(name+'.csv'),index=False)

def evaluate(cfg,manifest,paths,columns):
    import numpy as np
    import pandas as pd
    import subprocess,importlib.metadata
    from threadpoolctl import threadpool_limits
    from .admet500_pilot import scores
    from .admet_full_models import predict
    from .admet_full_math import blend_weight,place,placement_constants,primary
    started=time.time();out=Path(cfg['output_dir'])
    require(not (out/'complete.json').exists(),'Output already completed; create a child/output for a new run')
    out.mkdir(parents=True,exist_ok=True)
    identity={'config':cfg,'manifest_sha256':digest(cfg['snapshot_manifest']),'source_mode':'web_default','acquisition_goal_rows':32421,'snapshot_outcomes':manifest['observed_requests'],'acquisition_goal_complete':manifest['collection_complete'],'model_input_rows':5655,'reference_usage':'conditional_fixed_legacy_expert','official_train_rows':4905,'official_test_rows':750,'heldout_reuse_caveat':'Both frozen cohorts are development diagnostics; briford529 is reconstructed and the cohorts overlap143 molecules.'}
    old=out/'run-identity.json'
    if old.exists():require(json.loads(old.read_text())==identity,'Existing output belongs to another configuration/input')
    save(old,identity)
    data,X,y,lo,hi,groups,cohorts,audit=load_data(cfg,manifest,paths,columns)
    save(out/'data-audit.json',audit);save(out/'admet-feature-columns.json',columns)
    data[['Molecule_Name','SMILES','request_id']].to_csv(out/'official-embedding-input.csv',index=False)
    if any(x['family']=='chemeleon_ridge' for x in cfg['portfolio']):
        subprocess.run([sys.executable,'-u','-m','night.admet500_embed',str(out/'official-embedding-input.csv'),str(paths['chemeleon']),str(out/'frozen-chemeleon.npy')],check=True)
        X['chemeleon']=np.load(out/'frozen-chemeleon.npy')
        require(X['chemeleon'].shape==(4905,2048) and np.isfinite(X['chemeleon']).all(),'Frozen embedding alignment/shape failure')
    constants=placement_constants(ROOT/'vendor/briford_native/cyp_recalibrate.py')
    summary=[];per_target=[];selected={};predictions={};baseline={};oof_manifest={}
    def record(cohort,name,lane,indices,pred,meta=None):
        result=scores(y[indices],pred,lo[indices],hi[indices])
        summary.append({'cohort':cohort,'model':name,'lane':lane,**result['macro']})
        for t,value in result['per_cyp'].items():per_target.append({'cohort':cohort,'model':name,'lane':lane,'target':t,**value})
        save_predictions(out,cohort+'__'+name+'__'+lane,data,indices,pred)
        if meta is not None:save(out/(cohort+'__'+name+'__'+lane+'__metadata.json'),meta)
        predictions[(cohort,name,lane)]=pred
        event('outer_diagnostic',cohort=cohort,model=name,lane=lane,macro=result['macro'])
    for cohort,(tr,te,splits) in cohorts.items():
        base_oof,base_test=native_predictions(paths,cohort,data)
        require(np.isfinite(base_oof[tr][np.isfinite(y[tr])]).all() and np.isfinite(base_test[te]).all(),'Missing native predictions')
        baseline[cohort]=base_test[te];selected[cohort]={}
        record(cohort,'native','raw',te,base_test[te])
        placed=pd.read_csv(paths[cohort+'_native_placed']).set_index('Molecule_Name').loc[data.iloc[te].Molecule_Name,TARGETS].to_numpy()
        record(cohort,'native','native_published_placement_diagnostic',te,placed)
        reconstructed,placement_meta=place(y[tr],base_oof[tr],base_test[te],TARGETS,constants)
        require(reconstructed is not None and np.allclose(reconstructed,placed,atol=1e-6,rtol=1e-6),'Placement reimplementation does not match pinned native baseline')
        save(out/(cohort+'__native_placement_parity.json'),placement_meta)
        for spec in cfg['portfolio']:
            name=spec['name'];candidates=[];oof_by_id={}
            for number,params in enumerate(spec['grid']):
                candidate=name+'__grid'+str(number);oof=np.full_like(y,np.nan)
                for fold,(fit_ids,val_ids) in enumerate(splits):
                    for j in range(4):
                        fit=fit_ids[np.isfinite(y[fit_ids,j])]
                        require(len(fit)>=2,'Insufficient labels in training fold')
                        oof[val_ids,j]=predict(spec,params,fit,val_ids,y[fit,j],X,cfg['model_seed'],cfg['threads'])
                require(np.isfinite(oof[tr]).all(),'Incomplete training OOF')
                result=scores(y[tr],oof[tr],lo[tr],hi[tr]);oof_by_id[candidate]=oof
                candidates.append({'candidate':candidate,'params':params,'training_OOF':result})
                save_predictions(out,cohort+'__'+candidate+'__training_OOF',data,tr,oof[tr])
                event('inner_candidate_complete',cohort=cohort,model=name,candidate=candidate,metrics=result['macro'])
            chosen=min(candidates,key=lambda row:(row['training_OOF']['macro']['ST_RAE'],row['candidate']))
            oof=oof_by_id[chosen['candidate']];params=chosen['params']
            # Commit selection evidence before consulting this model's outer scores.
            selected[cohort][name]={'selected':chosen,'candidates':candidates,'selection_uses_outer_labels':False}
            save(out/'inner-selection.json',selected)
            query=np.empty((len(te),4))
            for j in range(4):
                fit=tr[np.isfinite(y[tr,j])];query[:,j]=predict(spec,params,fit,te,y[fit,j],X,cfg['model_seed'],cfg['threads'])
            record(cohort,name,'raw',te,query)
            pp,meta=place(y[tr],oof[tr],query,TARGETS,constants)
            if pp is not None:record(cohort,name,'native_published_placement_diagnostic',te,pp,meta)
            else:save(out/(cohort+'__'+name+'__undefined-placement.json'),meta)
            selected[cohort][name]['blends']={}
            for mode in cfg['blend_modes']:
                if mode=='global':w,info=blend_weight(y[tr],base_oof[tr],oof[tr],lo[tr],hi[tr])
                elif mode=='per_target':
                    pieces=[blend_weight(y[tr,j:j+1],base_oof[tr,j:j+1],oof[tr,j:j+1],lo[tr,j:j+1],hi[tr,j:j+1]) for j in range(4)]
                    w=np.array([piece[0] for piece in pieces]);info={'per_target_fit':dict(zip(TARGETS,[piece[1] for piece in pieces])),'fit_scope':'outer training OOF only'}
                else:raise ValueError('Unknown blend mode:'+mode)
                blend=(1-w)*base_test[te]+w*query;blend_oof=(1-w)*base_oof[tr]+w*oof[tr]
                info['blend_training_OOF_ST_RAE']=primary(y[tr],blend_oof,lo[tr],hi[tr])
                stored_weight=w.tolist() if isinstance(w,np.ndarray) else w
                blend_name=name+'__native_blend_'+mode
                record(cohort,blend_name,'raw',te,blend,{'weight':stored_weight,**info})
                pp,meta=place(y[tr],blend_oof,blend,TARGETS,constants)
                if pp is not None:record(cohort,blend_name,'native_published_placement_diagnostic',te,pp,meta)
                else:save(out/(cohort+'__'+blend_name+'__undefined-placement.json'),meta)
                selected[cohort][name]['blends'][mode]={'weight':stored_weight,**info}
                save(out/'inner-selection.json',selected)
        # This winner is cohort-specific; do not pool selection across different outer-training sets.
        options=[('native',scores(y[tr],base_oof[tr],lo[tr],hi[tr])['macro']['ST_RAE'])]
        for name,value in selected[cohort].items():
            options.append((name,value['selected']['training_OOF']['macro']['ST_RAE']))
            options += [(name+'__native_blend_'+mode,info['blend_training_OOF_ST_RAE']) for mode,info in value['blends'].items()]
        winner=min(options,key=lambda x:(x[1],x[0]))
        oof_manifest[cohort]={'chosen_by_training_OOF_only':winner[0],'training_OOF_ST_RAE':winner[1],'diagnostic_outer_scores_not_used':True,'not_a_global_final_submission_recipe':True}
    pd.DataFrame(summary).to_csv(out/'all-metrics.csv',index=False);pd.DataFrame(per_target).to_csv(out/'per-cyp-metrics.csv',index=False)
    save(out/'cohort-specific-selection.json',oof_manifest)
    paired=[]
    for cohort,(tr,te,splits) in cohorts.items():
        unique=np.unique(groups[te]);members=[np.flatnonzero(groups[te]==g) for g in unique];rng=np.random.default_rng(cfg['bootstrap_seed'])
        resamples=[np.concatenate([members[k] for k in rng.integers(0,len(unique),len(unique))]) for _ in range(cfg['bootstrap_samples'])]
        for name in sorted({key[1] for key in predictions if key[0]==cohort and key[2]=='raw' and key[1]!='native'}):
            p=predictions[(cohort,name,'raw')];point_a=scores(y[te],p,lo[te],hi[te])['macro'];point_b=scores(y[te],baseline[cohort],lo[te],hi[te])['macro'];deltas={metric:[] for metric in ('ST_RAE','MAE','R2','Spearman','Kendall')}
            for ix in resamples:
                try:
                    a=scores(y[te][ix],p[ix],lo[te][ix],hi[te][ix])['macro'];b=scores(y[te][ix],baseline[cohort][ix],lo[te][ix],hi[te][ix])['macro']
                except (ValueError,AssertionError):continue
                for metric in deltas:
                    if a[metric] is not None and b[metric] is not None and np.isfinite(a[metric]-b[metric]):deltas[metric].append(a[metric]-b[metric])
            for metric,values in deltas.items():
                paired.append({'cohort':cohort,'model':name,'reference':'native','lane':'raw','metric':metric,'delta_point':point_a[metric]-point_b[metric] if point_a[metric] is not None and point_b[metric] is not None else None,'lower95':float(np.quantile(values,.025)) if values else None,'upper95':float(np.quantile(values,.975)) if values else None,'valid_samples':len(values),'requested_samples':cfg['bootstrap_samples'],'note':'Paired scaffold bootstrap conditional on predictions; exploratory multiple comparisons, no selection correction'})
    pd.DataFrame(paired).to_csv(out/'paired-bootstrap.csv',index=False)
    save(out/'complete.json',{'status':'complete','seconds':time.time()-started,'no_full_refit':True,'no_submission':True,'source_mode':'web_default','packages':{x:importlib.metadata.version(x) for x in ('numpy','pandas','scikit-learn','lightgbm','rdkit','torch','chemprop')}})
    event('full_feature_evaluation_complete',seconds=time.time()-started,output=str(out),selection=oof_manifest)

def main():
    p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');args=p.parse_args()
    cfg=json.loads((ROOT/'full_feature_config.json').read_text())
    require(digest(ROOT/'official_scoring_functions.py')==cfg['scorer_sha256'],'Official scorer revision changed')
    require(digest(ROOT/'vendor/briford_native/cyp_recalibrate.py')==cfg['placement_source_sha256'],'Placement source changed')
    try:manifest,paths,columns=validate(cfg)
    except (ContractError,OSError) as exc:
        event('input_contract_blocked',error=str(exc),fits_started=0);raise SystemExit(2)
    require(digest(ROOT/'night/h5_features.py')==cfg['embedding_contract_sha256'],'Embedding validator source changed')
    from .h5_features import validate_embedding_assets
    _,proof=validate_embedding_assets(cfg)
    require(proof['official_train_sha256']==manifest['files']['official_train']['sha256'],'Embedding source table changed')
    if args.preflight:
        load_data(cfg,manifest,paths,columns)
        event('input_contract_ready',model_input_rows=5655,adme_embedding_rows=4905,blind_adme_embedding_rows=0,snapshot_outcomes=manifest['observed_requests'],acquisition_goal_complete=manifest['collection_complete'],views=[600,720],fits_started=0)
        return
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=cfg['threads']):evaluate(cfg,manifest,paths,columns)
if __name__=='__main__':main()
