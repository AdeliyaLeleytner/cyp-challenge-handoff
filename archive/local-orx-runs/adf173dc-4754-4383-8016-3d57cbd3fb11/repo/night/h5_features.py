"""Frozen ADME600 cache joined by exact official ID, SMILES and row order."""
import json
from pathlib import Path
import numpy as np,pandas as pd
from .admet_full_contract import require,digest

def validate_embedding_assets(cfg):
 assets=cfg['embedding_assets']
 require(set(assets)=={'adme_matrix','adme_source_rows','adme_checkpoint','adme_preparation_record','adme_producer_source','adme_provenance','adme_runtime_lock'},'Unexpected embedding asset set')
 for name,item in assets.items():require(digest(item['path'])==item['sha256'],'Embedding asset changed:'+name)
 proof=json.loads(Path(assets['adme_provenance']['path']).read_text())
 require(proof['rows']==4905 and proof['dimensions']==600 and proof['embeddings_for_blind750_available_in_this_stage'] is False,'Embedding scope changed')
 require(proof['matrix_sha256']==assets['adme_matrix']['sha256'] and proof['row_source_sha256']==assets['adme_source_rows']['sha256'] and proof['checkpoint_sha256']==assets['adme_checkpoint']['sha256'],'Embedding provenance hash mismatch')
 require(proof['historical_runtime_lock_sha256']==assets['adme_runtime_lock']['sha256'],'Historical encoder runtime evidence changed')
 return assets,proof

def build_views(data,admet,cfg):
 assets,proof=validate_embedding_assets(cfg)
 rows=pd.read_csv(assets['adme_source_rows']['path']);embedding=np.load(assets['adme_matrix']['path'],allow_pickle=False)
 require(rows.Molecule_Name.tolist()==data.Molecule_Name.tolist(),'Embedding IDs/order differ from official model rows')
 require(rows.SMILES.tolist()==data.SMILES.tolist(),'Embedding SMILES/order differ from official model rows')
 require(embedding.shape==(4905,600) and embedding.dtype==np.float32 and np.isfinite(embedding).all(),'Invalid frozen ADME matrix')
 require(admet.shape==(4905,120) and np.isfinite(admet).all(),'Invalid official ADMET view')
 # Lossless common precision before identical train-only scaling; final model input remainsfloat32.
 a=embedding.astype(np.float64);b=np.concatenate([a,admet.astype(np.float64)],axis=1)
 require(np.array_equal(a,b[:,:600]),'Matched representation prefix changed')
 return {'adme':a,'adme_admet':b},{'embedding_rows':4905,'blind_embedding_rows':0,'views':{'adme':600,'adme_admet':720},'order':'ADME600 then the120 sorted declared ADMET columns','provenance':proof}
