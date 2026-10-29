"""Private retention copies and reconstructed incumbent OOF; never changes frozen sources."""
from pathlib import Path
import os,json,shutil,hashlib,subprocess
import numpy as np,pandas as pd
os.umask(0o077);R=Path(__file__).resolve().parent;W=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026');OLD=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-briford-reproduction-20261024/remote/finalized');NEW=W/'model-audit/corrected-fullfit-native/recovered-output/results';H6=W/'final-locked-h6-output';T=[f'{x}_pIC50_direct_inhibition' for x in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def copy(src,dst):
 dst.parent.mkdir(exist_ok=True,parents=True)
 if not dst.exists():shutil.copy2(src,dst);dst.chmod(0o600)
 assert sha(src)==sha(dst);return {'original_path':str(src),'private_copy':str(dst),'sha256':sha(dst)}
rows={}
for src in NEW.rglob('*'):
 if src.is_file() and (src.suffix in ['.ckpt','.csv','.json']):rows['corrected_native/'+str(src.relative_to(NEW))]=copy(src,R/'corrected-native-artifact-copy'/src.relative_to(NEW))
for src in (H6/'final-models').rglob('*'):
 if src.is_file():rows['H6_models/'+str(src.relative_to(H6))]=copy(src,R/'H6-artifact-copy'/src.relative_to(H6))
for fn in ['full-data-selection.json','complete.json','final-placement.json','run-identity.json','selected__training_OOF.csv']:
 rows['H6/'+fn]=copy(H6/fn,R/'H6-artifact-copy'/fn)
truth=pd.read_csv('/Users/adeliyaleleytner/autoresearch-runs/cyp-admet500-pilot-20261025/stage/official-train.csv');total=np.zeros((len(truth),4));count=np.zeros_like(total);inputs={}
for m in ['union18','mtaux8','2d6isoform6','2d6single']:
 p=OLD/m/'oof.csv';f=pd.read_csv(p).set_index('molecule_name');assert f.index.is_unique;inputs[m]=sha(p)
 for j,t in enumerate(T):
  k=t.lower()+'_pred'
  if k not in f:continue
  a=f[k].reindex(truth.Molecule_Name).to_numpy();mask=np.isfinite(a);total[mask,j]+=a[mask];count[mask,j]+=1
pred=total/count;assert np.isfinite(pred).all();out=truth[['Molecule_Name','SMILES']].copy()
for j,t in enumerate(T):out[t]=pred[:,j]
p=R/'frozen-predictions/incumbent_official_training_OOF_reconstructed.csv';out.to_csv(p,index=False,float_format='%.17g')
rows['incumbent_official_OOF']={'private_copy':str(p),'sha256':sha(p),'derived_without_fit':True,'component_oof_sha256':inputs,'note':'Rowwise mean over available component predictions; component folds are not one shared split.'}
for name,p in [('corrected_native_official_OOF',NEW/'native_official_training_OOF.csv'),('H6_selected_OOF',H6/'selected__training_OOF.csv')]:rows[name]=copy(p,R/'frozen-predictions'/(name+'.csv'))
for name,commit in [('corrected-native-source','ed1ab38328eb9d088d785f90d4f96b99d95712e3'),('H6-final-source','7a62af907462847097a9ce4cf05921af404f6776')]:
 p=R/(name+'.tar.gz')
 if not p.exists():subprocess.run(['git','-C','/Users/adeliyaleleytner/.local/share/openresearch/projects/cyp-chemeleon-baseline-20261023','archive','--format=tar.gz','--output='+str(p),commit],check=True)
 rows[name]={'private_copy':str(p),'sha256':sha(p),'git_commit':commit}
(R/'additional_preservation_manifest.json').write_text(json.dumps({'files':rows,'no_fits':True,'private_only':True},indent=2)+'\n');print(json.dumps({'retention_files':len(rows),'original_and_corrected_native_checkpoints':40,'H6_heads':4,'new_fits':0}))
