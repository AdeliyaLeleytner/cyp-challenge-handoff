"""Offline pinned Uni-Mol2 84M structure-only CLS bank for ORX.

Uses unmodified model/graph/padding modules from a verified toolkit checkout, in
an isolated namespace. Training APIs, automatic downloads, silent atom cropping,
and the toolkit's 2D/zero conformer fallbacks are not invoked.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import importlib
import importlib.metadata
import json
import logging
import os
import subprocess
import sys
import types
import warnings
import numpy as np
import pandas as pd

TOOLKIT_REPOSITORY='https://github.com/deepmodeling/unimol_tools'
TOOLKIT_COMMIT='670afbd3144b58caef1d76cc618ddfeaecab8424'
MODEL_REPOSITORY='dptech/Uni-Mol2'
MODEL_REVISION='bf37d253c0f5ac61f468137eb00059978a104ff0'
MODEL_FILE='modelzoo/84M/checkpoint.pt'
MODEL_BYTES=336632021
MODEL_SHA256='5b9241630f1cf0b173fb06d1e76096e5daf5f91c3e51b066ba69524dafe60e35'
MODEL_DIM=768
SOURCE_FILES=['config/model_config.py','utils/util.py','data/dictionary.py','data/conformer.py',
              'models/transformersv2.py','models/unimolv2.py']
DEFAULT_CONFIG={'seed':42,'batch_size':8,'conformer_workers':4,'max_heavy_atoms':256,
                'embedding_timeout_seconds':30,'embedding_max_iterations':1000,
                'forcefield_max_iterations':200,'device':'cuda','precision':'float32'}

class ExtractionFailure(RuntimeError):
    def __init__(self,message,audit):
        super().__init__(message);self.audit=audit

def _sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def _atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
    temp.replace(path)

def _verify_assets(toolkit_root,checkpoint):
    root=Path(toolkit_root).resolve();checkpoint=Path(checkpoint).resolve()
    head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if head!=TOOLKIT_COMMIT:raise ValueError('Uni-Mol toolkit checkout must match the pinned commit exactly')
    sources={}
    for relative in SOURCE_FILES:
        path=root/'unimol_tools'/relative
        committed=subprocess.check_output(['git','-C',str(root),'show',f'{TOOLKIT_COMMIT}:unimol_tools/{relative}'])
        actual=path.read_bytes()
        if actual!=committed:raise ValueError(f'Modified toolkit source: {relative}')
        sources[relative]=hashlib.sha256(actual).hexdigest()
    if checkpoint.stat().st_size!=MODEL_BYTES or _sha(checkpoint)!=MODEL_SHA256:
        raise ValueError('Uni-Mol2 84M checkpoint size/SHA256 mismatch')
    return {'repository':MODEL_REPOSITORY,'revision':MODEL_REVISION,'file':MODEL_FILE,
        'checkpoint_path':str(checkpoint),'checkpoint_sha256':MODEL_SHA256,'checkpoint_bytes':MODEL_BYTES,
        'toolkit_repository':TOOLKIT_REPOSITORY,'toolkit_commit':head,'toolkit_source_sha256':sources}

def _namespace(name,path):
    module=types.ModuleType(name);module.__path__=[str(path)];module.__package__=name
    sys.modules[name]=module;return module

def _import_pinned(toolkit_root):
    """Import only the audited dependency surface; never package training __init__."""
    prefix='_cyp_unimol2_'+TOOLKIT_COMMIT[:12]
    if prefix in sys.modules:raise RuntimeError('Pinned Uni-Mol namespace already loaded; use a fresh worker process')
    root=Path(toolkit_root).resolve()/'unimol_tools'
    _namespace(prefix,root)
    for sub in ['config','models','data','utils','weights']:_namespace(prefix+'.'+sub,root/sub)
    config=importlib.import_module(prefix+'.config.model_config')
    sys.modules[prefix+'.config'].MODEL_CONFIG=config.MODEL_CONFIG
    sys.modules[prefix+'.config'].MODEL_CONFIG_V2=config.MODEL_CONFIG_V2
    utility=importlib.import_module(prefix+'.utils.util')
    utils=sys.modules[prefix+'.utils'];utils.logger=logging.getLogger('cyp.unimol84')
    for name in ['pad_1d_tokens','pad_2d','pad_coords']:setattr(utils,name,getattr(utility,name))
    def offline_only(*args,**kwargs):raise RuntimeError('Automatic Uni-Mol weight/dictionary download is forbidden')
    weights=sys.modules[prefix+'.weights']
    for name in ['get_weight_dir','weight_download','weight_download_v2']:setattr(weights,name,offline_only)
    # conformer.py suppresses warnings and RDKit logging globally at import. Undo
    # those diagnostic side effects; only its graph conversion is used below.
    with warnings.catch_warnings():
        conformer=importlib.import_module(prefix+'.data.conformer')
    from rdkit import RDLogger
    RDLogger.EnableLog('rdApp.warning');RDLogger.EnableLog('rdApp.error')
    model=importlib.import_module(prefix+'.models.unimolv2')
    return model.UniMolV2Model,conformer.mol2unimolv2

def _seed(base,identifier,attempt=0):
    payload=f'{base}:{identifier}:{attempt}'.encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:4],'big')%2147483647

def generate_conformer(item,config):
    """Strict RDKit3D generation. Retry explicit random coordinates, never2D/zeros."""
    from rdkit import Chem
    from rdkit.Chem import AllChem
    identifier,smiles=item
    row={'Molecule_Name':identifier,'status':'failed','attempts':[], 'smiles_sha256':hashlib.sha256(smiles.encode()).hexdigest()}
    try:
        original=Chem.MolFromSmiles(smiles)
        if original is None:raise ValueError('Invalid SMILES')
        heavy=Chem.RemoveAllHs(original);n=heavy.GetNumAtoms()
        row.update(input_atoms=original.GetNumAtoms(),heavy_atoms=n,
                   fragments=len(Chem.GetMolFrags(heavy)),hydrogen_policy='Uni-Mol2 removes all H; no heavy atoms or fragments removed')
        if n<1:raise ValueError('No non-hydrogen atoms')
        if n>int(config['max_heavy_atoms']):raise ValueError(f'Atom limit exceeded: {n}; cropping is forbidden')
        mol=None
        for attempt,random_coordinates in enumerate([False,True]):
            candidate=Chem.AddHs(Chem.Mol(heavy))
            params=AllChem.ETKDGv3();params.randomSeed=_seed(config['seed'],identifier,attempt)
            params.useRandomCoords=random_coordinates;params.numThreads=1
            params.maxIterations=int(config['embedding_max_iterations'])
            if not hasattr(params,'timeout'):raise RuntimeError('Pinned RDKit embedding timeout API is unavailable')
            params.timeout=int(config['embedding_timeout_seconds'])
            code=int(AllChem.EmbedMolecule(candidate,params))
            row['attempts'].append({'random_seed':params.randomSeed,'random_coordinates':random_coordinates,'return_code':code})
            if code==0:mol=candidate;break
        if mol is None:raise RuntimeError('Both bounded ETKDG3D attempts failed')
        if AllChem.MMFFHasAllMoleculeParams(mol):
            optimization={'forcefield':'MMFF94','return_code':int(AllChem.MMFFOptimizeMolecule(mol,maxIters=int(config['forcefield_max_iterations'])))}
        elif AllChem.UFFHasAllMoleculeParams(mol):
            optimization={'forcefield':'UFF','return_code':int(AllChem.UFFOptimizeMolecule(mol,maxIters=int(config['forcefield_max_iterations'])))}
        else:optimization={'forcefield':None,'return_code':None,'note':'No complete forcefield parameters; successful ETKDG coordinates retained.'}
        # A valid, finite embedded conformer can be retained even if forcefield
        # optimization reaches its iteration limit; record this, do not call it convergence.
        heavy3d=Chem.RemoveAllHs(mol)
        xyz=np.asarray(heavy3d.GetConformer().GetPositions(),dtype=np.float32)
        if heavy3d.GetNumAtoms()!=n or xyz.shape!=(n,3):raise RuntimeError('Heavy-atom count/coordinate mismatch')
        if not heavy3d.GetConformer().Is3D() or not np.isfinite(xyz).all():raise RuntimeError('No valid finite3D conformer')
        if n>1 and np.max(np.linalg.norm(xyz-xyz[0],axis=1))<1e-6:raise RuntimeError('Degenerate all-coincident conformer')
        row.update(status='ok',optimization=optimization,
            coordinates_sha256=hashlib.sha256(xyz.astype('<f4',copy=False).tobytes()).hexdigest(),
            zero_z_axis=bool(np.all(xyz[:,2]==0)),coordinate_rank=int(np.linalg.matrix_rank(xyz-xyz.mean(axis=0))),
            geometry_note='Planar/single-atom geometries are not rejected solely for zero z or low rank; ETKDG success and3D flag are required.')
        return heavy3d,row
    except Exception as exc:
        row.update(error_type=type(exc).__name__,error=str(exc))
        return None,row

def prepare_conformers(frame,config,provider=None):
    provider=provider or generate_conformer
    pairs=list(zip(frame.Molecule_Name.astype(str),frame.SMILES.astype(str)))
    workers=int(config['conformer_workers'])
    if workers<1:raise ValueError('conformer_workers must be positive')
    def collect(iterator):
        results=[]
        for result in iterator:
            results.append(result)
            if len(results)%250==0 or len(results)==len(pairs):
                print(json.dumps({'event':'unimol_conformers','completed':len(results),'total':len(pairs),
                    'failed_so_far':sum(row['status']!='ok' for _,row in results)}),flush=True)
        return results
    if workers==1:results=collect(provider(item,config) for item in pairs)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results=collect(pool.map(lambda item:provider(item,config),pairs))
    mols,rows=zip(*results)
    if [row['Molecule_Name'] for row in rows]!=[p[0] for p in pairs]:raise RuntimeError('Conformer provider changed ID alignment')
    return list(mols),list(rows)

class PinnedBackend:
    def __init__(self,toolkit_root,checkpoint,config):
        import torch
        if torch.__version__.split('+')[0]!='2.8.0' or torch.version.cuda!='12.8':
            raise RuntimeError('Production extraction requires separate Torch2.8.0/CUDA12.8 environment')
        if config['device']!='cuda' or not torch.cuda.is_available():raise RuntimeError('Requested CUDA inference is unavailable; no silent CPU fallback')
        if config['precision']!='float32':raise ValueError('84M control is pinned to float32 extraction')
        model_type,self.featurize=_import_pinned(toolkit_root)
        # Avoid the upstream implicit loader, which does not audit partial loads
        # and inherits Torch2.8 weights_only default changes.
        self.model=model_type(output_dim=1,model_size='84m',load_pretrained=False)
        checkpoint_data=torch.load(checkpoint,map_location='cpu',weights_only=False)
        state=checkpoint_data.get('model',checkpoint_data.get('model_state_dict',checkpoint_data))
        if not isinstance(state,dict) or not state:raise ValueError('Checkpoint lacks a model state dictionary')
        if any(k.startswith(('classification_head.','classification_heads.')) for k in state):
            raise ValueError('Unexpected downstream classifier head in pretrained checkpoint; review provenance')
        args=checkpoint_data.get('args')
        task=args.get('task') if isinstance(args,dict) else getattr(args,'task',None)
        if task and 'finetun' in str(task).lower():raise ValueError('Checkpoint reports a finetuning task')
        result=self.model.load_state_dict(state,strict=False)
        allowed_missing={'classification_head.out_proj.weight','classification_head.out_proj.bias'}
        if set(result.missing_keys)-allowed_missing or any(not k.startswith('lm_head.') for k in result.unexpected_keys):
            raise RuntimeError(f'Unreviewed checkpoint mismatch: missing={result.missing_keys}, unexpected={result.unexpected_keys}')
        self.audit={'loaded_backbone':True,'missing_unused_head_keys':result.missing_keys,
                    'unused_pretraining_head_keys':result.unexpected_keys,'checkpoint_task':str(task) if task else None,
                    'checkpoint_load':'weights_only=False for SHA256-verified official checkpoint only',
                    'torch_version':torch.__version__,'cuda_version':torch.version.cuda,'representation':'CLS token x[:,0,:]'}
        del checkpoint_data,state
        self.model.eval().to('cuda')
        for parameter in self.model.parameters():parameter.requires_grad_(False)
        if self.model.args.encoder_embed_dim!=MODEL_DIM:raise ValueError('Unexpected84M embedding dimension')
        self.torch=torch
    def encode(self,mols):
        features=[]
        for mol in mols:
            n=mol.GetNumAtoms()
            f=self.featurize(mol,max_atoms=n,remove_hs=True)
            if len(f['src_tokens'])!=n or f['src_coord'].shape!=(n,3) or f['atom_feat'].shape[0]!=n:
                raise RuntimeError('Toolkit featurization dropped/truncated atoms')
            features.append((f,np.zeros(1,dtype=np.float32)))
        batch,_=self.model.batch_collate_fn(features)
        batch={key:value.to('cuda') for key,value in batch.items()}
        with self.torch.inference_mode():output=self.model(**batch,return_repr=True,return_atomic_reprs=False)
        return output.detach().float().cpu().numpy()

def encode_bank(mols,rows,backend,batch_size):
    """Pure alignment layer; mock backends can exercise it without real inference."""
    if len(mols)!=len(rows) or not mols:raise ValueError('Molecule/audit row-count mismatch')
    if batch_size<1:raise ValueError('batch_size must be positive')
    if any(mol is None or row.get('status')!='ok' for mol,row in zip(mols,rows)):
        raise ValueError('Incomplete conformer bank; no rows may be dropped or imputed')
    result=np.empty((len(mols),MODEL_DIM),np.float32)
    for start in range(0,len(mols),batch_size):
        stop=min(start+batch_size,len(mols));values=np.asarray(backend.encode(mols[start:stop]),np.float32)
        if values.shape!=(stop-start,MODEL_DIM) or not np.isfinite(values).all():raise RuntimeError('Nonfinite/misaligned Uni-Mol CLS output')
        result[start:stop]=values
        if start//batch_size%25==0 or stop==len(mols):
            print(json.dumps({'event':'unimol_embeddings','completed':stop,'total':len(mols)}),flush=True)
    return result

def extract_features(frame,toolkit_root,checkpoint,config=None,audit_path=None):
    if set(config or {})-set(DEFAULT_CONFIG):raise ValueError('Unknown Uni-Mol84 extraction configuration keys')
    cfg=dict(DEFAULT_CONFIG);cfg.update(config or {})
    if int(cfg['embedding_max_iterations'])<1 or int(cfg['forcefield_max_iterations'])<1:raise ValueError('Iteration bounds must be positive')
    if int(cfg['batch_size'])<1 or int(cfg['max_heavy_atoms'])<1:raise ValueError('Invalid batch/atom limit')
    if int(cfg['embedding_timeout_seconds'])<1:raise ValueError('Embedding timeout must be positive')
    ids=frame.Molecule_Name.astype(str).tolist()
    if frame[['Molecule_Name','SMILES']].isna().any().any() or len(ids)!=len(set(ids)) or not ids:raise ValueError('Invalid molecule IDs/SMILES')
    asset=_verify_assets(toolkit_root,checkpoint)
    for dependency in ['torch','numpy','pandas','rdkit','scipy','addict','tqdm','numba']:
        importlib.metadata.version(dependency)
    import torch
    if torch.__version__.split('+')[0]!='2.8.0' or torch.version.cuda!='12.8' or not torch.cuda.is_available():
        raise RuntimeError('Require isolated Torch2.8.0/CUDA12.8 GPU environment before conformer generation')
    audit={'ids':ids,'config':cfg,'encoder_asset':asset,'failure_policy':'raise','status':'preparing',
        'n_rows':len(ids),'labels_used':False,'structures_only':True,'rows':[],
        'pretraining':{
            'claim':'Official public Uni-Mol2 model-zoo84M checkpoint, frozen self-supervised representation; no CYP adaptation performed.',
            'objectives':['masked atom tokens','coordinate denoising'],
            'paper':'https://arxiv.org/html/2406.14969v1#S3',
            'model_zoo':'https://github.com/deepmodeling/Uni-Mol/blob/90f52c41299a1a582da0f9765e9f87aa21faa16a/unimol2/README.md',
            'upstream_corpus_caveat':'Paper includes a19M Uni-Mol corpus sourced from ZINC15,ChEMBL,and a commercial database, plus ZINC20; do not claim entirely public upstream pretraining chemistry.',
            'model_card_limit':'Pinned HF README contains only MIT license metadata; pretraining interpretation also relies on official model-zoo linkage and paper.'},
        'adaptations':['Explicit ETKDGv3 conformers with bounded retries; no upstream2D/zero fallback.',
            'Hydrogens omitted as required by Uni-Mol2; all heavy atoms/fragments retained.',
            'Strict backbone checkpoint coverage rather than unchecked strict=False.',
            'Isolated imports of unmodified pinned core files; no training package initializer or auto-download.']}
    try:
        mols,rows=prepare_conformers(frame,cfg);audit['rows']=rows
        audit['failed_rows']=[row for row in rows if row['status']!='ok']
        if audit_path:_atomic_json(audit_path,audit)
        if audit['failed_rows']:raise ExtractionFailure('Conformer/atom-limit failures; complete bank not published',audit)
        backend=PinnedBackend(toolkit_root,checkpoint,cfg)
        audit['checkpoint_loading']=backend.audit
        X=encode_bank(mols,rows,backend,int(cfg['batch_size']))
        audit.update(status='completed',shape=list(X.shape),packages={name:importlib.metadata.version(name) for name in ['numpy','pandas','rdkit','scipy','torch','addict','tqdm']})
        try:audit['packages']['numba']=importlib.metadata.version('numba')
        except importlib.metadata.PackageNotFoundError:audit['packages']['numba']=None
        names=[f'unimol2_84m_cls_{i}' for i in range(MODEL_DIM)]
        if audit_path:_atomic_json(audit_path,audit)
        return X,names,audit
    except Exception as exc:
        audit.update(status='failed',error_type=type(exc).__name__,error=str(exc))
        if audit_path:_atomic_json(audit_path,audit)
        if isinstance(exc,ExtractionFailure):raise
        raise ExtractionFailure(str(exc),audit) from exc

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--molecules',required=True)
    parser.add_argument('--toolkit-root',required=True)
    parser.add_argument('--checkpoint',required=True)
    parser.add_argument('--asset-root',required=True)
    parser.add_argument('--asset-key',default='unimol2_84m_foundation')
    parser.add_argument('--feature-manifest',default='feature_manifest.json')
    parser.add_argument('--config')
    parser.add_argument('--audit-path',required=True)
    args=parser.parse_args()
    try:
        frame=pd.read_csv(args.molecules,usecols=['Molecule_Name','SMILES'],dtype=str)
        if len(frame)!=5655:raise ValueError(f'Expected complete5655-row official TRAIN+TEST bank, received{len(frame)}')
        cfg=json.loads(Path(args.config).read_text()) if args.config else {}
        X,names,audit=extract_features(frame,args.toolkit_root,args.checkpoint,cfg,args.audit_path)
        from .encoders import publish_features
        record=publish_features(frame,X,names,audit,args.asset_root,args.asset_key,args.feature_manifest)
        audit['published_asset']=record;_atomic_json(args.audit_path,audit)
        print(json.dumps({'status':'completed','asset_key':args.asset_key,'shape':list(X.shape),'failed_rows':0}),flush=True)
    except Exception as exc:
        audit=getattr(exc,'audit',{})
        audit.update(status='failed',error_type=type(exc).__name__,error=str(exc))
        _atomic_json(args.audit_path,audit)
        raise

if __name__=='__main__':main()
