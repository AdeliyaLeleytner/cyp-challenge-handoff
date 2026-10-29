#!/usr/bin/env python3
"""Verify archive checksums and immutable challenge CSVs without ML dependencies."""
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--all',action='store_true');v=a.parse_args();errors=[];checked=0;deferred=0;cache={}
 for line in (ROOT/'manifest/files.jsonl').read_text().splitlines():
  r=json.loads(line);p=ROOT/r['path']
  if not p.exists():
   if r['storage']=='release' and not v.all:deferred+=1;continue
   errors.append('missing '+r['path']);continue
  st=p.stat();key=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
  if key not in cache:cache[key]=digest(p)
  if st.st_size!=r['size'] or cache[key]!=r['sha256']:errors.append('checksum '+r['path'])
  checked+=1
 base=ROOT/'archive/artifacts/cyp-private-v2-20261026/p11/evidence'
 with (base/'official_blind.csv').open() as f:reference=list(csv.DictReader(f))
 columns=[x+'_pIC50_direct_inhibition' for x in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
 hashes={'native-csv.csv':'349165ecf50906e43a27f12dee97891a92cda59e798db614ef27a7c920c38a37','H6-csv.csv':'91fa8bf0870f68071b04183166b1507c20001d04f3ae3fb5f4d055618fff98c7','anchored-csv.csv':'6807263f0ccadcb31aa28a5c54653608e12271939a2490a2404d4353aeb0e16d'}
 for name,want in hashes.items():
  p=base/name
  if digest(p)!=want:errors.append('incumbent/submission hash '+name)
  with p.open() as f:rows=list(csv.DictReader(f))
  if len(rows)!=750 or [(r['Molecule_Name'],r['SMILES']) for r in rows]!=[(r['Molecule_Name'],r['SMILES']) for r in reference]:errors.append('identity/order '+name)
  if any(not math.isfinite(float(r[c])) for r in rows for c in columns):errors.append('nonfinite '+name)
 print(json.dumps({'status':'fail' if errors else 'pass','checked_files':checked,'deferred_release_paths':deferred,'verified_submission_files':len(hashes),'errors':errors[:30]},indent=2));sys.exit(bool(errors))
if __name__=='__main__':main()
