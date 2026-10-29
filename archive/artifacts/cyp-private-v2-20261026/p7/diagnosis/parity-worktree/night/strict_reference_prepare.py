"""Deterministic data-only preparation of the corrected native reference."""
import argparse,csv,copy,hashlib,json,shutil
from pathlib import Path
from collections import Counter
from functools import lru_cache
import numpy as np,pandas as pd
from rdkit import Chem
from . import briford_native as native

MEMBERS=list(native.MODELS)
AFFECTED={'union18','2d6isoform6'}
EXPECTED={('own750','union18'):4,('own750','2d6isoform6'):2,('briford529','union18'):3,('briford529','2d6isoform6'):3}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hash_json(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def copy_file(src,dest):
 dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);assert sha(src)==sha(dest)
@lru_cache(maxsize=100000)
def canon(s):return Chem.MolToSmiles(Chem.MolFromSmiles(s),isomericSmiles=True)
def read_csv(path):
 with Path(path).open(newline='') as f:return list(csv.DictReader(f))
def prepare(source,audit,stage,cohorts_path,validator):
 if stage.exists() and any(stage.iterdir()):raise FileExistsError('Use an empty staging directory')
 stage.mkdir(parents=True,exist_ok=True)
 exclusions=read_csv(audit/'proposed_strict_tautomer_purge.csv')
 assert len(exclusions)==12 and all(r['source_smiles_match']=='True' and r['stereo_preserving_tautomer_key_equal']=='True' for r in exclusions)
 pairs=[r for r in read_csv(audit/'tautomer-pair-chemical-details.csv') if r['stereo_preserving_tautomer_key_equal']=='True']
 assert len(pairs)==13 and all(r['official_normalization_status']==r['external_normalization_status']=='Completed' for r in pairs)
 queue={r['request_id']:r for r in read_csv(audit/'queue-snapshot.csv')}
 aliases={(r['source'],r['Molecule_Name']):r for r in read_csv(audit/'id-map-snapshot.csv')}
 group={}
 for p in pairs:
  ids=p['request_ids'].split(';');key=min(ids)
  for i in ids:
   assert i in queue and (i not in group or group[i]==key);group[i]=key
 cohorts=json.loads(cohorts_path.read_text())['cohorts']
 copy_file(cohorts_path,stage/'cohorts.json');copy_file(validator,stage/'activity_validation.py')
 for name in ['proposed_strict_tautomer_purge.csv','tautomer-pair-chemical-details.csv','queue-snapshot.csv','id-map-snapshot.csv']:
  copy_file(audit/name,stage/'audit'/name)
 manifest={'protocol':'strict_tautomer_reference_v1','source_sha256':native.sources(),'outer_ids_preserved':True,'inner_validation_assignments_preserved':True,'hyperparameters_preserved':True,'outer_removed_rows':[],'inner_train_removed_rows':[],'components':{},'reused_folds':[],'runtime_packages':None}
 for cohort,expected_n in [('own750',750),('briford529',529)]:
  src=source/cohort;dest=stage/'corrected'/cohort;prep=dest/'prepared';prep.mkdir(parents=True)
  query=read_csv(src/'query.csv');truth=read_csv(src/'truth.csv')
  assert len(query)==expected_n and [r['Molecule_Name'] for r in query]==[r['Molecule_Name'] for r in truth]
  assert set(r['Molecule_Name'] for r in query)==set(cohorts[cohort]['test_ids'])
  held=set(cohorts[cohort]['test_ids']);forbidden=held|set(cohorts[cohort]['outer_parent_purged_ids'])
  strict_held_groups={group[aliases[('official-train.csv',i)]['request_id']] for i in forbidden if aliases[('official-train.csv',i)]['request_id'] in group}
  for name in ['query.csv','truth.csv','exclusion-audit.json']:
   copy_file(src/name,dest/name)
  old_manifest=json.loads((src/'prepared/manifest.json').read_text());assert old_manifest['source_sha256']==native.sources()
  final=json.loads((src/'results/final_complete.json').read_text());assert final['source_sha256']==native.sources() and final['data_manifest_sha256']==sha(src/'prepared/manifest.json')
  original_audit=json.loads((src/'exclusion-audit.json').read_text());newmodels={}
  for member in MEMBERS:
   path=src/'prepared'/f'{member}.csv';spec_path=path.with_suffix('.json');spec=json.loads(spec_path.read_text());assert sha(path)==spec['data_sha256']
   assert original_audit[member]['remaining_held_id_parent_or_connectivity_overlap']==0
   rows=read_csv(path);names=[r['molecule_name'] for r in rows];assert len(names)==len(set(names)) and not(set(names)&forbidden)
   mapping=[aliases[(member,n)] for n in names]
   for row,mapping_row in zip(rows,mapping):assert canon(row['smiles'])==canon(mapping_row['request_smiles'])
   selected=[r for r in exclusions if (r['cohort'],r['member'])==(cohort,member)]
   assert len(selected)==EXPECTED.get((cohort,member),0)
   remove=[]
   for r in selected:
    assert r['heldout_official_id'] in held
    index=names.index(r['training_molecule_name']);assert mapping[index]['request_id']==r['external_request_id']
    assert mapping[index]['request_smiles']==queue[r['external_request_id']]['SMILES']
    assert all(rows[index][t]=='' for t in native.PRIMARY if t in rows[index])
    remove.append(index);manifest['outer_removed_rows'].append({'cohort':cohort,'member':member,'old_index':index,'reason':'audited_stereo_preserving_tautomer_counterpart','heldout_official_id':r['heldout_official_id'],'request_id':r['external_request_id'],'row':rows[index]})
   remove=set(remove);kept=[i for i in range(len(rows)) if i not in remove];old_to_new={old:new for new,old in enumerate(kept)}
   assert not ({group[mapping[i]['request_id']] for i in kept if mapping[i]['request_id'] in group}&strict_held_groups)
   rawlines=path.read_bytes().splitlines(keepends=True);assert len(rawlines)==len(rows)+1
   newpath=prep/f'{member}.csv';newpath.write_bytes(rawlines[0]+b''.join(rawlines[i+1] for i in kept))
   updated=copy.deepcopy(spec);fold_audit=[]
   for fold,f in enumerate(spec['folds']):
    validation=[old_to_new[i] for i in f['validation'] if i in old_to_new]
    train_old=[i for i in f['train'] if i in old_to_new]
    validation_groups={group[mapping[kept[i]]['request_id']] for i in validation if mapping[kept[i]]['request_id'] in group}
    inner_drop=[i for i in train_old if group.get(mapping[i]['request_id']) in validation_groups and mapping[i]['request_id'] in group]
    for i in inner_drop:manifest['inner_train_removed_rows'].append({'cohort':cohort,'member':member,'fold':fold,'old_index':i,'new_index':old_to_new[i],'molecule_name':names[i],'request_id':mapping[i]['request_id'],'strict_group':group[mapping[i]['request_id']]})
    train=[old_to_new[i] for i in train_old if i not in set(inner_drop)]
    assert not set(train)&set(validation)
    assert [rows[kept[i]]['molecule_name'] for i in validation]==[names[i] for i in f['validation'] if i in old_to_new]
    train_groups={group[mapping[kept[i]]['request_id']] for i in train if mapping[kept[i]]['request_id'] in group};assert not(train_groups&validation_groups)
    updated['folds'][fold]={'train':train,'validation':validation}
    fold_audit.append({'fold':fold,'original_train_sha256':hash_json(f['train']),'original_validation_sha256':hash_json(f['validation']),'revised_train_sha256':hash_json(train),'revised_validation_sha256':hash_json(validation),'retained_validation_ids_sha256':hash_json([names[kept[i]] for i in validation]),'inner_train_removed_old_indices':inner_drop,'train_rows':len(train),'validation_rows':len(validation)})
   assert sorted(i for f in updated['folds'] for i in f['validation'])==list(range(len(kept)))
   newframe=pd.read_csv(newpath,float_precision='round_trip');oldframe=pd.read_csv(path,float_precision='round_trip')
   pd.testing.assert_frame_equal(oldframe.iloc[kept].reset_index(drop=True),newframe,check_exact=True)
   counts=newframe[spec['targets']].notna().sum().astype(int).to_dict()
   for target in native.PRIMARY:
    if target in counts:assert counts[target]==spec['target_counts'][target]
   updated.update(rows=len(kept),target_counts=counts,data_sha256=sha(newpath))
   assert updated['hyperparameters']==spec['hyperparameters']
   inner_changes=sum(len(x['inner_train_removed_old_indices']) for x in fold_audit)
   if member not in AFFECTED:
    assert not remove and inner_changes==0 and updated==spec
    copy_file(spec_path,prep/f'{member}.json');assert sha(newpath)==sha(path)
   else:save(prep/f'{member}.json',updated)
   newmodels[member]={k:v for k,v in updated.items() if k!='folds'}
   certificate={'source_data_sha256':sha(path),'source_spec_sha256':sha(spec_path),'new_data_sha256':sha(newpath),'new_spec_sha256':sha(prep/f'{member}.json'),'outer_removed_count':len(remove),'inner_train_removals':inner_changes,'rows_before':len(rows),'rows_after':len(kept),'folds':fold_audit,'old_to_new':{str(k):v for k,v in old_to_new.items()},'hyperparameters_sha256':hash_json(spec['hyperparameters']),'primary_target_counts_unchanged':True,'original_outer_audit_sha256':sha(src/'exclusion-audit.json'),'original_prepared_manifest_sha256':sha(src/'prepared/manifest.json'),'query_sha256':sha(src/'query.csv'),'truth_sha256':sha(src/'truth.csv')}
   manifest['components'][cohort+'/'+member]=certificate
   save(dest/'audits'/f'{member}.json',certificate)
   if member not in AFFECTED:
    for fold in range(5):
     old=src/'results'/member/f'fold{fold}';done=json.loads((old/'complete.json').read_text());metadata=json.loads((old/'metadata.json').read_text());job=json.loads((old/'job.json').read_text())
     assert done['status']=='complete' and done['source_sha256']==native.sources()
     assert metadata['native_training_source']==native.sha(native.VENDOR/'chemprop_core.py') and metadata['model_hyperparameters']==spec['hyperparameters']
     assert metadata['training_rows']==len(spec['folds'][fold]['train']) and metadata['validation_rows']==len(spec['folds'][fold]['validation'])
     assert job['member']==member and job['fold']==fold and job['prepared_dir']==f'/workspace/cyp-repro/holdouts/{cohort}/prepared'
     if manifest['runtime_packages'] is None:manifest['runtime_packages']=metadata['packages']
     assert metadata['packages']==manifest['runtime_packages']
     hashes={}
     for rel,expected in done['files'].items():
      assert sha(old/rel)==expected;copy_file(old/rel,stage/'reuse'/cohort/member/f'fold{fold}'/rel);hashes[rel]=expected
     copy_file(old/'complete.json',stage/'reuse'/cohort/member/f'fold{fold}'/'complete.json')
     assert any(k.endswith('.ckpt') for k in hashes)
     manifest['reused_folds'].append({'cohort':cohort,'member':member,'fold':fold,'complete_sha256':sha(old/'complete.json'),'data_sha256':sha(path),'spec_sha256':sha(spec_path),'fold_sha256':hash_json(spec['folds'][fold]),'query_sha256':sha(src/'query.csv'),'checkpoint_prediction_and_metadata_hashes':hashes})
  combined_audit=copy.deepcopy(original_audit)
  for member in MEMBERS:
   extra=[r['row']['molecule_name'] for r in manifest['outer_removed_rows'] if r['cohort']==cohort and r['member']==member]
   item=combined_audit[member];item['after']=newmodels[member]['rows'];item['removed']=item['before']-item['after']
   item['removed_ids']=item['removed_ids']+extra;item['strict_tautomer_removed_ids']=extra
   item['remaining_strict_outer_tautomer_group_overlap']=0;item['target_counts']=newmodels[member]['target_counts']
  copy_file(src/'exclusion-audit.json',dest/'original-exclusion-audit.json');save(dest/'exclusion-audit.json',combined_audit)
  new_manifest=copy.deepcopy(old_manifest);new_manifest.update(models=newmodels,strict_tautomer_correction=True,original_manifest_sha256=sha(src/'prepared/manifest.json'),original_outer_exclusion_audit=original_audit,outer_exclusion_audit=combined_audit)
  save(prep/'manifest.json',new_manifest)
 assert len(manifest['outer_removed_rows'])==12 and len(manifest['reused_folds'])==20
 assert all(x['member'] in AFFECTED for x in manifest['inner_train_removed_rows'])
 save(stage/'purge-and-reuse-manifest.json',manifest);save(stage/'runtime-packages.json',manifest['runtime_packages'])
 assets={str(p.relative_to(stage)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(stage.rglob('*')) if p.is_file()}
 save(stage/'asset-manifest.json',assets)
 summary={'preparation_only':True,'fits_launched':0,'outer_removed_rows':len(manifest['outer_removed_rows']),'inner_train_removed_rows':len(manifest['inner_train_removed_rows']),'reused_folds_verified':len(manifest['reused_folds']),'retrain_folds':20,'stage_files':len(assets),'stage_bytes':sum(x['bytes'] for x in assets.values()),'asset_manifest_sha256':sha(stage/'asset-manifest.json'),'runtime_packages':manifest['runtime_packages'],'components':{k:{q:v[q] for q in ['rows_before','rows_after','outer_removed_count','inner_train_removals']} for k,v in manifest['components'].items()}}
 print(json.dumps(summary,indent=2));return summary

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--audit',type=Path,required=True);p.add_argument('--stage',type=Path,required=True);p.add_argument('--cohorts',type=Path,required=True);p.add_argument('--validator',type=Path,required=True);p.add_argument('--summary',type=Path,required=True);a=p.parse_args()
 save(a.summary,prepare(a.source,a.audit,a.stage,a.cohorts,a.validator))
if __name__=='__main__':main()
