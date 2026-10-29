"""Freeze a terminal original run for the single authorized resume; no inference/launch."""
from pathlib import Path
import json,hashlib,sqlite3,shutil
import numpy as np
p=Path(__file__).parent;old=p.parent/'p9b';out=p/'prior-snapshot';runid='f870d574-9ed7-4b77-b0c6-e42ec35509dd';con=sqlite3.connect('file:/Users/adeliyaleleytner/.cache/cyp-inhibition/orx-store/orx.db?mode=ro',uri=True);status,source=con.execute('select status,commit_sha from runs where id=?',(runid,)).fetchone();assert status in ['done','failed'],status;assert source=='8ab23c4d9513919e71dd50f6e25b0cbc75eb42df';sup=json.load(open(old/'results/supervisor.json'));assert sup['returncode'] in [0,124],sup
out.mkdir(exist_ok=False);paths={'config':old/'worktree/p9b_config.json','supervisor':old/'results/supervisor.json','outcomes':old/'results/row-outcomes.jsonl','features':old/'results/successful-embeddings-progress.npy','indices':old/'results/successful-indices-progress.npy'};paths.update({f'coords_{i}':f for i,f in enumerate(sorted((old/'results').glob('coordinates-through-*.npz')))})
if (old/'results/COMPLETE.json').exists():paths['complete']=old/'results/COMPLETE.json'
records={}
for key,sourcepath in paths.items():
 target=out/sourcepath.name;shutil.copy2(sourcepath,target);originalhash=hashlib.sha256(sourcepath.read_bytes()).hexdigest();assert originalhash==hashlib.sha256(target.read_bytes()).hexdigest();records[key]={'path':str(target),'sha256':originalhash,'original_path':str(sourcepath)}
vectors=np.load(records['features']['path']);idx=np.load(records['indices']['path']);assert vectors.shape==(len(idx),256) and vectors.dtype==np.float32 and np.isfinite(vectors).all();coords=set()
for key,r in records.items():
 if key.startswith('coords_'):
  f=np.load(r['path']);coords|={int(k[2:]) for k in f.files if k.startswith('z_')}
assert set(idx.tolist())<=coords,'checkpointvectorsmissingcoordinates';manifest={'terminal':True,'status':status,'run_id':runid,'source_commit':source,'source_returncode':sup['returncode'],'files':records,'persisted_successful_embeddings':len(idx),'persisted_coordinate_rows':len(coords),'remaining_missing_or_failed_rows':5655-len(idx),'snapshot_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};m=out/'manifest.json';m.write_text(json.dumps(manifest,indent=2)+'\n');c=json.load(open(p/'worktree/p9_resume_config.json'));assert c['previous_snapshot'] is None;c['previous_snapshot']={'path':str(m),'sha256':hashlib.sha256(m.read_bytes()).hexdigest()};(p/'worktree/p9_resume_config.json').write_text(json.dumps(c,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items() if k!='files'}));print('Prior snapshot pinned. Commit before ORX resume launch.')
