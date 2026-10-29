from pathlib import Path
from functools import lru_cache
import pandas as pd,numpy as np,json,hashlib
from rdkit import Chem,RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize
RDLogger.DisableLog('rdApp.*')
P=Path(__file__).resolve().parents[1];O=Path(__file__).resolve().parent;G=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026');A=G/'chemistry-audit/full-pool-preaudit';F=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/fullfit-strae-prep/stage/original_full');raw=F/'raw';audit=pd.read_csv(A/'molecule-input-audit.csv').set_index('request_id');imap=pd.read_csv(A/'id-map-snapshot.csv');test=pd.read_csv(F/'official-test.csv');chembl=pd.read_csv(raw/'chembl_all_isoforms.csv');pub=pd.read_csv(raw/'pubchem_all_isoforms.csv');final=pd.read_csv(P/'p7/stage/table.csv');parent={}
@lru_cache(None)
def canonical(s):
 if not isinstance(s,str) or not s:return None
 m=Chem.MolFromSmiles(s);return Chem.MolToSmiles(m,isomericSmiles=True) if m else None
def find(x):
 parent.setdefault(x,x)
 if parent[x]!=x:parent[x]=find(parent[x])
 return parent[x]
pairs=pd.read_csv(A/'tautomer-pair-chemical-details.csv')
for ids in pairs[pairs.stereo_preserving_tautomer_key_equal==True].request_ids.str.split(';'):
 for v in ids[1:]:parent[find(ids[0])]=find(v)
request_by_graph={row.isomeric_key:rid for rid,row in audit.iterrows()};
normalizer=rdMolStandardize.Normalizer();uncharger=rdMolStandardize.Uncharger()
@lru_cache(None)
def broad_key(s):
 key=canonical(s);rid=request_by_graph.get(key)
 if rid:return audit.loc[rid,'parent_uncharged_no_stereo_key']
 if key is None:return None
 n=normalizer.normalize(Chem.MolFromSmiles(s));n=uncharger.uncharge(n)
 if len(Chem.GetMolFrags(n))>1:n=rdMolStandardize.FragmentParent(n,skipStandardize=True)
 Chem.RemoveStereochemistry(n);return Chem.MolToSmiles(n,isomericSmiles=True)
final['iso']=final.smiles.map(canonical);final['group']=final.request_id.map(find);final['broad']=final.request_id.map(audit.parent_uncharged_no_stereo_key)
externalcols=[c for c in final if c.endswith('_pic50_chembl') or c.endswith('_max_response')];final['has_public_aux']=final[externalcols].notna().any(axis=1);blindmap=imap[imap.source=='official-test.csv'].set_index('Molecule_Name');test['request_id']=blindmap.loc[test.Molecule_Name,'request_id'].to_numpy();test['iso']=test.SMILES.map(canonical);test['group']=test.request_id.map(find);test['broad']=test.request_id.map(audit.parent_uncharged_no_stereo_key)
# Existing source rows, preserved original and prepared representations.
records=[]
for i,r in chembl.iterrows():
 vals={k:r[k] for k in r.index if k.endswith('_pic50') and pd.notna(r[k])};orig=canonical(r.orig_smiles);prepared=canonical(r.smiles);rid=request_by_graph.get(prepared)
 records.append({'source':'ChEMBL_aggregate','source_row':i,'source_id':str(r.chembl_id),'original_smiles':r.orig_smiles,'prepared_smiles':r.smiles,'original_iso':orig,'prepared_iso':prepared,'request_id':rid,'group':find(rid) if rid else None,'broad':broad_key(r.smiles),'original_broad':broad_key(r.orig_smiles),'values':vals,'source_payload':r.to_dict()})
for i,r in pub.iterrows():
 vals={k:r[k] for k in ['pic50','ac50_um','fit_log_ac50','max_response','curve_class','fit_r2','hill_slope'] if pd.notna(r[k])};orig=canonical(r.orig_smiles);prepared=canonical(r.smiles);rid=request_by_graph.get(prepared)
 records.append({'source':'PubChem_Veith','source_row':i,'source_id':f'SID{r.sid}/CID{r.cid}/{r.isoform}','original_smiles':r.orig_smiles,'prepared_smiles':r.smiles,'original_iso':orig,'prepared_iso':prepared,'request_id':rid,'group':find(rid) if rid else None,'broad':broad_key(r.smiles),'original_broad':broad_key(r.orig_smiles),'values':vals,'source_payload':r.to_dict()})
matched=[];counts=[];levelcols=[('original_exact_isomeric','original_iso','iso'),('prepared_exact_isomeric','prepared_iso','iso'),('approved_equivalence_including_exact','group','group'),('broader_parent_uncharged_no_stereo','broad','broad'),('original_broader_parent_uncharged_no_stereo','original_broad','broad')]
for level,scol,tcol in levelcols:
 lookup={}
 for r in records:
  key=r[scol]
  if key is not None:lookup.setdefault(key,[]).append(r)
 for source in ['ChEMBL_aggregate','PubChem_Veith']:
  hits=[]
  for _,t in test.iterrows():
   for r in lookup.get(t[tcol],[]):
    if r['source']==source:
     row={'match_level':level,'official_id':t.Molecule_Name,'official_SMILES':t.SMILES,'official_request_id':t.request_id,**r};matched.append(row);hits.append(row)
  counts.append({'level':level,'source':source,'blind_molecules':len({x['official_id'] for x in hits}),'source_rows':len(hits),'source_ids':len({x['source_id'] for x in hits})})
