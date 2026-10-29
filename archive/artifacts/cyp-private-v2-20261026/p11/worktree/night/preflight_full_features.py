"""Read-only parity checks on existing native predictions; no feature fits/inference."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from .admet500_pilot import old_base_predictions
from .admet_full_math import place,placement_constants
from .admet_full import TARGETS
from .admet_full_contract import digest,require

def main():
    root=Path(__file__).resolve().parents[1];m=json.loads((root/'full_snapshot_manifest.template.json').read_text());files=m['files']
    paths={k:Path(v['path']) for k,v in files.items() if v.get('path')}
    for k,path in paths.items():require(digest(path)==files[k]['sha256'],'Static template input changed:'+k)
    data=pd.read_csv(paths['official_train']);cohorts=json.loads(paths['cohorts'].read_text())['cohorts'];lookup={x:i for i,x in enumerate(data.Molecule_Name)}
    constants=placement_constants(root/'vendor/briford_native/cyp_recalibrate.py');report={}
    for cohort in ('own750','briford529'):
        tr=np.array([lookup[x] for x in cohorts[cohort]['train_ids']]);te=np.array([lookup[x] for x in cohorts[cohort]['test_ids']])
        aliases={cohort+'_native_test':paths[cohort+'_native_raw'],**{cohort+'_'+member+'_oof':paths[cohort+'_'+member+'_oof'] for member in ('union18','mtaux8','2d6isoform6','2d6single')}}
        oof,test=old_base_predictions(aliases,cohort,data)
        predicted,meta=place(data.iloc[tr][TARGETS].to_numpy(float),oof[tr],test[te],TARGETS,constants)
        original=pd.read_csv(paths[cohort+'_native_placed']).set_index('Molecule_Name').loc[data.iloc[te].Molecule_Name,TARGETS].to_numpy()
        difference=float(np.max(np.abs(predicted-original)))
        require(np.allclose(predicted,original,atol=1e-6,rtol=1e-6),'Native placement parity failed:'+cohort)
        report[cohort]={'train':len(tr),'test':len(te),'max_placement_abs_difference':difference}
    print(json.dumps({'no_fits':True,'no_embedding_inference':True,'does_not_approve_reference_purges':True,'mathematical_native_placement_parity':report},indent=2))
if __name__=='__main__':main()
