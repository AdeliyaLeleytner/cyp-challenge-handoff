"""Tiny synthetic parser/cache smoke tests; no live HTTP, model fitting or GPU."""
from pathlib import Path
import sys,io,json,hashlib,tempfile,zipfile,urllib.error
import numpy as np,pandas as pd
R=Path('/Users/adeliyaleleytner/.local/share/openresearch/projects/cyp-chemeleon-baseline-20261023');sys.path.insert(0,str(R))
from night.public_data import (CachedHTTP,PublicDataError,normalize_parent_key,normalize_and_exclude,
 parse_measurement,to_p_activity,parse_tox21_frame,parse_bindingdb_stream,wide_auxiliary_table,_join_bindingdb_assays,
 build_public_auxiliary_dataset)
checks=[]
assert parse_measurement('> 10')==('>',10.)
assert to_p_activity(100,'nM','=')==(7.,'=')
assert to_p_activity(10,'uM','>')==(5.,'<')
assert to_p_activity(-6,'log10(M)','<=')==(6.,'>=')
assert to_p_activity(0,'nM')[0] is None
checks.append('units_and_inequality_reversal')
assert normalize_parent_key('CCO.[Na+]')==normalize_parent_key('CCO')
f,a=normalize_and_exclude(pd.DataFrame({'SMILES':['CCO','CCO.[Na+]','CCN','badsmiles']}),(v for v in ['CCO']))
assert f.SMILES.tolist()==['CCN'] and a['invalid_structure_records']==1 and a['excluded_official_parent_records']==2
left='F[C@H](Cl)Br';right='F[C@@H](Cl)Br';assert normalize_parent_key(left)==normalize_parent_key(right)
checks.append('normalization_exclusion_generator_and_stereo_parent')
desc={'aid':{'id':1671196,'version':1},'aid_source':{'db':{'name':'824'}},'results':[
 {'name':'Fit_LogAC50-Replicate_1','description':['The logarithm of AC50 calculated based on Molar Units.']},
 {'name':'Potency-Replicate_1','unit':5}]}
raw=pd.DataFrame([
 {'PUBCHEM_SID':'1','PUBCHEM_CID':'10','PUBCHEM_RESULT_TAG':'1','PUBCHEM_ACTIVITY_OUTCOME':'Active','Fit_LogAC50-Replicate_1':'-6','Phenotype-Replicate_1':'Inhibitor'},
 {'PUBCHEM_SID':'2','PUBCHEM_CID':'11','PUBCHEM_RESULT_TAG':'2','PUBCHEM_ACTIVITY_OUTCOME':'Inactive','Fit_LogAC50-Replicate_1':'-2','Phenotype-Replicate_1':'Inactive'},
 {'PUBCHEM_SID':'3','PUBCHEM_CID':'12','PUBCHEM_RESULT_TAG':'3','PUBCHEM_ACTIVITY_OUTCOME':'Inconclusive','Potency-Replicate_1':'25','Phenotype-Replicate_1':'Inconclusive'},
 {'PUBCHEM_SID':'4','PUBCHEM_CID':'13','PUBCHEM_RESULT_TAG':'4','PUBCHEM_ACTIVITY_OUTCOME':'Active','Potency-Replicate_1':'>10','Phenotype-Replicate_1':'Inhibitor'}])
tidy,a=parse_tox21_frame(raw,desc,{10:'CCO',11:'CCN',12:'CCC',13:'CCCC'},'CYP2D6')
assert len(tidy)==8
pot=tidy.loc[tidy.endpoint=='AC50'].set_index('compound_id')
assert pot.loc['CID:10','p_activity']==6 and pot.loc['CID:10','is_point_eligible']
assert not pot.loc['CID:11','is_point_eligible'] and not pot.loc['CID:12','is_point_eligible']
assert pot.loc['CID:13','p_relation']=='<' and not pot.loc['CID:13','is_point_eligible']
unknown=tidy.loc[(tidy.endpoint=='activity_outcome')&(tidy.compound_id=='CID:12'),'value'].iloc[0];assert pd.isna(unknown)
unknown_desc={**desc,'results':[{'name':'Fit_LogAC50-Replicate_1','description':['Unknown logarithmic units']} ]}
u,_=parse_tox21_frame(raw.iloc[:1],unknown_desc,{10:'CCO'},'CYP2D6');u=u.loc[u.endpoint=='AC50'].iloc[0];assert pd.isna(u.p_activity) and u.units=='unverified_log10'
micro_desc={**desc,'results':[{'name':'Fit_LogAC50-Replicate_1','description':['Calculated in micromolar units']}]}
u,_=parse_tox21_frame(raw.iloc[:1],micro_desc,{10:'CCO'},'CYP2D6');assert pd.isna(u.loc[u.endpoint=='AC50','p_activity'].iloc[0])
checks.append('tox21_replicates_qc_unknowns_and_unverified_units')
headers=['BindingDB Reactant_set_id','Ligand SMILES','BindingDB MonomerID','Target Name','Target Source Organism According to Curator or DataSource','Curation/DataSource','IC50 (nM)','Ki (nM)','Number of Protein Chains in Target (N>1 implies a multichain complex)','UniProt (SwissProt) Primary ID of Target Chain 1','Article DOI']
rows=[['1','CCO','101','CYP2D6','Homo sapiens','BindingDB','100','>20','1','P10635','10.fake/a'],
 ['2','CCN','102','CYP3A4','Homo sapiens','BindingDB','<1000','','1','P08684','10.fake/b'],
 ['3','CCC','103','CYP3A4','Mus musculus','BindingDB','100','','1','P08684',''],
 ['4','CCCC','104','CYP2D6','Homo sapiens','ChEMBL','100','','1','P10635',''],
 ['5','CCCCC','105','CYP2D6','Homo sapiens','BindingDB','100','','2','P10635','']+['extra','chain'],
 ['6','CCCCCC','106','CYP2D6','Homo sapiens','BindingDB','100','','1','',''],
 ['7','COC','107','CYP1A2','Homo sapiens','BindingDB','not measured','','1','P05177','']]
