"""Private disjoint-pool analogue validation feasibility. No model fits or hidden labels."""
from pathlib import Path
from collections import defaultdict,Counter
from functools import lru_cache
import os,json,hashlib,time
import numpy as np,pandas as pd
from rdkit import Chem,DataStructs,RDLogger
from rdkit.Chem import rdFingerprintGenerator
from rdkit.ML.Cluster import Butina
from .public_data import normalize_parent_key
ROOT=Path(__file__).resolve().parents[1];T=[f'{c}_pIC50_direct_inhibition' for c in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']];SEED_T=[T[0],T[1],T[3]];OBS=[t+'_observed' for t in T];RDLogger.DisableLog('rdApp.*');GEN=rdFingerprintGenerator.GetMorganGenerator(radius=2,includeChirality=False)
def require(x,msg):
 if not x:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def event(n,**v):print(json.dumps({'event':n,**v},allow_nan=False),flush=True)
@lru_cache(maxsize=100000)
def structure(s):
 m=Chem.MolFromSmiles(s);require(m is not None,'Invalid source SMILES');p=normalize_parent_key(s);require(p is not None,'Invalid normalized parent');return GEN.GetSparseCountFingerprint(m),p,Chem.MolToInchiKey(m).split('-')[0]
def roles(data,strict_by_name,seed,fraction):
 parent=list(range(len(data)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 def union(a,b):parent[find(a)]=find(b)
 seen={}
 for i,r in enumerate(data.itertuples()):
  _,p,c=structure(r.SMILES);keys=['P:'+p,'C:'+c]+(['S:'+strict_by_name[r.Molecule_Name]] if r.Molecule_Name in strict_by_name else [])
  for k in keys:
   if k in seen:union(i,seen[k])
   else:seen[k]=i
 groups=defaultdict(list)
 for i in range(len(data)):groups[find(i)].append(i)
 result=np.empty(len(data),object);gids=np.empty(len(data),object)
 for members in groups.values():
  key=';'.join(sorted(data.iloc[members].Molecule_Name));h=hashlib.sha256((str(seed)+'|'+key).encode()).hexdigest();role='seed_pool' if int(h[:16],16)/2**64<fraction else 'query_candidate_pool'
  result[members]=role;gids[members]=h
 return result,gids

def projections(data,role):
 a=data.loc[role=='seed_pool',['Molecule_Name','SMILES',*SEED_T]].copy();b=data.loc[role=='query_candidate_pool',['Molecule_Name','SMILES']].copy()
 for t,o in zip(T,OBS):b[o]=data.loc[role=='query_candidate_pool',t].notna().to_numpy()
 return a,b

def select_queries(seed_frame,query_frame,n_hits,neighbors):
 require(set(seed_frame.Molecule_Name).isdisjoint(query_frame.Molecule_Name),'Seed/query pools overlap')
 require(set(query_frame)=={'Molecule_Name','SMILES',*OBS},'Query numeric outcomes are forbidden')
 chosen=[]
 for t in SEED_T:
  a=seed_frame.dropna(subset=[t]).sort_values([t,'Molecule_Name'],ascending=[False,True],kind='stable').head(n_hits)
  for r in a.itertuples():chosen.append({'seed_target':t,'Molecule_Name':r.Molecule_Name,'SMILES':r.SMILES,'seed_pIC50':float(getattr(r,t))})
 unique=sorted(set(x['Molecule_Name'] for x in chosen));seed_index=seed_frame.set_index('Molecule_Name');qfp=[structure(s)[0] for s in query_frame.SMILES];edges=[]
 for name in unique:
  sim=np.asarray(DataStructs.BulkTanimotoSimilarity(structure(seed_index.loc[name,'SMILES'])[0],qfp));order=np.lexsort((query_frame.Molecule_Name.to_numpy(),-sim))[:min(neighbors,len(sim))]
  for rank,i in enumerate(order):edges.append({'seed_id':name,'query_id':query_frame.Molecule_Name.iloc[i],'neighbor_rank':rank+1,'Tanimoto':float(sim[i])})
 ids=sorted(set(x['query_id'] for x in edges));return chosen,edges,ids

def profile(query,reference,reference_mask=None):
 qfp=[structure(s)[0] for s in query.SMILES];rfp=[structure(s)[0] for s in reference.SMILES];a=np.asarray([DataStructs.BulkTanimotoSimilarity(f,rfp) for f in qfp]);within=np.asarray([DataStructs.BulkTanimotoSimilarity(f,qfp) for f in qfp]);np.fill_diagonal(within,-1);n=len(query);near=a.max(1);wn=within.max(1);dist=[float(1-within[i,j]) for i in range(1,n) for j in range(i)];cl=Butina.ClusterData(dist,n,.3,isDistData=True,reordering=True);sizes=np.array([len(x) for x in cl])
 return {'query_rows':n,'reference_rows':len(reference),'median_query_to_training':float(np.median(near)),'fraction_query_to_training_ge_0.7':float(np.mean(near>=.7)),'median_within_query':float(np.median(wn)),'fraction_within_query_ge_0.7':float(np.mean(wn>=.7)),'Butina0.7_proxy_clusters':len(cl),'effective_proxy_clusters':float(1/np.sum((sizes/n)**2)),'largest_proxy_cluster':int(sizes.max())}

def main():
 os.umask(0o077);started=time.time();cfg=json.loads((ROOT/'private_p2_config.json').read_text());out=Path(cfg['output_dir']);require(not out.exists() or not any(out.iterdir()),'Output already populated');out.mkdir(parents=True,exist_ok=True)
 for k,r in cfg['files'].items():require(sha(r['path'])==r['sha256'],'Pinned asset changed:'+k)
 data=pd.read_csv(cfg['files']['official_train']['path']);blind=pd.read_csv(cfg['files']['official_blind']['path']);require(set(blind)=={'Molecule_Name','SMILES'},'Blind labels forbidden');pairs=pd.read_csv(cfg['files']['strict_pairs']['path'],dtype=str).fillna('');sg={}
 for r in pairs.itertuples():
  if r.stereo_preserving_tautomer_key_equal!='True':continue
  ids=r.request_ids.split(';');key=min(ids)
  for rid in ids:sg[rid]=key
 mapping=pd.read_csv(cfg['files']['id_map']['path'],dtype=str);rid={(r.source,r.Molecule_Name):r.request_id for r in mapping.itertuples()};strict={r.Molecule_Name:sg[r.request_id] for r in mapping[mapping.source=='official-train.csv'].itertuples() if r.request_id in sg}
 role,gid=roles(data,strict,cfg['seed'],cfg['seed_pool_fraction']);seed_input,query_input=projections(data,role)
 # Metamorphic data-flow test: arbitrary replacements of query-pool numeric outcomes cannot change selector inputs.
 altered=data.copy();qrows=np.flatnonzero(role=='query_candidate_pool')
 for t in T:
  ix=qrows[altered.iloc[qrows][t].notna().to_numpy()];altered.loc[ix,t]=np.arange(len(ix),dtype=float)*1000+123456
 alt_seed,alt_query=projections(altered,role);pd.testing.assert_frame_equal(seed_input,alt_seed);pd.testing.assert_frame_equal(query_input,alt_query)
 seeds,edges,query_ids=select_queries(seed_input,query_input,cfg['hits_per_target'],cfg['neighbors_per_hit']);require(len(query_ids)>1,'No usable query set');query=query_input.set_index('Molecule_Name').loc[query_ids].reset_index();require(not set(query_ids)&set(seed_input.Molecule_Name),'Selected query/seed overlap');seed_ids=set(x['Molecule_Name'] for x in seeds)
 seed_input.to_csv(out/'seed-pool-numeric-input.csv',index=False);query_input.to_csv(out/'query-candidate-input-no-outcomes.csv',index=False);pd.DataFrame(seeds).to_csv(out/'selected-seeds.csv',index=False);pd.DataFrame(edges).to_csv(out/'seed-query-edges.csv',index=False);query.to_csv(out/'query-panel-no-outcomes.csv',index=False)
 pd.DataFrame({'Molecule_Name':data.Molecule_Name,'SMILES':data.SMILES,'role_group':gid,'pool_role':role,'selected_seed':data.Molecule_Name.isin(seed_ids),'selected_query':data.Molecule_Name.isin(query_ids)}).to_csv(out/'official-roles.csv',index=False)
 qparent={structure(s)[1] for s in query.SMILES};qconn={structure(s)[2] for s in query.SMILES};qstrict={strict[x] for x in query_ids if x in strict};qfp=[structure(s)[0] for s in query.SMILES];source_summaries={};official_panels={}
 for member in ['union18','mtaux8','2d6isoform6','2d6single']:
  frame=pd.read_csv(cfg['files'][member]['path']);spec=json.loads(Path(cfg['files'][member+'_spec']['path']).read_text());targets=spec['targets'];mask=frame[targets].notna();availability=[''.join('1' if x else '0' for x in r) for r in mask.to_numpy()];nearest=[];reasons=[]
  for r in frame.itertuples():
   f,p,c=structure(r.smiles);s=sg.get(rid.get((member,r.molecule_name)));reason=[]
   if r.molecule_name in query_ids:reason.append('query_id')
   if p in qparent:reason.append('query_parent')
   if c in qconn:reason.append('query_connectivity')
   if s is not None and s in qstrict:reason.append('audited_strict_group')
   reasons.append(';'.join(reason));nearest.append(max(DataStructs.BulkTanimotoSimilarity(f,qfp)))
  nearest=np.asarray(nearest);base=np.array([not x for x in reasons]);near=base&(nearest>=cfg['series_similarity_cutoff']);series=base&~near;random=base.copy();strata=defaultdict(list)
  for i in np.flatnonzero(base):strata[(frame.molecule_name.iloc[i].split('-')[0] if frame.molecule_name.iloc[i].startswith('OCNT-') else 'CHEMBL' if frame.molecule_name.iloc[i].startswith('CHEMBL') else 'public_other',availability[i])].append(i)
  for key,indices in strata.items():
   count=int(near[indices].sum());order=sorted(indices,key=lambda i:hashlib.sha256((str(cfg['seed'])+'|'+member+'|'+frame.molecule_name.iloc[i]).encode()).hexdigest());random[order[:count]]=False
  require(series.sum()==random.sum() and mask.loc[series].sum().equals(mask.loc[random].sum()),'Random control failed count/availability matching')
  table=pd.DataFrame({'row_index':np.arange(len(frame)),'molecule_name':frame.molecule_name,'SMILES':frame.smiles,'availability_mask':availability,'query_exclusion_reason':reasons,'nearest_query_similarity':nearest,'anchor_retained':base,'series_withheld':series,'availability_matched_random':random});table.to_csv(out/(member+'-source-panels.csv'),index=False)
  summary={'source_rows':len(frame),'query_equivalent_rows_removed':int((~base).sum()),'source_policy':'Original incumbent pools retained for review; no automatic new source curation. Paired policy changes require separate declaration.','panels':{name:{'rows':int(use.sum()),'observed_target_cells':mask.loc[use].sum().astype(int).to_dict(),'retained_indices_sha256':hashlib.sha256(np.flatnonzero(use).astype(np.int64).tobytes()).hexdigest()} for name,use in [('anchor_retained',base),('series_withheld',series),('availability_matched_random',random)]},'random_matches_every_target_availability_count':True};source_summaries[member]=summary
  if member=='mtaux8':
   for name,use in [('anchor_retained',base),('series_withheld',series),('availability_matched_random',random)]:official_panels[name]=frame.loc[use].rename(columns={'molecule_name':'Molecule_Name','smiles':'SMILES'})
   require(seed_ids<=set(frame.loc[base].molecule_name),'Anchor-retained panel lost a selected seed')
  event('source_panel_ready',member=member,query_excluded=int((~base).sum()),anchor_rows=int(base.sum()),series_rows=int(series.sum()),random_rows=int(random.sum()))
 geom=[];coverage=[]
 for name,ref in official_panels.items():
  geom.append({'context':'prospective_query','panel':name,**profile(query,ref)})
  geom.append({'context':'blind750_same_reference','panel':name,**profile(blind,ref)})
  for t,o in zip(T,OBS):
   q=query.loc[query[o]];rr=ref.loc[ref[t.lower()].notna()];nn=[max(DataStructs.BulkTanimotoSimilarity(structure(s)[0],[structure(x)[0] for x in rr.SMILES])) for s in q.SMILES] if len(q) and len(rr) else []
   coverage.append({'panel':name,'target':t,'query_observed':len(q),'training_observed':len(rr),'median_query_to_primary_labeled_train':float(np.median(nn)) if nn else None})
 single=pd.read_csv(cfg['files']['single']['path']);single_ids=set(single.Molecule_Name);summary={'status':'feasibility_complete_not_model_validation','design':{k:cfg[k] for k in ['seed','seed_pool_fraction','hits_per_target','neighbors_per_hit','seed_targets','series_similarity_cutoff']},'official_rows':len(data),'seed_pool_rows':len(seed_input),'query_candidate_rows':len(query_input),'seed_selections':len(seeds),'unique_seed_molecules':len(seed_ids),'neighbor_slots':len(edges),'unique_query_molecules':len(query),'query_observed_per_target':{t:int(query[o].sum()) for t,o in zip(T,OBS)},'query_all4_observed':int(query[OBS].all(1).sum()),'query_no_released_single':int((~query.Molecule_Name.isin(single_ids)).sum()),'query_numeric_perturbation_leaves_selector_inputs_identical':True,'seed_query_role_groups_disjoint':True,'source_panels':source_summaries,'no_750_forcing':True,'no_imputed_labels':True,'no_model_fits':True,'no_hidden_labels':True,'private_only':True,'no_network':True,'limitations':['One declared50/50 role partition, not an optimized split search.','Allquery numeric values were excluded from selector inputs; only known availability was reported.','This does not establish a dense4-CYP target panel or recover true organizer parent series.','Series/random controls match row counts and every target availability count, not numeric activity distributions.','Purges cover declared parent/connectivity/audited strict rules, not all possible chemical equivalences.']}
 pd.DataFrame(geom).to_csv(out/'geometry.csv',index=False);pd.DataFrame(coverage).to_csv(out/'endpoint-support.csv',index=False);save(out/'summary.json',summary);save(out/'run-identity.json',{'config':cfg,'seed_numeric_fields':SEED_T,'query_input_fields':list(query_input.columns),'no_query_numeric_outcomes':True});save(out/'complete.json',{'status':'complete','seconds':time.time()-started,'model_fits':0,'private_only':True,'publication':False,'submission':False,'files_sha256':{p.name:sha(p) for p in out.iterdir() if p.is_file()}});event('private_P2_complete',seconds=time.time()-started,seed_pool=len(seed_input),query_candidates=len(query_input),selected_query=len(query),query_observed=summary['query_observed_per_target'],all4=summary['query_all4_observed'])
if __name__=='__main__':main()
