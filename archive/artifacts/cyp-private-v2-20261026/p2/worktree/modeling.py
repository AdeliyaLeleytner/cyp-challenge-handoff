from pathlib import Path
import hashlib,json,urllib.request
import numpy as np
import pandas as pd
import torch
from chemprop import data,featurizers,nn,models

CYP=['CYP1A2','CYP2C9','CYP2D6','CYP3A4']
COLS=[x+'_pIC50_direct_inhibition' for x in CYP]
WEIGHT_SHA='c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651'
WEIGHT_URL='https://zenodo.org/records/15460715/files/chemeleon_mp.pt'

def weight_path():
    p=Path.home()/'.cache/cyp-inhibition/chemeleon_mp.pt'
    if not p.exists():
        p.parent.mkdir(parents=True,exist_ok=True);urllib.request.urlretrieve(WEIGHT_URL,p)
    assert hashlib.sha256(p.read_bytes()).hexdigest()==WEIGHT_SHA
    return p

def datasets():
    manifest=json.loads(Path('data/manifest.json').read_text())
    for f,sha in manifest['sha256'].items():assert hashlib.sha256((Path('data')/f).read_bytes()).hexdigest()==sha,(f,'hash mismatch')
    train=pd.read_csv('data/train.csv');val=pd.read_csv('data/validation.csv')
    feat=featurizers.SimpleMoleculeMolGraphFeaturizer()
    def make(df):
        y=df[COLS].to_numpy(np.float32)
        ds=data.MoleculeDataset([data.MoleculeDatapoint.from_smi(s,y_) for s,y_ in zip(df.SMILES,y)],feat)
        ds.cache=True
        return ds
    td=make(train);scaler=td.normalize_targets();vd=make(val);vd.normalize_targets(scaler)
    assert np.allclose(scaler.mean_,np.nanmean(train[COLS].to_numpy(),axis=0),atol=1e-5)
    return train,val,td,vd,scaler,feat

def build(scaler,cfg):
    ck=torch.load(weight_path(),weights_only=True,map_location='cpu')
    assert {'hyper_parameters','state_dict'}<=ck.keys()
    mp=nn.BondMessagePassing(**ck['hyper_parameters'])
    result=mp.load_state_dict(ck['state_dict'],strict=True)
    assert not result.missing_keys and not result.unexpected_keys
    feat=featurizers.SimpleMoleculeMolGraphFeaturizer()
    from rdkit import Chem
    mg=feat(Chem.MolFromSmiles('CCOc1ccccc1'))
    assert mg.V.shape[1]==ck['hyper_parameters']['d_v']
    assert mg.E.shape[1]==ck['hyper_parameters']['d_e']
    ffn=nn.RegressionFFN(n_tasks=4,input_dim=mp.output_dim,hidden_dim=300,n_layers=1,dropout=0,
                          output_transform=nn.UnscaleTransform.from_standard_scaler(scaler))
    model=models.MPNN(mp,nn.MeanAggregation(),ffn,batch_norm=False,
        warmup_epochs=cfg['warmup_epochs'],init_lr=cfg['init_lr'],max_lr=cfg['max_lr'],final_lr=cfg['final_lr'])
    assert all(p.requires_grad for p in model.message_passing.parameters())
    info={'weight_sha256':WEIGHT_SHA,'weight_source':WEIGHT_URL,'encoder_hyperparameters':{k:v for k,v in ck['hyper_parameters'].items() if isinstance(v,(str,int,float,bool,type(None)))},
          'encoder_tensors_loaded':len(ck['state_dict']),'trainable_parameters':sum(p.numel() for p in model.parameters() if p.requires_grad),
          'encoder_parameters':sum(p.numel() for p in mp.parameters()),'output_tasks':4}
    return model,info
