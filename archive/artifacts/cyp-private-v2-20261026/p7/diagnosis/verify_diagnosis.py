from pathlib import Path
import json,hashlib
import pandas as pd,numpy as np
from scipy.stats import spearmanr,kendalltau
from rdkit import Chem,DataStructs
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.MolStandardize import rdMolStandardize
p=Path(__file__).parent;r=pd.read_csv(p/'results/measured-row-diagnostics.csv');m=pd.read_csv(p/'results/metrics-by-stratum.csv');pairs=pd.read_csv(p/'results/close-pairs.csv');errors=[]
for ep,g in r.groupby('endpoint'):
 for scope,q in [('pooled',g)]+[(f'fold={k}',g[g.fold==k]) for k in range(5)]:
  for c in ['zero','fusion']:
   y=q.truth.to_numpy();v=q[c].to_numpy();e=v-y;sy=np.std(y);sp=np.std(v);rho=np.corrcoef(y,v)[0,1];terms=np.array([np.mean(e)**2,(sp-sy)**2,2*sp*sy*(1-rho)]);ref=m[(m.endpoint==ep)&(m.scope==scope)&(m.cell==c)].iloc[0];values={'MAE':abs(e).mean(),'MSE':np.mean(e**2),'RMSE':np.sqrt(np.mean(e**2)),'bias':e.mean(),'mse_bias2':terms[0],'mse_sd_gap2':terms[1],'mse_covariance_loss':terms[2],'within_2fold':np.mean(abs(e)<=np.log10(2)),'within_10fold':np.mean(abs(e)<=1)}
   for k,vv in values.items():errors.append(abs(vv-ref[k]));assert abs(vv-ref[k])<1e-12
   assert abs(sum(terms)-np.mean(e**2))<1e-12
gen=rdFingerprintGenerator.GetMorganGenerator(radius=2,fpSize=2048,includeChirality=False)
fps={}
for a in pairs.itertuples():
 for smi in [a.smiles_a,a.smiles_b]:
  if smi not in fps:fps[smi]=gen.GetFingerprint(rdMolStandardize.FragmentParent(rdMolStandardize.Cleanup(Chem.MolFromSmiles(smi))))
 exact_sim=DataStructs.TanimotoSimilarity(fps[a.smiles_a],fps[a.smiles_b])
 assert exact_sim>=.7 and abs(exact_sim-a.similarity)<1e-7 and a.id_a!=a.id_b
 g=r[r.endpoint==a.endpoint].set_index('molecule_name');assert int(g.loc[a.id_a,'fold'])==int(g.loc[a.id_b,'fold'])==a.fold
 assert abs((g.loc[a.id_b,'truth']-g.loc[a.id_a,'truth'])-a.truth_delta_b_minus_a)<1e-12
 for c in ['zero','fusion']:assert abs((g.loc[a.id_b,c]-g.loc[a.id_a,c])-getattr(a,c+'_delta_b_minus_a'))<1e-12
receipt={'status':'pass','independent_Pearson_form_MSE_reconstruction':True,'pooled_and_per_fold_checks':48,'max_numeric_difference':max(errors),'pairs_checked':len(pairs),'all_pair_similarities_recomputed_exactly':True,'float32_threshold_note':'Six cached0.7 entries roundto0.699999988; exactRDKit Tanimoto is>=0.7 for all120pairs','no_CYP2C9_pairs':not(pairs.endpoint=='CYP2C9').any(),'fixed_geometry_threshold':.7,'scientific_run':'07bd32c8-6e52-4139-90f1-e381b856c7fc','scientific_source':'aaf0cee3d12c8ccd17fe04bc10d5a7326fe0beb8','files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((p/'results').iterdir()) if f.is_file()},'verification_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(p/'VERIFICATION.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='files'}))
