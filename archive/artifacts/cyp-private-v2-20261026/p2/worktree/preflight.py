"""One forward/backward compatibility check; no optimizer or parameter update."""
import json,time
from pathlib import Path
import numpy as np
import torch
from chemprop import data
from modeling import datasets,build
cfg=json.loads(Path('config.json').read_text());torch.manual_seed(cfg['seed']);torch.set_num_threads(6)
tr,va,td,vd,scaler,feat=datasets();model,info=build(scaler,cfg)
assert torch.backends.mps.is_available()
loader=data.build_dataloader(td,batch_size=cfg['batch_size'],num_workers=0,shuffle=False)
batch=next(iter(loader));bmg,Vd,Xd,y,w,lt,gt=batch
model.train();model.to('mps');bmg.to('mps');y=y.to('mps');mask=y.isfinite()
start=time.perf_counter();pred=model(bmg,Vd,Xd);loss=(pred-y.nan_to_num()).square()[mask].mean();loss.backward();torch.mps.synchronize()
assert torch.isfinite(loss) and torch.isfinite(pred).all()
assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())
info.update({'batch':len(y),'forward_backward_seconds':time.perf_counter()-start,'loss':float(loss.detach().cpu()),
             'mps_allocated_bytes':torch.mps.current_allocated_memory(),'optimizer_steps':0,
             'input_train_count':len(tr),'input_validation_count':len(va),'scaler_means':scaler.mean_.tolist()})
print(json.dumps(info,indent=2),flush=True)
Path('preflight-result.json').write_text(json.dumps(info,indent=2)+'\n')
