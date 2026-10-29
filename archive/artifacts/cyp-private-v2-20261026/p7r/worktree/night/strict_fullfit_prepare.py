"""Prepare full native pools with strict train-side inner-fold tautomer exclusions."""
import argparse,copy,json
from pathlib import Path
import numpy as np,pandas as pd
from . import briford_native as native
from .strict_reference_prepare import sha,save,hash_json,copy_file,canon,read_csv

AFFECTED={'union18','2d6isoform6'};REUSED={'mtaux8','2d6single'}
EXPECTED_ROWS={'union18':31670,'mtaux8':4905,'2d6isoform6':23264,'2d6single':1493}
FINAL_SHA='349165ecf50906e43a27f12dee97891a92cda59e798db614ef27a7c920c38a37'
def strict_groups(audit):
 pairs=[r for r in read_csv(audit/'tautomer-pair-chemical-details.csv') if r['stereo_preserving_tautomer_key_equal']=='True']
 assert len(pairs)==13 and all(r['official_normalization_status']==r['external_normalization_status']=='Completed' for r in pairs)
 group={}
 for p in pairs:
  ids=p['request_ids'].split(';');key=min(ids)
  for rid in ids:assert rid not in group or group[rid]==key;group[rid]=key
 assert len(set(group.values()))==13
 return group

