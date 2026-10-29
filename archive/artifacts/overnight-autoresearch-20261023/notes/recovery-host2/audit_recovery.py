"""Read-only remote filesystem SHA256 snapshot plus local recovery comparison."""
import argparse,collections,hashlib,json,os,subprocess,time
from datetime import datetime,timezone
from pathlib import Path

CAMPAIGN=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023')
OUT=Path(__file__).parent
HOST='cyp-night-57428215'
REMOTE=r'''
import os,json,hashlib,time,stat
from pathlib import Path
from datetime import datetime,timezone
roots={'assets':'/workspace/cyp-night/assets','results':'/workspace/cyp-night/results',
       'orx_runs':'/root/.orx/runs','orx_source':'/root/.orx/source','root_files':'/workspace/cyp-night'}
def paths(root,recursive=True):
 if not recursive:return sorted(p for p in root.iterdir() if not p.is_dir() or p.is_symlink())
 result=[]
 for directory,dirs,files in os.walk(root,followlinks=False):
  d=Path(directory)
  links=[name for name in dirs if (d/name).is_symlink()]
  dirs[:]=[name for name in dirs if name not in links]
  result.extend(d/name for name in files+links)
 return sorted(result)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
start=datetime.now(timezone.utc).isoformat();scopes={};errors=[]
for label,name in roots.items():
 root=Path(name);initial=paths(root,label!='root_files');files=[]
 for p in initial:
  record={'path':str(p.relative_to(root))}
  try:
   before=p.lstat();record.update(bytes=before.st_size,mtime_ns=before.st_mtime_ns)
   if p.is_symlink():
    record.update(kind='symlink',target=os.readlink(p),resolved_target=str(p.resolve()),
                  target_exists=p.exists())
   elif stat.S_ISREG(before.st_mode):
    record.update(kind='file',sha256=sha(p))
   else:record.update(kind='special_file')
   after=p.lstat();record['stable_during_hash']=(before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
  except Exception as error:
   record.update(kind='error',error=type(error).__name__+': '+str(error));errors.append({'scope':label,**record})
  files.append(record)
 final=paths(root,label!='root_files')
 scopes[label]={'remote_root':name,'files':files,'added_during_scan':sorted(str(p.relative_to(root)) for p in set(final)-set(initial)),
                'removed_during_scan':sorted(str(p.relative_to(root)) for p in set(initial)-set(final))}
# Paths outside the recovery roots: inspect known cache/workspace/temp locations,
# but never enumerate or read credentials, system package trees, or /proc.
outside=[]
suffixes={'.pt','.pth','.ckpt','.bin','.safetensors','.npy','.npz','.parquet','.arrow','.csv','.tsv','.joblib','.pkl','.cbm','.tar','.zip'}
for base in [Path('/root/.cache'),Path('/tmp'),Path('/workspace')]:
 for directory,dirs,files in os.walk(base,followlinks=False):
  d=Path(directory)
  dirs[:]=[v for v in dirs if not (d/v).is_symlink() and str(d/v) not in roots.values() and v not in {'site-packages','__pycache__'}]
  for name in files:
   p=d/name
   if p.suffix.lower() in suffixes:
    s=p.stat();outside.append({'path':str(p),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns})
print(json.dumps({'host':'cyp-night-57428215','started_utc':start,'finished_utc':datetime.now(timezone.utc).isoformat(),
 'scopes':scopes,'errors':errors,'outside_artifact_candidates':outside,
 'excluded_scope':'Python environments/system packages are not content-hashed; environment lockfiles in root_files are included. No credentials inspected.'}))
'''

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()

