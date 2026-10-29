from pathlib import Path
import os,subprocess,json,hashlib,shutil
os.umask(0o077);ROOT=Path(__file__).resolve().parent;BASE=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-briford-reproduction-20261024/remote');DEST=ROOT/'incumbent-artifact-copy';records={}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
files=[p for p in (BASE/'assets/prepared').glob('*') if p.is_file()]+[BASE/'requirements.lock.txt']+[BASE/'finalized'/x for x in ['config.json','final_complete.json','placement.json']]
for p in files:
 rel=Path('prepared')/p.name if p.parent.name=='prepared' else Path(p.name);dst=DEST/rel;dst.parent.mkdir(exist_ok=True,parents=True)
 if not dst.exists():shutil.copy2(p,dst);dst.chmod(0o600)
 assert sha(dst)==sha(p);records[str(rel)]={'source':str(p),'sha256':sha(p),'private_copy':str(dst)}
repo='/Users/adeliyaleleytner/.local/share/openresearch/projects/cyp-chemeleon-baseline-20261023'
for name,commit in [('original-training','d4c1a31c2952f8d933ce035a1cab04417f46cb76'),('original-serving','38fe110e5a8d17a7bfb48ac78fe12e425da8deeb')]:
 p=DEST/(name+'.tar.gz')
 if not p.exists():subprocess.run(['git','-C',repo,'archive','--format=tar.gz','--output='+str(p),commit],check=True)
 records[name]={'git_commit':commit,'private_archive':str(p),'sha256':sha(p)}
(ROOT/'incumbent_preservation.json').write_text(json.dumps({'model_checkpoint_manifest':'lineage_manifest.json','source_and_data':records,'public_writes':False,'new_training':False},indent=2)+'\n');print(json.dumps({'preserved_data_and_runtime_files':len(files),'private_source_archives':2,'no_model_changes':True}))
