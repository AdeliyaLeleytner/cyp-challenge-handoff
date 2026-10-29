from pathlib import Path
import json,hashlib,sqlite3,shutil
p=Path(__file__).resolve().parent;out=p/'gate_bundle_v1';out.mkdir(exist_ok=True)
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
def asset(x):return {'path':str(Path(x).resolve()),'sha256':sha(x)}
conn=sqlite3.connect('file:/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/orx.db?mode=ro',uri=True);conn.row_factory=sqlite3.Row
runs={42:['c21a6b2a-c01f-473f-bae1-f78869f29bc7','7eb5500d-fe98-4fe1-8f53-009b75723e23'],142:['55299c4e-66d2-4474-bc16-cfd5dfcd007d','f2c81394-f501-4e06-9e80-c20acd9eadcf']}
evidence={}
for run in sum(runs.values(),[]):
 row=dict(conn.execute('select id,experiment_id,project_id,status,commit_sha,exit_code,created_at,ended_at,updated_at from runs where id=?',(run,)).fetchone())
 assert row['status']=='done' and row['exit_code'] in (None,0),row
 f=out/(run+'.json');f.write_text(json.dumps(row,indent=2));evidence[run]=asset(f)
members=['union18','mtaux8','2d6isoform6','2d6single']
manifest={'schema_version':1,'truth':asset(p/'stage/official-train.csv'),'cohorts':asset(p/'stage/cohorts.json'),'candidate':{'name':'reference_reweight_affine','predictions':{}},'reference':{'name':'briford_reference','recipe_members':members,'predictions':{}}}
for role in ['candidate','reference']:
 for cohort in ['own750','briford529']:
  manifest[role]['predictions'][cohort]={}
  for seed in [42,142]:
   if role=='candidate':
    base=p/'quick/results/M1_reference_reweight' if seed==42 else p/'confirmation_affine142'
    src=base/'reference_reweight_affine'/cohort/f'seed{seed}'/'predictions.csv'
   else:
    base=p/'quick/results/R0_reference_seed42' if seed==42 else p/'ref142_inputs'
    src=base/'briford_reference'/cohort/f'seed{seed}'/'outer_calibrated.csv'
   assert src.exists(),src
   dst=out/f'{role}_{cohort}_{seed}.csv';shutil.copy2(src,dst)
   selected=runs[seed] if role=='candidate' else [runs[seed][0]]
   prov={'status':'completed','model_name':manifest[role]['name'],'cohort':cohort,'seed':seed,'prediction_sha256':sha(dst),'source_prediction':asset(src),'source_runs':[{'run_id':r,'status':'done','evidence':evidence[r]} for r in selected]}
   if role=='reference':prov['recipe_members']=members
   f=out/f'{role}_{cohort}_{seed}_provenance.json';f.write_text(json.dumps(prov,indent=2));manifest[role]['predictions'][cohort][str(seed)]=dict(asset(dst),run_status='completed',provenance=asset(f))
recipe={'schema_version':1,'candidate_name':'reference_reweight_affine','base_recipe':asset(p/'reference_audit/reference_recipe.json'),'base_members':members,'foundation_initialization':'scratch','seeds':[42,142],'inner_folds':5,'fold_seed':42,'public_parent_exclusion':'all official train and actualTEST normalized parents','aggregation':'mean of five fold models per seed, then mean of both final seed vectors','views':'R0 raw four-member average plus union18,mtaux8,and two views replacing only CYP2D6 by its specialist','metamodel':{'model_names':['briford_reference','union18','mtaux8','specialist_single_view','specialist_aux_view'],'weight_constraint':'positive_affine','reference_model':'briford_reference','l1_grid':[0,.01,.1,1.0],'selection':'development crossfit ST-RAE only'},'proprietary_data_used':False,'unknown_CYP_pretraining_weights_used':False}
f=out/'qualified_recipe.json';f.write_text(json.dumps(recipe,indent=2));manifest['candidate']['recipe']=asset(f)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
print({'manifest':str(out/'manifest.json'),'verified_source_runs':len(evidence),'recipe_sha256':sha(f)})