def audit(remote_manifest):
 mappings={'assets':CAMPAIGN/'remote2/assets','results':CAMPAIGN/'remote2/results',
           'orx_runs':CAMPAIGN/'remote2-orx/runs','orx_source':CAMPAIGN/'remote2-orx/source','root_files':CAMPAIGN/'remote2'}
 comparison={};differences=[];unresolved_links=[]
 for label,scope in remote_manifest['scopes'].items():
  root=mappings[label];counts=collections.Counter();total_bytes=0;matched_bytes=0;local_hashes={}
  for rec in scope['files']:
   counts['remote_entries']+=1;p=root/rec['path'];kind=rec['kind']
   if kind=='file':counts['remote_files']+=1;total_bytes+=rec['bytes']
   if not rec.get('stable_during_hash',False):differences.append({'scope':label,'path':rec['path'],'reason':'remote_changed_or_error_during_hash'});counts['unstable_remote']+=1;continue
   if not p.exists() and not p.is_symlink():differences.append({'scope':label,'path':rec['path'],'reason':'missing_local','bytes':rec['bytes']});counts['missing_local']+=1;continue
   try:
    if kind=='symlink':
     if not p.is_symlink() or os.readlink(p)!=rec['target']:differences.append({'scope':label,'path':rec['path'],'reason':'symlink_mismatch'});counts['symlink_mismatch']+=1
     else:counts['matched_symlinks']+=1
     unresolved_links.append({'scope':label,**rec,'local_resolves':p.exists()})
     continue
    if kind!='file':differences.append({'scope':label,'path':rec['path'],'reason':'unsupported_remote_entry'});counts['unsupported']+=1;continue
    if p.is_symlink() or not p.is_file():differences.append({'scope':label,'path':rec['path'],'reason':'local_type_mismatch'});counts['type_mismatch']+=1;continue
    before=p.stat()
    if before.st_size!=rec['bytes']:differences.append({'scope':label,'path':rec['path'],'reason':'size_mismatch','remote_bytes':rec['bytes'],'local_bytes':before.st_size});counts['size_mismatch']+=1;continue
    actual=sha(p);after=p.stat();local_hashes[rec['path']]=actual
    if (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):
     differences.append({'scope':label,'path':rec['path'],'reason':'local_changed_during_hash'});counts['unstable_local']+=1
    elif actual!=rec['sha256']:
     differences.append({'scope':label,'path':rec['path'],'reason':'sha256_mismatch','remote_sha256':rec['sha256'],'local_sha256':actual});counts['hash_mismatch']+=1
    else:counts['matched_files']+=1;matched_bytes+=rec['bytes']
   except Exception as error:differences.append({'scope':label,'path':rec['path'],'reason':'local_read_error','error':str(error)});counts['read_error']+=1
  for path in scope['added_during_scan']+scope['removed_during_scan']:differences.append({'scope':label,'path':path,'reason':'remote_file_list_changed'})
  (OUT/f'local-{label}-hashes.json').write_text(json.dumps(local_hashes,sort_keys=True))
  comparison[label]={'local_root':str(root),'remote_root':scope['remote_root'],'counts':dict(counts),'remote_file_bytes':total_bytes,'matched_file_bytes':matched_bytes}
 extra=remote_manifest['outside_artifact_candidates']
 complete=not differences and not remote_manifest['errors'] and not extra and not unresolved_links
 cert={'schema_version':1,'host':HOST,'created_utc':datetime.now(timezone.utc).isoformat(),
       'remote_snapshot_started':remote_manifest['started_utc'],'remote_snapshot_finished':remote_manifest['finished_utc'],
       'scope_comparison':comparison,'difference_count':len(differences),'differences':differences,
       'outside_artifact_candidates':extra,'symlinks_requiring_target_review':unresolved_links,
       'all_scoped_regular_files_match':not differences,'recovery_complete_for_audited_scope':complete,
       'remote_manifest_sha256':sha(OUT/'remote-manifest.json'),
       'limitations':['Point-in-time filesystem recovery audit, not a model reload or environment restoration test.',
                      'No instance stop/destruction authorized or performed by this audit.',
                      'System packages/Python environment binaries omitted; requirements lockfiles are covered.',
                      'Remote paths outside /workspace,/tmp,/root/.cache and the specified ORX roots were not broadly searched.'],
       'total_regular_files':sum(v['counts'].get('remote_files',0) for v in comparison.values()),
       'total_regular_file_bytes':sum(v['remote_file_bytes'] for v in comparison.values())}
 (OUT/'recovery-certificate.json').write_text(json.dumps(cert,indent=2))
 print(json.dumps({k:cert[k] for k in ['difference_count','all_scoped_regular_files_match','recovery_complete_for_audited_scope','total_regular_files','total_regular_file_bytes']}),flush=True)
 for label,values in comparison.items():print(label,json.dumps(values['counts']),values['remote_file_bytes'],flush=True)
 if differences:print('differences',json.dumps(differences[:25]),flush=True)
 if extra:print('outside',json.dumps(extra),flush=True)
 if unresolved_links:print('symlinks',json.dumps(unresolved_links[:20]),flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--compare-only',action='store_true');args=parser.parse_args()
 if not args.compare_only:
  temporary=OUT/'remote-manifest.json.part'
  with temporary.open('w') as out:
   result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',HOST,'python3','-'],input=REMOTE,text=True,stdout=out,stderr=subprocess.PIPE)
  if result.returncode:raise RuntimeError(result.stderr[-2000:])
  json.loads(temporary.read_text());temporary.replace(OUT/'remote-manifest.json')
  print('REMOTE_HASHING_COMPLETE',flush=True)
 audit(json.loads((OUT/'remote-manifest.json').read_text()))
