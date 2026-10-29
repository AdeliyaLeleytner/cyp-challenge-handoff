#!/usr/bin/env python3
"""Bind completed local artifacts to actual ORX run metadata; does not fit/upload."""
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from night.admet_full_contract_v1 import require,digest
from night.external_tabpfn_contract import write_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=['oof','query','selection'],required=True);p.add_argument('--result-dir',type=Path,required=True);p.add_argument('--experiment-id',required=True);p.add_argument('--run-id',required=True);p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    for value in (a.experiment_id,a.run_id):require(re.fullmatch(r'[0-9a-f-]{36}',value) is not None,'Pass actual ORX UUID metadata')
    require(re.fullmatch(r'[0-9a-f]{40}',a.commit) is not None,'Pass exact actual producer source commit')
    require(not a.output.exists(),'Artifact manifest is immutable; use a new path')
    if a.kind=='selection':
        receipt=json.loads((a.result_dir/'complete.json').read_text());require(receipt['status']=='awaiting_tabpfn_query','CPU selector did not select TabPFN')
        names={'selection':'full-data-selection.json','selection_lock':'selection-lock.json','selected_oof':'selected__training_OOF.csv','query_request':'tabpfn-query-request.json','producer_config':'producer-config.json','external_oof':'external_tabpfn_oof.csv'}
    else:
        receipt=json.loads((a.result_dir/'complete.json').read_text());require(receipt['status']=='complete' and receipt['phase']==a.kind,'Wrong/incomplete TabPFN phase')
        require(receipt['producer_experiment_id']==a.experiment_id,'ORX experiment differs from stage config/receipt')
        names={'receipt':'complete.json','predictions':'tabpfn-'+a.kind+'-predictions.csv'}
    require(receipt.get('producer_experiment_id')==a.experiment_id,'Actual producer experiment differs from requested manifest metadata')
    files={}
    for key,name in names.items():
        path=(a.result_dir/name).resolve();require(path.is_file(),'Missing stage output: '+name);files[key]={'path':str(path),'sha256':digest(path)}
    manifest={'schema_version':1,'kind':a.kind,'producer_experiment_id':a.experiment_id,'producer_orx_run_id':a.run_id,'producer_commit':a.commit,'files':files}
    write_json(a.output,manifest);print(json.dumps({'artifact':str(a.output),'sha256':digest(a.output),'fits_started':0}))
if __name__=='__main__':main()
