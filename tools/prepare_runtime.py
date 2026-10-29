#!/usr/bin/env python3
"""Copy an archived subtree and rebase known local paths without changing evidence."""
import argparse,json,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--source',type=Path,required=True);a.add_argument('--output',type=Path,required=True);v=a.parse_args()
 src=v.source.resolve();dst=v.output.resolve()
 if dst.exists():raise SystemExit('Output already exists; choose a fresh runtime directory.')
 if not src.is_dir() or dst.is_relative_to(src):raise SystemExit('Invalid source/output')
 mappings=json.loads((ROOT/'manifest/path-map.json').read_text());pairs=sorted([(k,str(ROOT/w)) for k,w in mappings.items()],key=lambda x:len(x[0]),reverse=True)
 # References to this copied subtree should use the runtime copy; other assets stay in archive.
 pairs=[(k,str(dst)+new[len(str(src)):]) if new.startswith(str(src)+'/') or new==str(src) else (k,new) for k,new in pairs]
 shutil.copytree(src,dst);changes=[]
 for p in dst.rglob('*'):
  if not p.is_file() or p.stat().st_size>10_000_000:continue
  try:s=p.read_text()
  except (UnicodeError,OSError):continue
  t=s
  for old,new in pairs:t=t.replace(old,new)
  if t!=s:
   p.write_text(t);changes.append({'path':str(p.relative_to(dst)),'original_sha256':hashlib.sha256(s.encode()).hexdigest(),'runtime_sha256':hashlib.sha256(t.encode()).hexdigest()})
 (dst/'PATH_REBASE_RECORD.json').write_text(json.dumps({'source':str(src),'output':str(dst),'changes':changes,'warning':'Rebased files have new hashes. Do not bypass sealed manifest gates; review remote /workspace paths separately.'},indent=2)+'\n')
 print(json.dumps({'runtime':str(dst),'rebased_files':len(changes),'executed_archived_code':False}))
if __name__=='__main__':main()
