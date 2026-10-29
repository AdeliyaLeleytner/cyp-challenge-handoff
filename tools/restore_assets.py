#!/usr/bin/env python3
"""Restore private release assets with size/SHA256 checks; never execute archived code."""
import argparse,hashlib,json,os,shutil,subprocess,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def destination(rel):
 p=(ROOT/rel).resolve()
 if not p.is_relative_to(ROOT):raise ValueError('Unsafe manifest path')
 return p
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--download',action='store_true');a.add_argument('--list',action='store_true');a.add_argument('--prefix',default='');a.add_argument('--cache',type=Path,default=ROOT/'.asset-cache');v=a.parse_args()
 meta=json.loads((ROOT/'manifest/releases.json').read_text())
 rows=[json.loads(s) for s in (ROOT/'manifest/files.jsonl').read_text().splitlines()]
 rows=[r for r in rows if r['storage']=='release' and r['path'].startswith(v.prefix)]
 needed={r['sha256'] for r in rows if not destination(r['path']).exists() or digest(destination(r['path']))!=r['sha256']}
 packs=[p for p in meta['packs'] if needed.intersection(p['objects'])]
 print(json.dumps({'selected_paths':len(rows),'missing_unique_objects':len(needed),'required_packs':len(packs),'download_bytes':sum(p['size'] for p in packs)},indent=2))
 if not v.download:
  if not v.list:print('Use --download to restore, or --prefix to select a subdirectory.')
  return
 v.cache.mkdir(parents=True,exist_ok=True)
 byhash={}
 for r in rows:byhash.setdefault(r['sha256'],[]).append(r)
 for pack in packs:
  path=v.cache/pack['name']
  if path.exists() and (path.stat().st_size!=pack['size'] or digest(path)!=pack['sha256']):path.unlink()
  if not path.exists():subprocess.run(['gh','release','download',meta['tag'],'--repo',meta['repo'],'--pattern',pack['name'],'--dir',str(v.cache)],check=True)
  if path.stat().st_size!=pack['size'] or digest(path)!=pack['sha256']:raise ValueError('Pack checksum mismatch: '+pack['name'])
  with tarfile.open(path,'r:gz') as tf:
   for member in tf:
    sha=member.name
    if sha not in needed:continue
    if not member.isfile() or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):raise ValueError('Unsafe pack member')
    dest=destination(byhash[sha][0]['path']);dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dest.parent,delete=False) as tmp:
     tmpname=Path(tmp.name)
     with tf.extractfile(member) as inp:shutil.copyfileobj(inp,tmp,8*1024*1024)
    if digest(tmpname)!=sha:tmpname.unlink();raise ValueError('Object checksum mismatch')
    os.replace(tmpname,dest);os.chmod(dest,byhash[sha][0]['mode'])
    for row in byhash[sha][1:]:
     other=destination(row['path']);other.parent.mkdir(parents=True,exist_ok=True)
     if other.exists():
      if digest(other)==sha:continue
      raise ValueError('Refusing to replace changed file: '+str(other))
     try:os.link(dest,other)
     except OSError:shutil.copy2(dest,other)
    needed.remove(sha)
  path.unlink();print('Restored '+pack['name'],flush=True)
 if needed:raise ValueError('Missing objects: '+str(len(needed)))
 exclude=ROOT/'.git/info/exclude'
 if exclude.parent.exists():
  existing=exclude.read_text() if exclude.exists() else ''
  added=['/'+r['path'] for r in rows if '/'+r['path'] not in existing.splitlines()]
  with exclude.open('a') as f:f.write('\n'+'\n'.join(added)+'\n')
 print('Restoration complete; run python3 tools/verify_handoff.py --all')
if __name__=='__main__':main()