(O/'blind-source-matches.json').write_text(json.dumps(matched,indent=2,default=lambda v:None if pd.isna(v) else str(v))+'\n');pd.DataFrame(counts).to_csv(O/'blind-coverage-counts.csv',index=False)
# Concrete retained current-table targets for each blind source relation.
retained=[]
for _,t in test.iterrows():
 for level,key in [('prepared_exact_isomeric','iso'),('approved_equivalence_including_exact','group'),('broader_parent_uncharged_no_stereo','broad')]:
  for _,r in final[(final[key]==t[key])&final.has_public_aux].iterrows():
   for endpoint in externalcols:
    if pd.notna(r[endpoint]):retained.append({'level':level,'official_id':t.Molecule_Name,'official_SMILES':t.SMILES,'training_molecule':r.molecule_name,'training_SMILES':r.smiles,'training_request_id':r.request_id,'target':endpoint,'value':r[endpoint]})
pd.DataFrame(retained).to_csv(O/'blind-current-training-public-targets.csv',index=False)
# Reuse actual historical outer-purge tables, compare only with currently retained public-aux rows.
outerrows=[];outercounts=[]
for cohort in ['own750','briford529']:
 R=G/'chemistry-audit/corrected-native-reference/stage/corrected'/cohort;q=pd.read_csv(R/'query.csv');om=imap[imap.source=='official-train.csv'].set_index('Molecule_Name');q['rid']=om.loc[q.Molecule_Name,'request_id'].to_numpy();q['iso']=q.SMILES.map(canonical);q['group']=q.rid.map(find);q['broad']=q.rid.map(audit.parent_uncharged_no_stereo_key);outer=pd.read_csv(R/'prepared/union18.csv');outerids=set(outer.molecule_name)
 for level,key in [('prepared_exact_isomeric','iso'),('approved_equivalence_including_exact','group'),('broader_parent_uncharged_no_stereo','broad')]:
  matches=[]
  for _,t in q.iterrows():
   hit=final[(final[key]==t[key])&final.has_public_aux]
   for _,r in hit.iterrows():
    vals={c:float(r[c]) for c in externalcols if pd.notna(r[c])};entry={'cohort':cohort,'level':level,'official_holdout_id':t.Molecule_Name,'heldout_SMILES':t.SMILES,'public_training_row_id':r.molecule_name,'public_training_row_SMILES':r.smiles,'request_id':r.request_id,'retained_in_corrected_outer_union18':r.molecule_name in outerids,'public_values':json.dumps(vals,sort_keys=True)};outerrows.append(entry);matches.append(entry)
  outercounts.append({'cohort':cohort,'holdout_n':len(q),'level':level,'heldout_molecules_with_public_aux_in_full_table':len({z['official_holdout_id'] for z in matches}),'matching_public_rows_in_full_table':len(matches),'still_retained_in_outer':sum(z['retained_in_corrected_outer_union18'] for z in matches),'purged_from_outer':sum(not z['retained_in_corrected_outer_union18'] for z in matches)})
pd.DataFrame(outerrows).to_csv(O/'outer-public-availability-detail.csv',index=False);pd.DataFrame(outercounts).to_csv(O/'outer-public-availability-summary.csv',index=False)
# Actually retrieved typed P4 records: do not treat broad graph resemblance as direct assay identity.
p4=json.loads((P/'p4-data/expanded-activity-occurrences.json').read_text());typed=[]
for item in p4:
 a=item['activity'];key=canonical(a.get('canonical_smiles'))
 for _,t in test[test.iso==key].iterrows():typed.append({'official_id':t.Molecule_Name,'activity':a})
(O/'p4-typed-exact-blind-matches.json').write_text(json.dumps(typed,indent=2)+'\n')
summary={'blind_n':len(test),'raw_chEMBL_rows':len(chembl),'raw_PubChem_rows':len(pub),'prepared_source_graphs_outside_request_queue':{s:len({r['prepared_iso'] for r in records if r['source']==s and r['request_id'] is None}) for s in ['ChEMBL_aggregate','PubChem_Veith']},'blind_coverage':counts,'retained_blind_target_cells_by_level':pd.DataFrame(retained).groupby('level').size().to_dict() if retained else {},'outer_availability':outercounts,'p4_typed_exact_blind_records':len(typed),'scope':'existingcachedrecords only; noquery/newdata/inference; broadconnectivity notchemicalidentity; publicvalues nothiddenchallengevalues','source_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [F/'official-test.csv',raw/'chembl_all_isoforms.csv',raw/'pubchem_all_isoforms.csv',P/'p7/stage/table.csv',A/'molecule-input-audit.csv',A/'tautomer-pair-chemical-details.csv',P/'p4-data/expanded-activity-occurrences.json',Path(__file__)]}};(O/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
