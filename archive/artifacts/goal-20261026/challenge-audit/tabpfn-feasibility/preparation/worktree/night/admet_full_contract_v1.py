"""Immutable full-feature input contract. Standard library only; never fits models."""
from pathlib import Path
import csv,hashlib,json

class ContractError(ValueError):pass

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_json(path):return json.loads(Path(path).read_text())
def require(condition,message):
    if not condition:raise ContractError(message)

def validate(cfg):
    require(cfg.get('stage')=='evaluate','Only evaluation stage is implemented; no implicit refit/submission')
    manifest_path=cfg.get('snapshot_manifest');manifest_sha=cfg.get('snapshot_manifest_sha256')
    require(bool(manifest_path) and bool(manifest_sha),'Complete snapshot manifest and SHA256 must be pinned before any fit')
    require(digest(manifest_path)==manifest_sha,'Snapshot manifest SHA256 mismatch')
    m=read_json(manifest_path)
    require(m.get('schema_version')==1,'Unsupported snapshot contract')
    require(m.get('source_mode')=='web_default','Do not mix API feature=true vectors with web_default')
    require(m.get('collection_complete') is True and m.get('expected_requests')==32421,'Full32421 acquisition must be complete')
    require(m.get('expected_official_train')==4905 and m.get('expected_official_test')==750,'Official cohort counts changed')
    keys=['raw_features','numeric_features','feature_schema','queue','id_map','official_train','official_test','cohorts','chemical_audit','chemeleon']
    for cohort in ('own750','briford529'):
        keys += [cohort+'_native_raw',cohort+'_native_placed']+[cohort+'_'+member+'_oof' for member in ('union18','mtaux8','2d6isoform6','2d6single')]
    files=m.get('files',{});require(set(keys)<=set(files),'Missing required snapshot files: '+','.join(sorted(set(keys)-set(files))))
    paths={}
    for key,item in files.items():
        require(bool(item.get('path')) and bool(item.get('sha256')),'Unpinned asset: '+key)
        path=Path(item['path']);require(path.is_file(),'Missing asset: '+key)
        require(digest(path)==item['sha256'],'Asset hash mismatch: '+key);paths[key]=path
    audit=read_json(paths['chemical_audit'])
    require(audit.get('training_approved') is True,'Chemical audit has not approved training')
    require(audit.get('unresolved_identity_errors')==0,'Unresolved chemical identity errors')
    require(audit.get('native_reference_outer_purges_approved') is True,'Native reference outer-purge review is not approved')
    require(audit.get('audited_requests')==32421,'Chemical audit does not cover full32421')
    for key in ('raw_features','numeric_features','queue','id_map','cohorts'):
        require(audit.get('input_sha256',{}).get(key)==files[key]['sha256'],'Chemical audit input mismatch: '+key)
    for key in keys:
        if '_native_' in key or key.endswith('_oof'):
            require(audit.get('native_reference_prediction_sha256',{}).get(key)==files[key]['sha256'],'Reference review not bound to asset: '+key)
    with paths['queue'].open(encoding='utf-8-sig',newline='') as f:queue=list(csv.DictReader(f))
    require(len(queue)==32421,'Queue count mismatch')
    ids=[];smiles=[]
    for row in queue:
        s=row['SMILES'];i=row['request_id']
        require(bool(s) and not any(c.isspace() for c in s),'Whitespace or empty request SMILES')
        require(hashlib.sha256(s.encode()).hexdigest()==i,'request_id does not identify exact SMILES')
        ids.append(i);smiles.append(s)
    require(len(set(ids))==len(ids)==len(set(smiles)),'Duplicate queue identity')
    with paths['raw_features'].open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);raw_fields=reader.fieldnames;raw=[r['raw_smiles'] for r in reader]
    require(raw_fields and len(raw_fields)==len(set(raw_fields)),'Invalid raw CSV headers')
    require({'raw_smiles','smiles'}<=set(raw_fields) and len(raw_fields)-2==120,'Expected120 raw endpoint columns')
    require(len(raw)==32421 and set(raw)==set(smiles),'Raw result coverage mismatch or duplicate')
    with paths['numeric_features'].open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);numeric_fields=reader.fieldnames;numeric=list(reader)
    require(numeric_fields and len(numeric_fields)==len(set(numeric_fields)),'Invalid numeric CSV headers')
    columns=sorted(c for c in numeric_fields if c.startswith('ADMETLAB::'))
    require(len(columns)==120,'Expected120 numeric ADMETlab features')
    require(set(columns)==set(m.get('feature_columns',[])),'Feature column contract mismatch')
    require(len(numeric)==32421 and len({r['request_id'] for r in numeric})==32421,'Numeric result count/identity mismatch')
    known=dict(zip(ids,smiles))
    require(all(known.get(r['request_id'])==r['SMILES'] for r in numeric),'Numeric row/SMILES mismatch')
    return m,paths,columns
