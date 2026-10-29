from pathlib import Path
from functools import lru_cache
import json,pandas as pd,numpy as np,re,hashlib,datetime
from rdkit import Chem,RDLogger
RDLogger.DisableLog('rdApp.*')
P=Path(__file__).resolve().parent;O=P/'inventory';O.mkdir(exist_ok=True);oldroot=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024');raw=oldroot/'fullfit-strae-prep/stage/original_full/raw'
@lru_cache(None)
def canon(s):
 if not isinstance(s,str) or not s:return None
 m=Chem.MolFromSmiles(s);return Chem.MolToSmiles(m,isomericSmiles=True) if m else None
assays={a['assay_chembl_id']:a for v in json.loads((P/'assay-selection.json').read_text()).values() for a in v['assays']};assays.update({a['assay_chembl_id']:a for v in json.loads((P/'round2/PLAN.json').read_text())['contexts'].values() for a in v['assays']})
p=P/'metadata/control-assays.json'
if p.exists():assays.update({a['assay_chembl_id']:a for a in json.loads(p.read_text())['assays']})
docs={}
for p in (P/'metadata').glob('documents-*.json'):docs.update({d['document_chembl_id']:d for d in json.loads(p.read_text())['documents']})
sources={}
for p in (P/'metadata').glob('source-*.json'):
 d=json.loads(p.read_text());sources[str(d['src_id'])]=d
occ=json.loads((P/'expanded-activity-occurrences.json').read_text());rows=[]
for r in occ:
 a=r['activity'];assay=assays.get(a['assay_chembl_id'],{});doc=docs.get(a['document_chembl_id'],{});desc=assay.get('description',a.get('assay_description','')) or '';lower=desc.lower();row={k:(json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v) for k,v in a.items()};row.update({k:r.get(k,1 if k=='retrieval_round' else '') for k in ['retrieval_round','retrieval_context','retrieval_page','retrieval_url']});row.update({'assay_'+k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in assay.items() if k not in ['assay_chembl_id','description']});row['assay_description_exact']=desc;row.update({'doc_'+k:v for k,v in doc.items() if not isinstance(v,(dict,list))});row['source_registry']=json.dumps(sources.get(str(a['src_id']),{}),sort_keys=True);row['isomeric_graph']=canon(a.get('canonical_smiles'))
 probes=[s for s in ['DBOMF','midazolam','testosterone','dextromethorphan','bufuralol'] if s.lower() in lower];row['probe_mentions']='|'.join(probes) or 'unknown';row['preparation_mentions']='|'.join(s for s in ['microsom','recombinant','bactosom','supersom','insect','baculosom','hepatocyte','cDNA'] if s.lower() in lower) or 'unknown';row['concentration_mentions_unassigned']='|'.join(re.findall(r'\b[\d.]+\s*(?:nM|uM|microM|mM|µM|μM)\b',desc));row['time_mentions_unassigned']='|'.join(re.findall(r'\b[\d.]+\s*(?:mins?|minutes?|hrs?|hours?)\b',desc,re.I));row['NADPH_mention']='NADPH' in desc.upper();row['in_silico_flag']=bool(re.search(r'in.silico|predict(?:ed|ion)|docking',lower));row['curation_control']='curation_control' in r['retrieval_context'];row['source_structure_scope']='ChEMBL reported canonical structure; physical assay formulation not established'
 try:v=float(a['standard_value'])
 except (TypeError,ValueError):v=np.nan
 factors={'nM':1e-9,'uM':1e-6,'µM':1e-6,'mM':1e-3,'M':1.};factor=factors.get(a.get('standard_units'));row['derived_p_concentration']=float(-np.log10(v*factor)) if factor and np.isfinite(v) and v>0 else np.nan;rel=a.get('standard_relation');row['p_relation']={'=':'=','>':'<','>=':'<=','<':'>','<=':'>='}.get(rel,'unmapped');reasons=[]
 for bad,label in [(row['curation_control'],'curation_control'),(a['standard_type']!='IC50','not_IC50'),(rel!='=','not_exact_relation'),(not np.isfinite(row['derived_p_concentration']),'missing_or_invalid_value_unit'),(not row['isomeric_graph'],'unparseable_structure'),(bool(a.get('data_validity_comment')),'source_validity_flag'),(bool(a.get('potential_duplicate')),'potential_duplicate'),(row['in_silico_flag'],'nonexperimental_text'),(assay.get('assay_organism')!='Homo sapiens','assay_species_not_confirmed_human'),(assay.get('confidence_score')!=9,'not_confidence9')]:
  if bad:reasons.append(label)
 row['exact_comparison_eligible']=not reasons;row['review_or_other_factor_reasons']='|'.join(reasons);rows.append(row)