text='\t'.join(headers)+'\n'+'\n'.join('\t'.join(r) for r in rows)+'\n'
bdb,a=parse_bindingdb_stream(io.StringIO(text));assert len(bdb)==3 and set(bdb.endpoint)=={'IC50','Ki'}
assert a['extra_chain_tail_rows']==1 and a['excluded_multichain_rows']==1 and a['excluded_nonhuman_rows']==1 and a['excluded_imported_source_rows']==1 and a['invalid_numeric_cells']==1
assert bdb.loc[bdb.record_id=='2:IC50','p_relation'].iloc[0]=='>'
checks.append('bindingdb_variable_chain_tail_native_target_and_endpoint_separation')
clean,_=normalize_and_exclude(pd.concat([tidy,bdb],ignore_index=True),set());wide,names,meta=wide_auxiliary_table(clean)
assert len(names)==2 and not any('Ki_' in n for n in names) and wide.shape[0]==1
assert meta['records_used']==2 and set(meta['heads'][n]['endpoint'] for n in names)=={'AC50','IC50'}
checks.append('wide_equality_only_source_assay_heads')
with tempfile.TemporaryDirectory(prefix='cyp-public-data-smoke-') as tmp:
 root=Path(tmp)
 class Response(io.BytesIO):
  headers={'Content-Type':'text/plain'}
 calls=[]
 def opener(req,timeout):calls.append(req.full_url);return Response(b'fixture-content')
 c=CachedHTTP(root/'cache',min_interval=0,opener=opener);url='https://pubchem.ncbi.nlm.nih.gov/fixture'
 p=c.fetch(url,'source/v1/example.txt');assert p.read_bytes()==b'fixture-content'
 c.fetch(url,'source/v1/example.txt');assert len(calls)==1
 p.write_bytes(b'corrupted')
 try:c.fetch(url,'source/v1/example.txt');raise AssertionError('corruption not detected')
 except PublicDataError:pass
 try:c.fetch('https://private-bucket.s3.amazonaws.com/foo','not-public');raise AssertionError('private source not rejected')
 except PublicDataError:pass
 try:c.fetch(url,'bad-checksum',expected_sha256='0'*64);raise AssertionError('bad hash not detected')
 except PublicDataError:pass
 assert not (root/'cache/bad-checksum').exists() and not list((root/'cache').glob('.bad-checksum.*'))
 mp=root/'mapping.zip';ap=root/'assays.zip'
 with zipfile.ZipFile(mp,'w') as z:z.writestr('map.tsv','ReactantSet\tEntry_Assay\n1\t100_2\n')
 with zipfile.ZipFile(ap,'w') as z:z.writestr('assays.tsv','Entry\tAssay\tDescription\n100\t2\tSynthetic enzyme assay fixture\n')
 joined,ja=_join_bindingdb_assays(bdb,mp,ap);assert ja['assay_mapped_measurements']==2 and joined.loc[joined.record_id=='1:IC50','assay_id'].iloc[0]=='BDB_ASSAY_100_2'
 checks.append('atomic_http_cache_corruption_detection_public_allowlist_and_assay_join')
base=pd.DataFrame({'Molecule_Name':['z','a'],'SMILES':['CCN','CCO.[Na+]'],'primary':[4.,np.nan]})
pub=pd.concat([clean,clean.loc[clean.endpoint=='AC50'].iloc[[0]].assign(SMILES='CCCCCCC',canonical_smiles='CCCCCCC',parent_key='CCCCCCC')],ignore_index=True)
joined,heads,meta=build_public_auxiliary_dataset(base,pub,excluded_parent_keys={'CCO','CCN'},primary_columns=['primary'])
assert joined.Molecule_Name.iloc[:2].tolist()==['z','a'] and joined.SMILES.iloc[:2].tolist()==base.SMILES.tolist()
assert joined.primary.iloc[0]==4 and joined.primary.iloc[1:].isna().all()
assert len(joined)==3 and joined.parent_key.iloc[-1]=='CCCCCCC' and joined[heads].iloc[:2].isna().all().all()
assert meta['official_rows_with_auxiliary_labels']==0 and meta['public_only_net_new_parents']==1
attached,heads,meta=build_public_auxiliary_dataset(base,pub,excluded_parent_keys=(),primary_columns=['primary'])
assert len(attached)==3 and meta['official_rows_with_auxiliary_labels']==1
empty,heads,meta=build_public_auxiliary_dataset(base,pub.iloc[:0],excluded_parent_keys={'CCO','CCN'},primary_columns=['primary'])
assert len(empty)==2 and heads==[] and meta['public_only_rows']==0
try:
 build_public_auxiliary_dataset(base.assign(Molecule_Name=['a','a']),pub,excluded_parent_keys=(),primary_columns=['primary'])
 raise AssertionError('duplicate official ID not rejected')
except PublicDataError:pass
checks.append('auxiliary_join_preserves_official_order_labels_public_only_exclusion_and_empty_corpus')
result={'passed':True,'checks':checks,'live_network_calls':0,'model_training':False,'source_sha256':hashlib.sha256((R/'night/public_data.py').read_bytes()).hexdigest()}
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
