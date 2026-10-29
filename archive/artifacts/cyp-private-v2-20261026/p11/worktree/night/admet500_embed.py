"""Frozen encoder inference in a process without LightGBM's OpenMP runtime."""
import faulthandler
faulthandler.enable()
import sys,json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from chemprop import data,nn

if __name__=='__main__':
    source,checkpoint,destination=map(Path,sys.argv[1:])
    torch.set_num_threads(2)
    frame=pd.read_csv(source,usecols=['SMILES'])
    ck=torch.load(checkpoint,map_location='cpu',weights_only=False)
    encoder=nn.BondMessagePassing(**ck['hyper_parameters']);encoder.load_state_dict(ck['state_dict']);encoder.eval()
    aggregate=nn.MeanAggregation()
    dataset=data.MoleculeDataset([data.MoleculeDatapoint.from_smi(s) for s in frame.SMILES])
    loader=data.build_dataloader(dataset,batch_size=32,shuffle=False,num_workers=0)
    chunks=[]
    with torch.inference_mode():
        for batch in loader:chunks.append(aggregate(encoder(batch.bmg),batch.bmg.batch).numpy())
    result=np.concatenate(chunks);assert result.shape==(len(frame),2048) and np.isfinite(result).all()
    np.save(destination,result)
    print(json.dumps({'event':'isolated_frozen_encoder_exported','shape':list(result.shape)}),flush=True)
