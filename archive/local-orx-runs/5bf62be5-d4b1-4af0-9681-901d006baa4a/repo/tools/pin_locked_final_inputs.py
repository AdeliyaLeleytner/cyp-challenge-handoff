#!/usr/bin/env python3
"""Validate/pin immutable completed inputs; optionally enable, never launch a fit."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from night.admet_full_contract_v1 import digest,require
from night.locked_h6_final import check_locked_config
from night.final_feature_contract import validate
from night.final_feature_run import validate_bridge_config

def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--final-manifest',type=Path,required=True);p.add_argument('--enable',action='store_true');a=p.parse_args()
    config=Path('final_feature_config.json');cfg=json.loads(config.read_text())
    trial={**cfg,'snapshot_manifest':str(a.snapshot.resolve()),'snapshot_manifest_sha256':digest(a.snapshot),'final_manifest':str(a.final_manifest.resolve()),'final_manifest_sha256':digest(a.final_manifest),'training_enabled':bool(a.enable)}
    check_locked_config(trial);validate(trial);validate_bridge_config(trial)
    config.write_text(json.dumps(trial,indent=2)+'\n')
    print(json.dumps({'status':'validated_and_pinned','training_enabled':trial['training_enabled'],'fits_started':0,'next_action':'Commit exact config/source and launch only through ORX when root authorizes.'}))
if __name__=='__main__':main()
