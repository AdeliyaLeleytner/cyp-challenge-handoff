from pathlib import Path
import json,pickle,hashlib
import pandas as pd,numpy as np
from concurrent.futures import ProcessPoolExecutor
from analyse import normalize
P=Path(__file__).resolve().parent;T=P/'tables';A=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/remote/assets');OLD=Path('/Users/adeliyaleleytner/.local/share/cyp-inhibition/reciprocal-comparison-20261023/full/vendor/data/external')
def main():
 files=[A/'new_public/measurements.csv',A/'new_public_patents/measurements.csv',OLD/'cyp_chembl.csv',OLD/'pubchem_cyp_qhts_aid1851.csv']
 frames={str(f):pd.read_csv(f) for f in files};cache=pickle.loads((P/('structure_cache_all_raw.pkl' if (P/'structure_cache_all_raw.pkl').exists() else 'structure_cache_v2.pkl')).read_bytes());allsmiles=set()
 for f,d in frames.items():allsmiles.update(d['SMILES' if 'SMILES' in d else 'smiles'].dropna())
 missing=sorted(allsmiles-set(cache));print('raw additional SMILES',len(missing),flush=True)
 if missing:
  with ProcessPoolExecutor(max_workers=4) as pool:
   for r in pool.map(normalize,missing,chunksize=100):cache[r['smiles']]=r
 (P/'structure_cache_all_raw.pkl').write_bytes(pickle.dumps(cache));dsc=pd.DataFrame(cache.values())
 sources={};labels=[];summary=[]
 for fp,d in frames.items():
  d=d.rename(columns={'SMILES':'smiles'}).merge(dsc,on='smiles',how='left',validate='many_to_one')
  if 'endpoint' in d:
   for source,z in d.groupby('source'):
    name='Raw_'+source;sources[name]=z
    for (g,ep,rel),q in z.groupby(['target','endpoint','relation'],dropna=False):
     vals=pd.to_numeric(q.p_activity,errors='coerce');labels.append({'dataset':name,'gene':g,'endpoint':ep,'relation':str(rel),'records':len(q),'valid_log_values':int(vals.notna().sum()),'eligible_point_records':int(q.is_point_eligible.fillna(False).sum()),'median_log_value':vals.median(),'p_relation':','.join(sorted(q.p_relation.dropna().astype(str).unique())),'p05_log_value':vals.quantile(.05),'p95_log_value':vals.quantile(.95),'min_log_value':vals.min(),'max_log_value':vals.max(),'note':'Replicates retained; eligibility depends on source quality and endpoint. This table includes records not used for training.'})
    summary.append({'dataset':name,'records_or_rows':len(z),'raw_smiles':z.smiles.nunique(),'stereo_structures':z.iso.nunique(),'parents':z.parent.nunique(),'eligible_IC50_AC50_records':int((z.is_point_eligible.fillna(False)&z.endpoint.isin(['IC50','AC50'])).sum()),'censored_records':int(z.is_censored.fillna(False).sum()),'source_file':str(Path(fp).parent.name+'/'+Path(fp).name),'meaning':'Prepared measurement archive; all retained endpoints and outcomes, before training head aggregation'})
  else:
   name='Raw_earlier_ChEMBL' if 'cyp_chembl' in fp else 'Raw_earlier_PubChem';sources[name]=d
   cs=[c for c in d if c.startswith('CYP') and ('PIC50' in c or 'pIC50' in c)]
   for c in cs:
    vals=d[c].dropna();labels.append({'dataset':name,'gene':c.split('_')[0],'endpoint':'pKi' if '_Ki_' in c else ('pIC50' if '_IC50_' in c else 'reported_pIC50'),'relation':'point','records':len(vals),'valid_log_values':len(vals),'eligible_point_records':len(vals),'median_log_value':vals.median(),'p_relation':','.join(sorted(q.p_relation.dropna().astype(str).unique())),'p05_log_value':vals.quantile(.05),'p95_log_value':vals.quantile(.95),'min_log_value':vals.min(),'max_log_value':vals.max(),'note':'Values preserved from archived source; not all columns were selected in prior training.'})
   summary.append({'dataset':name,'records_or_rows':len(d),'raw_smiles':d.smiles.nunique(),'stereo_structures':d.iso.nunique(),'parents':d.parent.nunique(),'eligible_IC50_AC50_records':None,'censored_records':None,'source_file':str(Path(fp).name),'meaning':'Earlier downloaded table before selecting training columns and excluding overlaps'})
 pd.DataFrame(summary).to_csv(T/'raw_archive_comparison.csv',index=False);pd.DataFrame(labels).to_csv(T/'raw_archive_activity_counts.csv',index=False)
 existing=pd.read_csv(T/'all_sources_long.csv.gz');existing=existing[~existing.dataset.eq('User_ChEMBL37')]
 baseline=dsc[dsc.smiles.isin(existing.smiles)];rawall=pd.concat(list(sources.values()),ignore_index=True)
 available=pd.concat([baseline,rawall],ignore_index=True).drop_duplicates('smiles');user=pd.read_csv(T/'user_rows_annotated.csv.gz');td=pd.read_csv(A/'official-test.csv');test=dsc[dsc.smiles.isin(td.SMILES)]
 available[['smiles','iso','parent','iso_key','scaffold','MW','cLogP','TPSA']].to_csv(T/'all_available_structures.csv.gz',index=False,compression='gzip')
 train=dsc[dsc.smiles.isin(pd.read_csv(A/'official-train.csv').SMILES)]
 for row in summary:
  sp=set(sources[row['dataset']].parent.dropna());row.update(MW_median=float(sources[row['dataset']].drop_duplicates('parent').MW.median()),cLogP_median=float(sources[row['dataset']].drop_duplicates('parent').cLogP.median()),TPSA_median=float(sources[row['dataset']].drop_duplicates('parent').TPSA.median()),scaffolds_nonempty=len(set(sources[row['dataset']].scaffold.dropna())-{''}),user_parent_overlap=len(sp&set(user.parent)),train_parent_overlap=len(sp&set(train.parent)),test_parent_overlap=len(sp&set(test.parent)))
 pd.DataFrame(summary).to_csv(T/'raw_archive_comparison.csv',index=False)
 # Exact TEST structures are excluded for novelty, regardless of archive availability.
 allparents=set(available.parent.dropna());alliso=set(available.iso.dropna());all14=set(available.iso_key.dropna().str[:14]);up=set(user.parent);ui=set(user.iso);u14=set(user.iso_key.str[:14]);tp=set(test.parent);t14=set(test.iso_key.str[:14]);ti=set(test.iso)
 user['new_parent_vs_all_raw_excluding_TEST']=~user.parent.isin(allparents|tp);user['new_key14_vs_all_raw_excluding_TEST']=~user.iso_key.str[:14].isin(all14|t14)
 user.to_csv(T/'user_rows_all_archive_membership.csv.gz',index=False,compression='gzip')
 rowstats=[]
 for (task,rel),q in user.groupby(['endpoint','relation']):
  a=q[q.new_parent_vs_all_raw_excluding_TEST];b=q[q.new_key14_vs_all_raw_excluding_TEST];rowstats.append({'task':task,'relation':rel,'rows':len(q),'new_parent_rows':len(a),'new_parents':a.parent.nunique(),'new_key14_rows':len(b),'new_key14':b.iso_key.str[:14].nunique()})
 pd.DataFrame(rowstats).to_csv(T/'novelty_vs_all_raw_archives.csv',index=False)
 out={'scope':'All available raw/prepared CYP sources plus earlier used sources and official tables; not a single training pool. Includes downloaded columns/outcomes not trained.','raw_extra_views':len(sources),'all_available_parent_count':len(allparents),'user_parent_overlap':len(up&allparents),'new_parent_excluding_TEST':len(up-allparents-tp),'all_available_key14_count':len(all14),'user_key14_overlap':len(u14&all14),'new_key14_excluding_TEST':len(u14-all14-t14),'new_stereo_excluding_TEST':len(ui-alliso-ti),'groups':rowstats,'source_views':summary}
 (P/'all_archive_summary.json').write_text(json.dumps(out,indent=2,default=lambda x:x.item())+'\n')
 man=json.loads((P/'source_manifest.json').read_text());paths={x['path'] for x in man}
 for f in files:
  if str(f) not in paths:man.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'rows':len(frames[str(f)]),'columns':list(frames[str(f)])})
 (P/'source_manifest.json').write_text(json.dumps(man,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='source_views'},default=lambda x:x.item()),flush=True)
if __name__=='__main__':main()
