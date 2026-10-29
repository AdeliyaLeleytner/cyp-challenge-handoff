from pathlib import Path
import json,hashlib,numpy as np,pandas as pd

def check(stage):
 sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();m=json.loads((stage/'asset-manifest.json').read_text())
 for rel,h in m['files'].items():assert sha(stage/rel)==h
 old=np.load(stage/'features/original.npy');new=np.load(stage/'features/repaired.npy');repair=json.loads((stage/'features/repair-manifest.json').read_text());keep=[j for j in range(120) if j not in repair['affected_column_indices']];assert old.shape==new.shape==(31641,120) and np.isfinite(new).all();assert np.array_equal(old[:,keep],new[:,keep]);assert int((old!=new).sum())==170 and int((old!=new).any(1).sum())==85
 d=pd.read_csv(stage/'common/table.csv');r=pd.read_csv(stage/'features/rows.csv');assert d.molecule_name.tolist()==r.molecule_name.tolist() and d.request_id.tolist()==r.request_id.tolist();assert d.request_id.is_unique
 print(json.dumps({'P7R_stage':'PASS','rows':31641,'changed_raw_cells':170,'changed_raw_rows':85,'unchanged_features':118,'model_fits':0}))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,default=Path('/workspace/p7r/stage'));a=p.parse_args();check(a.stage)