d=pd.DataFrame(rows);assert len(d)==d.activity_id.nunique()<=3000
paths={'queue':oldroot/'admetlab-auto/data/molecules.csv','old_chembl':raw/'chembl_all_isoforms.csv','old_pubchem':raw/'pubchem_all_isoforms.csv','official_train':raw/'inhibition.csv','official_test':raw.parent/'official-test.csv'};tabs={k:pd.read_csv(p) for k,p in paths.items()};maps={}
for k,t in tabs.items():
 col='SMILES' if 'SMILES' in t else 'smiles';maps[k]={canon(s) for s in t[col].dropna()};maps[k].discard(None)
for k in ['old_chembl','old_pubchem']:maps[k+'_original']={canon(s) for s in tabs[k].orig_smiles.dropna()};maps[k+'_original'].discard(None)
for k,vals in maps.items():d['in_'+k+'_graph']=d.isomeric_graph.isin(vals)
d['in_old_chembl_id']=d.molecule_chembl_id.isin(tabs['old_chembl'].chembl_id)
d.to_csv(O/'activity-inventory.csv',index=False)
a=pd.DataFrame([assays[i] for i in sorted(set(d.assay_chembl_id))]);a.to_json(O/'assay-inventory.json',orient='records',indent=2);pd.DataFrame(docs.values()).to_json(O/'document-inventory.json',orient='records',indent=2)
comp=d.groupby(['molecule_chembl_id','isomeric_graph'],dropna=False).agg(records=('activity_id','size'),contexts=('retrieval_context',lambda x:'|'.join(sorted(set(x)))),eligible_exact=('exact_comparison_eligible','sum'),**{c:(c,'max') for c in d if c.startswith('in_')}).reset_index();comp.to_csv(O/'compound-inventory.csv',index=False)
e=d[d.exact_comparison_eligible].copy();e['compound_target_total_record_weight']=1.;e['record_weight']=1/e.groupby(['isomeric_graph','target_chembl_id']).activity_id.transform('size');e.to_csv(O/'proposed-exact-matched-records.csv',index=False)
# A physical probe-context comparison must inspect actual mentions, not retrieval bucket alone.
cross=[]
for (g,t),sub in e.groupby(['isomeric_graph','target_chembl_id']):
 if sub.probe_mentions.nunique()>1:
  for _,r in sub.iterrows():cross.append(r.to_dict())
pd.DataFrame(cross,columns=e.columns).to_csv(O/'exact-cross-probe-records.csv',index=False)
summary={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'activity_records':len(d),'main_IC50':int((~d.curation_control).sum()),'control_records':int(d.curation_control.sum()),'unique_compound_ids':d.molecule_chembl_id.nunique(),'unique_isomeric_graphs':d.isomeric_graph.nunique(),'unparseable_records':int(d.isomeric_graph.isna().sum()),'assays_with_records':d.assay_chembl_id.nunique(),'documents':d.document_chembl_id.nunique(),'missing_assay_metadata':sorted(set(d.assay_chembl_id)-set(assays)),'missing_document_metadata':sorted(set(d.document_chembl_id)-set(docs)),'context_counts':d.groupby('retrieval_context').size().to_dict(),'main_relations':d[~d.curation_control].standard_relation.fillna('missing').value_counts().to_dict(),'main_units':d[~d.curation_control].standard_units.fillna('missing').value_counts().to_dict(),'eligibility_reason_counts':d.review_or_other_factor_reasons.str.split('|').explode().value_counts().to_dict(),'exact_eligible_records':len(e),'exact_compound_targets':e.groupby(['isomeric_graph','target_chembl_id']).ngroups,'exact_cross_probe_compound_targets':pd.DataFrame(cross).groupby(['isomeric_graph','target_chembl_id']).ngroups if cross else 0,'exact_cross_probe_records':len(cross),'main_graph_overlap':{k:int(d.loc[~d.curation_control & d['in_'+k+'_graph'],'isomeric_graph'].nunique()) for k in maps},'main_unique_graphs':d.loc[~d.curation_control,'isomeric_graph'].nunique(),'main_new_graphs_beyond_original_sources':len(set(d.loc[~d.curation_control,'isomeric_graph'].dropna())-maps['old_chembl_original']-maps['old_pubchem_original']),'input_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*paths.values(),P/'expanded-activity-occurrences.json',Path(__file__)]},'no_fits':True,'no_automatic_molecule_standardization':True,'eligibility_is_proposal_not_training_authorization':True}
(O/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