def prepare(source,audit,stage,official_train):
 if stage.exists() and any(stage.iterdir()):raise FileExistsError('Use an empty staging folder')
 stage.mkdir(parents=True,exist_ok=True);prep=stage/'prepared';prep.mkdir()
 original=source/'prepared';results=source/'remote/finalized'
 original_manifest=json.loads((original/'manifest.json').read_text());final=json.loads((results/'final_complete.json').read_text())
 assert original_manifest['source_sha256']==native.sources()==final['source_sha256']
 assert final['data_manifest_sha256']==sha(original/'manifest.json')
 old_placed=results/'cyp-ensemble_activity_submission_native_raw_native_strae.csv';assert sha(old_placed)==FINAL_SHA
 query=source/'stage/official-test.csv';assert sha(query)==original_manifest['official_test_sha256']
 copy_file(query,stage/'query.csv');copy_file(source/'stage/activity_validation.py',stage/'activity_validation.py');copy_file(official_train,stage/'official-train.csv')
 copy_file(original/'manifest.json',stage/'original-prepared-manifest.json')
 for name in ['final_complete.json','placement.json','cyp-ensemble_activity_submission_native_raw.csv','cyp-ensemble_activity_submission_native_raw_native_strae.csv']:
  copy_file(results/name,stage/'original-finalized'/name)
 for name in ['tautomer-pair-chemical-details.csv','queue-snapshot.csv','id-map-snapshot.csv','official-test-public-assay-overlap.json']:
  copy_file(audit/name,stage/'audit'/name)
 group=strict_groups(audit);aliases={(r['source'],r['Molecule_Name']):r for r in read_csv(audit/'id-map-snapshot.csv')}
 official=pd.read_csv(official_train);blind=pd.read_csv(query);assert len(official)==4905 and len(blind)==750
 assert official.Molecule_Name.is_unique and blind.Molecule_Name.is_unique and not set(official.Molecule_Name)&set(blind.Molecule_Name)
 manifest={'protocol':'strict_fullfit_inner_tautomer_v1','source_sha256':native.sources(),'native_adapter_sha256':sha(Path(native.__file__)),'historical_training_parent':'d4c1a31c2952f8d933ce035a1cab04417f46cb76','serving_precision_source':'38fe110e5a8d17a7bfb48ac78fe12e425da8deeb','historical_finalized_submission_sha256':FINAL_SHA,'original_prepared_manifest_sha256':sha(original/'manifest.json'),'outer_removed_rows':0,'full_pools_preserved':True,'inner_validation_assignments_preserved':True,'hyperparameters_preserved':True,'strict_groups':13,'inner_train_removed_rows':[],'components':{},'reused_folds':[],'runtime_packages':None,'public_blind_alias_retained':[],'original_fold_durations':[]}
 models={};all_native_ids={}
 for member in native.MODELS:
  source_csv=original/f'{member}.csv';source_spec=original/f'{member}.json';spec=json.loads(source_spec.read_text())
  assert sha(source_csv)==spec['data_sha256'] and spec['rows']==EXPECTED_ROWS[member]
  copy_file(source_spec,stage/'original-specs'/f'{member}.json')
  rows=read_csv(source_csv);names=[r['molecule_name'] for r in rows];assert len(names)==len(set(names))==spec['rows']
  mapping=[aliases[(member,n)] for n in names]
  for row,mapped in zip(rows,mapping):assert canon(row['smiles'])==canon(mapped['request_smiles'])
  gids=[group.get(x['request_id']) for x in mapping]
  copy_file(source_csv,prep/f'{member}.csv');updated=copy.deepcopy(spec);folds=[]
  for fold,old in enumerate(spec['folds']):
   val=old['validation'];val_groups={gids[i] for i in val if gids[i]}
   removed=[i for i in old['train'] if gids[i] and gids[i] in val_groups]
   kept=[i for i in old['train'] if i not in set(removed)]
   for index in removed:
    manifest['inner_train_removed_rows'].append({'member':member,'fold':fold,'row_index':index,'molecule_name':names[index],'request_id':mapping[index]['request_id'],'strict_group':gids[index]})
   assert not set(kept)&set(val) and not({gids[i] for i in kept if gids[i]}&val_groups)
   updated['folds'][fold]={'train':kept,'validation':val.copy()}
   folds.append({'fold':fold,'source_train_sha256':hash_json(old['train']),'source_validation_sha256':hash_json(val),'new_train_sha256':hash_json(kept),'new_validation_sha256':hash_json(updated['folds'][fold]['validation']),'validation_ids_sha256':hash_json([names[i] for i in val]),'removed_training_indices':removed,'train_rows':len(kept),'validation_rows':len(val)})
  assert sorted(i for f in updated['folds'] for i in f['validation'])==list(range(len(rows)))
  assert updated['hyperparameters']==spec['hyperparameters'] and updated['target_counts']==spec['target_counts'] and updated['data_sha256']==spec['data_sha256']
  count=sum(len(f['removed_training_indices']) for f in folds)
  if member in REUSED:
   assert count==0 and updated==spec;copy_file(source_spec,prep/f'{member}.json')
  else:save(prep/f'{member}.json',updated)
  manifest['components'][member]={'rows':len(rows),'source_data_sha256':sha(source_csv),'new_data_sha256':sha(prep/f'{member}.csv'),'source_spec_sha256':sha(source_spec),'new_spec_sha256':sha(prep/f'{member}.json'),'target_counts':spec['target_counts'],'hyperparameters_sha256':hash_json(spec['hyperparameters']),'inner_train_removals':count,'folds':folds}
  models[member]={k:v for k,v in updated.items() if k!='folds'}
  for fold in range(5):
   old=results/member/f'fold{fold}';metadata=json.loads((old/'metadata.json').read_text())
   manifest['original_fold_durations'].append({'member':member,'fold':fold,'seconds':metadata['seconds']})
   if member not in REUSED:continue
   done=json.loads((old/'complete.json').read_text());job=json.loads((old/'job.json').read_text())
   assert done['status']=='complete' and done['source_sha256']==native.sources()
   assert metadata['member']==member and metadata['fold']==fold
   assert metadata['native_training_source']==sha(native.VENDOR/'chemprop_core.py') and metadata['model_hyperparameters']==spec['hyperparameters']
   assert metadata['training_rows']==len(spec['folds'][fold]['train']) and metadata['validation_rows']==len(spec['folds'][fold]['validation'])
   assert job['member']==member and job['fold']==fold and job['prepared_dir']=='/workspace/cyp-repro/assets/prepared' and job['official_test']=='/workspace/cyp-repro/assets/official-test.csv'
   if manifest['runtime_packages'] is None:manifest['runtime_packages']=metadata['packages']
   assert metadata['packages']==manifest['runtime_packages']
   oof=pd.read_csv(old/'oof.csv');test=pd.read_csv(old/'test.csv')
   assert oof.molecule_name.tolist()==[names[i] for i in spec['folds'][fold]['validation']]
   assert test.molecule_name.tolist()==blind.Molecule_Name.tolist()
   assert list(oof.columns)==list(test.columns)==['molecule_name']+spec['targets']
   assert np.isfinite(oof[spec['targets']].to_numpy()).all() and np.isfinite(test[spec['targets']].to_numpy()).all()
   hashes={}
   for rel,h in done['files'].items():
    assert sha(old/rel)==h;copy_file(old/rel,stage/'reuse'/member/f'fold{fold}'/rel);hashes[rel]=h
   copy_file(old/'complete.json',stage/'reuse'/member/f'fold{fold}'/'complete.json');assert any(x.endswith('.ckpt') for x in hashes)
   manifest['reused_folds'].append({'member':member,'fold':fold,'complete_sha256':sha(old/'complete.json'),'source_data_sha256':sha(source_csv),'source_spec_sha256':sha(source_spec),'fold_sha256':hash_json(spec['folds'][fold]),'query_sha256':sha(query),'files':hashes})
  if member in AFFECTED:
   alias='VEITH-RWZAIHHFBKOVIK';assert alias in names
   row=rows[names.index(alias)];assert all(row.get(t,'')=='' for t in native.PRIMARY)
   manifest['public_blind_alias_retained'].append({'member':member,'training_molecule_name':alias,'official_blind_id':'OCNT-0496981','request_id':aliases[(member,alias)]['request_id'],'public_assay_columns':[k for k,v in row.items() if k.endswith('_max_response') and v!='']})
 assert all(r['member'] in AFFECTED for r in manifest['inner_train_removed_rows'])
 assert len(manifest['reused_folds'])==10 and len(manifest['public_blind_alias_retained'])==2
 new_manifest=copy.deepcopy(original_manifest);new_manifest.update(models=models,strict_inner_tautomer_correction=True,full_pool_rows_unchanged=True,original_manifest_sha256=sha(original/'manifest.json'))
 save(prep/'manifest.json',new_manifest)
 # Prove serving arithmetic against the finalized, not obsolete, historical CSV.
 predictions={}
 for member in native.MODELS:
  spec=json.loads((original/f'{member}.json').read_text());targets=spec['targets'];arrays=[]
  for fold in range(5):
   p=pd.read_csv(results/member/f'fold{fold}/test.csv').set_index('molecule_name');arrays.append(p.loc[blind.Molecule_Name,targets].to_numpy(dtype=np.float32))
  mean=np.mean(arrays,axis=0).astype(np.float64);predictions[member]={t:mean[:,j] for j,t in enumerate(targets)}
 old_raw=pd.read_csv(results/'cyp-ensemble_activity_submission_native_raw.csv').set_index('Molecule_Name').loc[blind.Molecule_Name];parity={}
 for iso in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']:
  t=iso.lower()+'_pic50_direct_inhibition';members=list(native.MODELS) if iso=='CYP2D6' else ['union18','mtaux8']
  reconstructed=np.column_stack([predictions[m][t] for m in members]).mean(axis=1)
  difference=float(np.max(np.abs(reconstructed-old_raw[iso+'_pIC50_direct_inhibition'].to_numpy())))
  assert difference<1e-12;parity[iso]=difference
 manifest['historical_finalized_raw_numeric_parity']=parity
 save(stage/'purge-and-reuse-manifest.json',manifest);save(stage/'runtime-packages.json',manifest['runtime_packages'])
 assets={str(p.relative_to(stage)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(stage.rglob('*')) if p.is_file()};save(stage/'asset-manifest.json',assets)
 summary={'preparation_only':True,'fits_launched':0,'outer_removed_rows':0,'strict_groups':13,'inner_train_removed_rows':len(manifest['inner_train_removed_rows']),'reused_folds':10,'retrain_folds':10,'stage_files':len(assets),'stage_bytes':sum(v['bytes'] for v in assets.values()),'asset_manifest_sha256':sha(stage/'asset-manifest.json'),'components':{k:{'rows':v['rows'],'inner_train_removals':v['inner_train_removals']} for k,v in manifest['components'].items()},'historical_finalized_raw_numeric_parity':parity,'historical_finalized_placed_sha256':FINAL_SHA}
 return summary

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--audit',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--official-train',type=Path,required=True);p.add_argument('--summary',type=Path,required=True);a=p.parse_args();summary=prepare(a.source,a.audit,a.stage,a.official_train);save(a.summary,summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
