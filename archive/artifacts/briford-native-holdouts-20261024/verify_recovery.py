from pathlib import Path
import subprocess,json,hashlib,datetime
p=Path(__file__).resolve().parent
remote_code='''from pathlib import Path\nimport hashlib,json\nroots={"runtime":"/workspace/cyp-repro","orx":"/root/.orx"}\nrecords=[]\nfor label,root in roots.items():\n for f in sorted(Path(root).rglob("*")):\n  if f.is_symlink():raise RuntimeError("Unreviewed symlink:"+str(f))\n  if not f.is_file():continue\n  before=f.stat();h=hashlib.sha256()\n  with f.open("rb") as stream:\n   for chunk in iter(lambda:stream.read(4*1024*1024),b""):h.update(chunk)\n  after=f.stat()\n  assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),str(f)\n  records.append({"scope":label,"relative":str(f.relative_to(root)),"bytes":after.st_size,"sha256":h.hexdigest()})\nprint(json.dumps(records))\n'''
r=subprocess.run(['ssh','cyp-holdouts-57503867','python','-'],input=remote_code,capture_output=True,text=True,timeout=120,check=True);records=json.loads(r.stdout);(p/'remote-recovery-manifest.json').write_text(json.dumps(records,indent=2)+'\n')
roots={'runtime':p/'remote','orx':p/'remote-orx'};bad=[]
for item in records:
 f=roots[item['scope']]/item['relative']
 if not f.exists():bad.append({'file':str(f),'error':'missing'});continue
 h=hashlib.sha256()
 with f.open('rb') as stream:
  for chunk in iter(lambda:stream.read(4*1024*1024),b''):h.update(chunk)
 if f.stat().st_size!=item['bytes'] or h.hexdigest()!=item['sha256']:bad.append({'file':str(f),'error':'hash_or_size'})
report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':'cyp-holdouts-57503867','files':len(records),'bytes':sum(i['bytes'] for i in records),'mismatches':bad,'all_match':not bad,'scope':['/workspace/cyp-repro','/root/.orx'],'limitation':'System packages omitted; environment lock and committed setup script retained. All learned artifacts are explicitly written under audited runtime scope.'}
(p/'recovery-certificate.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));raise SystemExit(bool(bad))
