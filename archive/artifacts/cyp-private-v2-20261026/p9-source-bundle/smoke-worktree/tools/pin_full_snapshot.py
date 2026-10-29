#!/usr/bin/env python3
"""Pin an approved complete snapshot into this provisional node; does not fit models."""
import argparse,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from night.admet_full_contract import validate,digest,require

def main():
    p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path,default=Path('full_feature_config.json'));a=p.parse_args()
    require(not a.output.exists(),'Snapshot manifest destination already exists')
    m=json.loads(a.draft.read_text());cfg=json.loads(a.config.read_text())
    for name,item in m['files'].items():
        require(bool(item.get('path')),'Missing asset path:'+name)
        actual=digest(item['path'])
        if item.get('sha256'):require(item['sha256']==actual,'Existing pin changed:'+name)
        else:item['sha256']=actual
    # Check the full collection and audit before modifying the committed config.
    with tempfile.TemporaryDirectory() as temp:
        candidate=Path(temp)/'manifest.json';candidate.write_text(json.dumps(m,indent=2)+'\n')
        trial={**cfg,'snapshot_manifest':str(candidate),'snapshot_manifest_sha256':digest(candidate)}
        validate(trial)
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(candidate.read_bytes())
    cfg.update(snapshot_manifest=str(a.output.resolve()),snapshot_manifest_sha256=digest(a.output))
    a.config.write_text(json.dumps(cfg,indent=2)+'\n')
    print(json.dumps({'status':'pinned','manifest':str(a.output.resolve()),'manifest_sha256':cfg['snapshot_manifest_sha256'],'fits_started':0,'next_action':'Commit this provisional node before any ORX run.'}))
if __name__=='__main__':main()
