from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from rdkit import Chem,DataStructs,RDLogger
from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator
RDLogger.DisableLog('rdApp.*');R=Path(__file__).resolve().parent;O=R/'results';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();cfg=json.loads((R/'worktree/private_p2_config.json').read_text());done=json.loads((O/'complete.json').read_text());s=json.loads((O/'summary.json').read_text())
for k,r in cfg['files'].items():assert sha(r['path'])==r['sha256']
for k,h in done['files_sha256'].items():assert sha(O/k)==h
roles=pd.read_csv(O/'official-roles.csv');seed=pd.read_csv(O/'seed-pool-numeric-input.csv');qpool=pd.read_csv(O/'query-candidate-input-no-outcomes.csv');query=pd.read_csv(O/'query-panel-no-outcomes.csv');seeds=pd.read_csv(O/'selected-seeds.csv');edges=pd.read_csv(O/'seed-query-edges.csv');data=pd.read_csv(cfg['files']['official_train']['path']).set_index('Molecule_Name');T=[f'{c}_pIC50_direct_inhibition' for c in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']];OBS=[t+'_observed' for t in T];ST=[T[0],T[1],T[3]]
assert roles.Molecule_Name.tolist()==data.index.tolist() and roles.Molecule_Name.is_unique
assert set(seed.Molecule_Name).isdisjoint(qpool.Molecule_Name) and set(seed.Molecule_Name)|set(qpool.Molecule_Name)==set(data.index)
assert set(roles.loc[roles.pool_role=='seed_pool','role_group']).isdisjoint(roles.loc[roles.pool_role=='query_candidate_pool','role_group'])
assert set(qpool)=={'Molecule_Name','SMILES',*OBS} and set(query)==set(qpool)
for frame in [seed,qpool,query]:assert frame.SMILES.tolist()==data.loc[frame.Molecule_Name].SMILES.tolist()
for t,o in zip(T,OBS):assert np.array_equal(query[o],data.loc[query.Molecule_Name,t].notna())
for t in ST:
 expected=seed.dropna(subset=[t]).sort_values([t,'Molecule_Name'],ascending=[False,True]).head(25).Molecule_Name.tolist();actual=seeds.loc[seeds.seed_target==t].Molecule_Name.tolist();assert expected==actual
assert set(seeds.seed_target)==set(ST) and set(query.Molecule_Name)<=set(qpool.Molecule_Name)
gen=GetMorganGenerator(radius=2,includeChirality=False);qfp=[gen.GetSparseCountFingerprint(Chem.MolFromSmiles(x)) for x in qpool.SMILES]
for sid,g in edges.groupby('seed_id'):
 f=gen.GetSparseCountFingerprint(Chem.MolFromSmiles(data.loc[sid,'SMILES']));sim=DataStructs.BulkTanimotoSimilarity(f,qfp);expected=sorted(zip(qpool.Molecule_Name,sim),key=lambda x:(-x[1],x[0]))[:10];actual=g.sort_values('neighbor_rank');assert actual.query_id.tolist()==[x[0] for x in expected];assert np.allclose(actual.Tanimoto,[x[1] for x in expected],atol=1e-12)
assert set(query.Molecule_Name)==set(edges.query_id) and len(query)==s['unique_query_molecules']==474
for member in ['union18','mtaux8','2d6isoform6','2d6single']:
 p=pd.read_csv(O/(member+'-source-panels.csv'),dtype={'availability_mask':str,'query_exclusion_reason':str},keep_default_na=False);f=pd.read_csv(cfg['files'][member]['path']);spec=json.loads(Path(cfg['files'][member+'_spec']['path']).read_text());mask=f[spec['targets']].notna();assert p.molecule_name.tolist()==f.molecule_name.tolist() and p.SMILES.tolist()==f.smiles.tolist();assert np.array_equal(p.anchor_retained,p.query_exclusion_reason.eq(''));assert np.array_equal(p.series_withheld,p.anchor_retained&(p.nearest_query_similarity<.6));assert not set(p.loc[p.anchor_retained,'molecule_name'])&set(query.Molecule_Name);assert p.series_withheld.sum()==p.availability_matched_random.sum();assert mask.loc[p.series_withheld].sum().equals(mask.loc[p.availability_matched_random].sum())
value={'status':'independently_verified_feasibility_only','selected_query':len(query),'seed_selections':len(seeds),'unique_seeds':seeds.Molecule_Name.nunique(),'actual_three_seed_targets':ST,'query_numeric_columns_absent':True,'parent_role_groups_disjoint':True,'independent_top10_ranking_reproduced':True,'source_panel_count_and_all_target_availability_match':True,'query_ids_absent_from_all_proposed_training_panels':True,'fresh_29_eligibility_applied':False,'fit_ready':False,'required_before_fit':'New prospective child applies shared fresh eligibility before regenerating source masks/random matched controls; map by identity, not old row positions.','model_fits':0}
(R/'VERIFICATION.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value,indent=2))
