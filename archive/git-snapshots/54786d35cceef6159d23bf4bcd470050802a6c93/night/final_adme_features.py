"""H5 final view assembly. No embedding generation, encoder substitution or downloads."""
from pathlib import Path
import json
from .admet_full_contract_v1 import require,digest
ENCODER_RUNTIME={'chemprop':'2.2.1','lightning':'2.5.5','torch':'2.8.0+cu128','rdkit':'2026.9.1','numpy':'2.2.6'}

def validate_training_assets(cfg,model):
    expected=model.get('embedding_assets_sha256');assets=cfg.get('embedding_assets',{})
    require(expected and set(assets)==set(expected),'H5 training embedding assets must be explicitly pinned')
    for key,pin in expected.items():
        item=assets[key];require(item.get('sha256')==pin and Path(item['path']).is_file() and digest(item['path'])==pin,'H5 embedding source changed: '+key)
    return assets

def load_blind_bank(cfg,model,blind,query_request_sha,official_test_sha,binding_kind="selected_query"):
    import numpy as np
    import pandas as pd
    import hashlib
    path=cfg.get('adme_blind_embedding_manifest');sha=cfg.get('adme_blind_embedding_manifest_sha256')
    require(path and sha and digest(path)==sha,'H5 query requires verified750 ADME embeddings; no alternative derivation')
    m=json.loads(Path(path).read_text());require(m.get('schema_version')==1 and m.get('producer_orx_run_id') and m.get('producer_commit'),'Blind embedding producer provenance missing')
    field='selection_query_request_sha256' if binding_kind=='selected_query' else 'declared_final_recipe_sha256'
    require(binding_kind in ('selected_query','final_recipe') and m.get(field)==query_request_sha,'Blind embedding binding belongs to another selected query/final recipe')
    require(set(m['files'])=={'matrix','rows','receipt'},'Blind embedding artifact set mismatch')
    paths={}
    for key,item in m['files'].items():
        p=Path(item['path']);require(p.is_file() and digest(p)==item['sha256'],'Blind embedding artifact changed: '+key);paths[key]=p
    receipt=json.loads(paths['receipt'].read_text());pins=model['embedding_assets_sha256']
    require(receipt.get('status')=='complete' and receipt.get('approved') is True and receipt.get('expected_rows')==750 and receipt.get('expected_dimensions')==600,'Blind ADME bank incomplete or unverified')
    for field,key in [('checkpoint_sha256','adme_checkpoint'),('source_producer_sha256','adme_producer_source'),('historical_runtime_lock_sha256','adme_runtime_lock')]:require(receipt.get(field)==pins[key],'Blind encoder provenance changed: '+field)
    require(receipt.get('official_test_sha256')==official_test_sha,'Blind embedding input snapshot changed')
    require(receipt.get('actual_runtime')==ENCODER_RUNTIME==receipt.get('required_runtime'),'Blind encoder runtime differs from historical producer')
    protocol='MPNN.load_from_file.eval; SimpleMoleculeMolGraphFeaturizer; MoleculeDataset from exact official SMILES; DataLoader batch256 shuffleFalse drop_lastFalse; torch.inference_mode; model.fingerprint(bmg,Vd,Xd); concatenate in original order'
    require(receipt.get('protocol')==protocol and receipt.get('training_labels_read_by_encoder') is False,'Blind fingerprint protocol changed')
    require(receipt.get('producer_run_id')==m['producer_orx_run_id'] and receipt.get('producer_commit')==m['producer_commit'],'Blind producer receipt identity changed')
    require(receipt.get('output_matrix_sha256')==m['files']['matrix']['sha256'] and receipt.get('shape_verified') is True and receipt.get('all_finite') is True,'Blind matrix verification missing')
    rows=pd.read_csv(paths['rows']);require(rows.Molecule_Name.tolist()==blind.Molecule_Name.tolist() and rows.SMILES.tolist()==blind.SMILES.tolist() and rows.request_id.tolist()==blind.request_id.tolist(),'Blind embedding ID/SMILES/order differs from original official inputs')
    identity=hashlib.sha256(json.dumps(blind[['Molecule_Name','SMILES']].to_dict('records'),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    require(receipt.get('exact_input_ids_smiles_order_sha256')==identity==receipt.get('output_ids_smiles_order_sha256'),'Blind ordered identity proof changed')
    array=np.load(paths['matrix'],allow_pickle=False);require(array.shape==(750,600) and array.dtype==np.float32 and np.isfinite(array).all(),'Blind ADME matrix shape/dtype/finiteness invalid')
    return array,{'kind':'verified_ADME600_query','manifest_sha256':sha,'matrix_sha256':m['files']['matrix']['sha256'],'receipt_sha256':m['files']['receipt']['sha256'],'encoder_checkpoint_sha256':pins['adme_checkpoint'],'training_matrix_sha256':pins['adme_matrix'],'encoder_producer_source_sha256':pins['adme_producer_source'],'query_request_sha256':query_request_sha}

def build_views(train,blind,admet,cfg,phase,query_request_sha=None,official_test_sha=None,binding_kind="selected_query"):
    import numpy as np
    from .h5_features import build_views as historical_views
    model=cfg['expected_tabpfn_model_contract'];validate_training_assets(cfg,model)
    views,proof=historical_views(train,admet[:4905],cfg)
    extra={'kind':'cached4905_ADME600_only','blind_embedding_rows':0,'embedding_assets_sha256':model['embedding_assets_sha256']}
    if phase=='query':
        array,extra=load_blind_bank(cfg,model,blind,query_request_sha,official_test_sha,binding_kind)
        a=np.concatenate([views['adme'],array.astype(np.float64)],axis=0)
        b=np.concatenate([a,admet.astype(np.float64)],axis=1)
        require(np.array_equal(a[:4905],views['adme']) and np.array_equal(b[:4905],views['adme_admet']),'Query assembly altered training representation')
        views={'adme':a,'adme_admet':b}
    return views,extra
