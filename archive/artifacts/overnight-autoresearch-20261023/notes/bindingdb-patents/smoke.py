"""Synthetic patent adapter smoke; no HTTP, model training, or large files."""
import sys,io,json,tempfile,hashlib
from pathlib import Path
import pandas as pd
REPO=Path('/Users/adeliyaleleytner/.local/share/openresearch/projects/cyp-chemeleon-baseline-20261023')
sys.path.insert(0,str(REPO))
import night.bindingdb_patents as p
from night.public_data import normalize_and_exclude
header=['BindingDB Reactant_set_id','Ligand SMILES','BindingDB MonomerID','Target Name',
 'Target Source Organism According to Curator or DataSource','Curation/DataSource','IC50 (nM)',
 'Ki (nM)','Number of Protein Chains in Target (N>1 implies a multichain complex)',
 'UniProt (SwissProt) Primary ID of Target Chain 1','Patent Number','Article DOI']
rows=[['1','CCC','101','Cytochrome P450 2D6','Homo sapiens','US Patent','100','>20','1','P10635','US123456B2','10.fake/article'],
 ['2','CCN','102','Cytochrome P450 3A4','Homo sapiens','US Patent','<1000','','1','P08684','US456789B2',''],
 ['3','CCCC','103','Cytochrome P450 3A4','Homo sapiens','BindingDB','100','','1','P08684','',''],
 ['4','CCCC','104','Cytochrome P450 3A4','Mus musculus','US Patent','100','','1','P08684','US000001B2',''],
 ['5','CCCCC','105','CYP2D6','Homo sapiens','US Patent','100','','2','P10635','US000002B2',''],
 ['6','CCO','106','CYP2D6','Homo sapiens','US Patent','100','','1','P10635','US000003B2','']]
text='\t'.join(header)+'\n'+'\n'.join('\t'.join(row) for row in rows)+'\n'
raw,a=p.parse_patents_stream(io.StringIO(text))
assert len(raw)==4 and set(raw.source)=={'bindingdb_patents'} and a['measurements_missing_patent_number']==1
assert a['excluded_nonhuman_rows']==1 and a['excluded_multichain_rows']==1
assert raw.loc[raw.record_id=='1:IC50','document_id'].iloc[0]=='PATENT:US123456B2'
assert json.loads(raw.provenance_json.iloc[0])['Article DOI']=='10.fake/article'
assert raw.loc[raw.record_id=='1:Ki','p_relation'].iloc[0]=='<'
assert raw.loc[raw.record_id=='2:IC50','p_relation'].iloc[0]=='>'
checks=['patent_scope_provenance_exact_target_and_endpoint_relations']
with tempfile.TemporaryDirectory(prefix='cyp-patents-smoke-') as tmp:
 root=Path(tmp);(root/'cohorts.json').write_text(json.dumps({'excluded_parent_keys':['CCO','CCN']}))
 for filename,smiles in [('official-train.csv','CCO'),('official-test.csv','CCN')]:
  pd.DataFrame({'Molecule_Name':['fixture'],'SMILES':[smiles]}).to_csv(root/filename,index=False)
 (root/'new_public').mkdir();(root/'new_public/sentinel').write_text('initial source must stay unchanged')
 original=p.load_bindingdb_patents;p.load_bindingdb_patents=lambda *args,**kwargs:(raw,a)
 try:m=p.prepare_patents(root,parquet=False)
 finally:p.load_bindingdb_patents=original
 assert m['data_quality']['passed'] and m['table']['rows']==2 and len(m['auxiliary_heads'])==1
 assert m['exclusion_audit']['excluded_official_parent_records']==2
 assert (root/'new_public/sentinel').read_text()=='initial source must stay unchanged'
 assert set(x.name for x in (root/'new_public').iterdir())=={'sentinel'}
 assert (root/'new_public_patents/manifest.json').exists()
 checks.append('all_official_parent_purge_and_isolated_output_folder')
result={'passed':True,'checks':checks,'live_network_calls':0,'source_sha256':hashlib.sha256((REPO/'night/bindingdb_patents.py').read_bytes()).hexdigest()}
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
