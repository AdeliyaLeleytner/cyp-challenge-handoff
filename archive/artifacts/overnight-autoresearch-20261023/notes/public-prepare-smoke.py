"""Synthetic CPU data-preparation smoke; no network and no model fitting."""
import sys, json, tempfile, hashlib
from pathlib import Path
import pandas as pd
R=Path('/Users/adeliyaleleytner/.local/share/openresearch/projects/cyp-chemeleon-baseline-20261023')
sys.path.insert(0,str(R))
import night.public_prepare as prep
from night.public_data import _base_record, normalize_and_exclude, PublicDataError
checks=[]
raw=pd.DataFrame([_base_record(source=s,source_version='fixture-v1',assay_id='fixture',
    record_id=str(i),compound_id=str(i),SMILES='CCC',target='CYP2D6',endpoint=e,
    task_kind='regression',relation='=',p_relation='=',value=100.,units='nM',
    raw_value='100',p_activity=7.,is_point_eligible=True,is_censored=False)
    for i,(s,e) in enumerate([('pubchem_tox21_cyp','AC50'),('bindingdb_native_articles','IC50')])])
tidy,_=normalize_and_exclude(raw,())
assert prep.assess_quality(tidy,list(prep.SOURCE_NAMES),{'CCO','CCN'})['passed']
assert not prep.assess_quality(tidy,list(prep.SOURCE_NAMES),{'CCC'})['passed']
assert not prep.assess_quality(tidy.assign(p_activity=float('inf')),list(prep.SOURCE_NAMES),set())['passed']
checks.append('quality_schema_nonfinite_and_exclusion_gates')
with tempfile.TemporaryDirectory(prefix='cyp-prep-smoke-') as tmp:
 root=Path(tmp)
 (root/'cohorts.json').write_text(json.dumps({'excluded_parent_keys':['CCO','CCN']}))
 for filename,smiles in [('official-train.csv','CCO'),('official-test.csv','CCN')]:
  pd.DataFrame({'Molecule_Name':['fixture'],'SMILES':[smiles]}).to_csv(root/filename,index=False)
 excluded,meta=prep.official_exclusions(root);assert excluded=={'CCO','CCN'}
 original=prep.load_public_data
 def fake_loader(asset_root,**kwargs):
  assert kwargs['excluded_parent_keys']==excluded
  return tidy,{'fixture':True}
 prep.load_public_data=fake_loader
 try:
  result=prep.prepare(root,parquet=False)
 finally:prep.load_public_data=original
 assert result['data_quality']['passed'] and len(result['auxiliary_heads'])==2
 out=root/'new_public'
 assert all((out/name).exists() for name in ['manifest.json','overlap.json','data_quality.json','measurements.csv','auxiliary_wide.csv'])
 assert len(pd.read_csv(out/'measurements.csv'))==2
 assert json.loads((out/'data_quality.json').read_text())['status']=='pass'
 (root/'cohorts.json').write_text(json.dumps({'excluded_parent_keys':['CCO']}))
 try:prep.official_exclusions(root);raise AssertionError('incomplete exclusions passed')
 except PublicDataError:pass
 checks.append('official_exclusion_coverage_and_atomic_preparation_outputs')
result={'passed':True,'checks':checks,'live_network_calls':0,'model_training':False,
 'source_sha256':hashlib.sha256((R/'night/public_prepare.py').read_bytes()).hexdigest()}
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
