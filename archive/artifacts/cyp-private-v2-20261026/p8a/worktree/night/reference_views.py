"""Lift a CYP2D6 specialist into an explicit four-target reference view, without labels."""
from pathlib import Path
import json,hashlib,argparse
import pandas as pd
import numpy as np
from .reference import CANONICAL

def prepare(source_root,output_root,seeds=(42,),cohorts=('own750','briford529')):
    source_root,output_root=Path(source_root),Path(output_root)
    records=[]
    for seed in seeds:
        for cohort in cohorts:
            for component,name in [('2d6single','specialist_single_view'),('2d6isoform6','specialist_aux_view')]:
                dest=output_root/name/cohort/f'seed{seed}';dest.mkdir(parents=True,exist_ok=True)
                for kind in ['oof','outer_raw']:
                    basepath=source_root/'briford_reference'/cohort/f'seed{seed}'/f'{kind}.csv'
                    partpath=source_root/component/cohort/f'seed{seed}'/f'{kind}.csv'
                    base=pd.read_csv(basepath);part=pd.read_csv(partpath)
                    if base.Molecule_Name.duplicated().any() or part.Molecule_Name.duplicated().any():raise ValueError('Duplicate IDs')
                    if set(base.Molecule_Name)!=set(part.Molecule_Name):raise ValueError('Specialist/reference ID mismatch')
                    target='CYP2D6_pIC50_direct_inhibition'
                    if set(part.columns)!={'Molecule_Name',target}:raise ValueError('Unexpected specialist target scope')
                    base[target]=part.set_index('Molecule_Name').loc[base.Molecule_Name,target].to_numpy()
                    if not np.isfinite(base[CANONICAL].to_numpy()).all():raise ValueError('Nonfinite view')
                    path=dest/f'{kind}.csv';payload=base[['Molecule_Name']+CANONICAL].to_csv(index=False).encode()
                    if path.exists() and path.read_bytes()!=payload:raise ValueError('Existing view content differs')
                    path.write_bytes(payload)
                    records.append({'path':str(path),'sha256':hashlib.sha256(payload).hexdigest(),
                        'base':str(basepath),'base_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),
                        'specialist':str(partpath),'specialist_sha256':hashlib.sha256(partpath.read_bytes()).hexdigest(),
                        'replaced_target':target,'labels_used':False})
    (output_root/'view_manifest.json').write_text(json.dumps(records,indent=2))
    return records

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',required=True);p.add_argument('--output-root',required=True);p.add_argument('--seed',type=int,default=42);a=p.parse_args()
    print(json.dumps({'event':'reference_views_prepared','files':len(prepare(a.source_root,a.output_root,[a.seed]))}))
