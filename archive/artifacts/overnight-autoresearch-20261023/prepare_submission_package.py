"""Root-owned post-run evidence packaging. Does not train or submit."""
from pathlib import Path
import hashlib,json,sqlite3,datetime
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parent
E=P/'final_ensemble_v1'; OUT=P/'submission_package_v1'
TARGETS=[f'{c}_pIC50_direct_inhibition' for c in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
def read(p):return json.loads(p.read_text())
def rec(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(name,value):
    path=OUT/name
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    return rec(path)
OUT.mkdir(exist_ok=True)
meta=read(E/'metadata.json'); done=read(E/'complete.json');recipe=read(P/'gate_bundle_v1/qualified_recipe.json')
assert done['status']=='complete' and meta['recipe']==recipe and meta['recipe_compatibility']['matched']
assert rec(E/'submission.csv')['sha256']==meta['submission_sha256']==done['submission_sha256']
# Exact recipe audit is mechanically checked by final_ensemble before any output.
compat=meta['recipe_compatibility']
assert compat['no_additional_base_placement'] and compat['no_additional_width_or_neighbor_correction']
assert compat['same_full_train_folds_both_seeds'] and meta['actual_test_labels_read'] is False
assert set(meta['seeds'])=={'42','142'}
for seed in [42,142]:
    m=read(E/f'seed{seed}_metadata.json')
    assert m['protocol']['model_names']==recipe['metamodel']['model_names']
    assert m['protocol']['weight_constraint']==recipe['metamodel']['weight_constraint']
    assert m['selected_candidate'] in m['protocol']['tie_order']
    assert m['n_development']==4905 and m['n_query']==750
    assert m['query_labels_used'] is False and m['query_moments_used'] is False
    assert m['allowed_fit_ids_checked'] and m['forbidden_fit_ids_checked']
# Match reference output aggregation without looking at TEST labels.
q=pd.read_csv(E/'submission.csv'); refs=[];raws=[]
for seed,root in [(42,P/'remote/results/FINAL_reference_seed42'),(142,P/'remote2/results/FINAL_reference_seed142')]:
    for kind,arr in [('test_calibrated.csv',refs),('test_raw.csv',raws)]:
        f=pd.read_csv(root/'briford_reference'/f'seed{seed}'/kind).set_index('Molecule_Name')
        arr.append(f.loc[q.Molecule_Name,TARGETS].to_numpy())
ref=np.mean(refs,axis=0);raw=np.mean(raws,axis=0);candidate=q[TARGETS].to_numpy()
checks={}
for j,t in enumerate(TARGETS):
    a,b=candidate[:,j],ref[:,j]
    checks[t]={'candidate_mean':float(a.mean()),'reference_mean':float(b.mean()),'mean_shift':float((a-b).mean()),'candidate_sd':float(a.std(ddof=1)),'reference_sd':float(b.std(ddof=1)),'sd_ratio':float(a.std(ddof=1)/b.std(ddof=1)),'max_abs_difference':float(np.abs(a-b).max()),'pearson':float(np.corrcoef(a,b)[0,1])}
reference_csv=q[['Molecule_Name','SMILES']].copy();reference_csv[TARGETS]=ref
reference_csv.to_csv(OUT/'reference_comparator_NOT_SUBMITTED.csv',index=False,float_format='%.17g')
check_record=save('test_vector_comparison.json',{'actual_test_scored':False,'checks':checks,'candidate':rec(E/'submission.csv'),'reference':rec(OUT/'reference_comparator_NOT_SUBMITTED.csv'),'selection_scope':'No TEST moments used for fitting or selection; descriptive consistency audit only'})
c=sqlite3.connect('/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/orx.db');c.row_factory=sqlite3.Row
source_runs=[]
runids=['164ab051-2fe9-4c7e-8402-b844870a02e0','d50ef4b5-049c-4aac-9642-2fb3459fb99e']
# Find successful exact packaging node run, retaining its source commit.
rows=list(c.execute('select * from runs where experiment_id=? and status=? order by created_at desc',('9aed4e20-2f5d-4521-9b56-6ba5f41095e6','done')))
assert len(rows)==1, 'Exactly one successful final packaging run required'
runids.append(rows[0]['id'])
for rid in runids:
    row=dict(c.execute('select * from runs where id=?',(rid,)).fetchone())
    assert row['status']=='done' and row['exit_code'] in (None,0)
    state={k:row[k] for k in ['id','experiment_id','project_id','status','exit_code','command','commit_sha','created_at','updated_at','ended_at','backend_json']}
    source_runs.append({'run_id':rid,'status':'done','evidence':save('run-'+rid+'.json',state)})
provenance={'status':'completed','candidate_name':recipe['candidate_name'],'recipe_sha256':rec(P/'gate_bundle_v1/qualified_recipe.json')['sha256'],'gate_certificate_sha256':rec(P/'gate_bundle_v1/certificate.json')['sha256'],'submission_csv_sha256':rec(E/'submission.csv')['sha256'],'official_test_sha256':rec(P/'remote/assets/official-test.csv')['sha256'],'training_scope':'full_official_train','actual_test_scored':False,'recipe_match_verified':True,'seeds':[42,142],'targets':TARGETS,'source_runs':source_runs,'root_recipe_review':{'method':'Exact recipe equality; forty-fold source/data/completion hashes and raw aggregates reconstructed by final_ensemble; protocol names/constraint/candidate set/fit ids checked again here.','qualification_chain':rec(E/'qualification_chain.json'),'final_metadata':rec(E/'metadata.json'),'vector_checks':check_record,'fit_selection_scope':'Same frozen training-only crossfit selection procedure; fitted lambda and coefficients refit on full TRAIN. No frozen coefficient or lambda assumption.'}}
prov=save('final_training_provenance.json',provenance)
sources=P/'sources/presend-20261023T2345'
# Paths must match live refresh filenames; no stale snapshot fallback.
manifest={'schema_version':1,'candidate_name':recipe['candidate_name'],'qualified_recipe':rec(P/'gate_bundle_v1/qualified_recipe.json'),'gate_certificate':rec(P/'gate_bundle_v1/certificate.json'),'final_training_provenance':prov,'submission_csv':rec(E/'submission.csv'),'official_test':rec(P/'remote/assets/official-test.csv'),'official_validator':rec(P/'sources/activity_validation.py'),'api_schema':rec(sources/'gradio-info.json'),'source_snapshots':{k:rec(sources/(k+'.py')) for k in ['app','submission','config']},'model_tag':'Scratch D-MPNN multitask ensemble, 5 folds x 2 seeds, TRAIN-OOF affine stacking; public ChEMBL and PubChem','gradio_client_version':'2.7.2','disclosures':{'publication_opt_in':False,'used_proprietary_data':False,'open_source_code':False}}
save('submission-manifest.json',manifest)
print(json.dumps({'package':str(OUT),'checks':checks,'selected':{s:v['selected_candidate'] for s,v in meta['seeds'].items()}},indent=2))
