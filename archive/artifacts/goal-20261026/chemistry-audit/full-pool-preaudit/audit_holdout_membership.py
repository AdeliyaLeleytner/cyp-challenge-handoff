from pathlib import Path
import pandas as pd,json,hashlib
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize
ROOT=Path(__file__).resolve().parent
DATA=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-briford-holdouts-20261024/remote/holdouts')
mapdf=pd.read_csv(ROOT/'id-map-snapshot.csv',keep_default_na=False)
requests=pd.read_csv(ROOT/'molecule-input-audit.csv',keep_default_na=False).set_index('request_id')
pairs=pd.read_csv(ROOT/'tautomer-pairs-frozen-holdouts.csv',keep_default_na=False)
normalizer=rdMolStandardize.Normalizer();uncharger=rdMolStandardize.Uncharger()
te=rdMolStandardize.TautomerEnumerator();te.SetRemoveSp3Stereo(False);te.SetRemoveBondStereo(False)
def normtaut(s):
 m=normalizer.normalize(Chem.MolFromSmiles(s));m=uncharger.uncharge(m)
 r=te.Enumerate(m)
 return Chem.MolToSmiles(te.PickCanonical(r),isomericSmiles=True),str(r.status)
def stereo(s):
 m=Chem.MolFromSmiles(s)
 return len([1 for _,tag in Chem.FindMolChiralCenters(m,includeUnassigned=True,useLegacyImplementation=False) if tag!='?']),sum(b.GetStereo() not in (Chem.BondStereo.STEREONONE,Chem.BondStereo.STEREOANY) for b in m.GetBonds())
relations=[]
for row in pairs.to_dict('records'):
 ids=row['request_ids'].split(';');official=[x for x in ids if requests.loc[x,'category']=='official_train'][0];external=[x for x in ids if requests.loc[x,'category']=='external_only'][0]
 left=requests.loc[official,'SMILES'];right=requests.loc[external,'SMILES'];lk,ls=normtaut(left);rk,rs=normtaut(right)
 row.update(official_request_id=official,external_request_id=external,official_smiles=left,external_smiles=right,stereo_preserving_tautomer_key_equal=lk==rk,official_normalization_status=ls,external_normalization_status=rs,official_specified_stereocenters=stereo(left)[0],external_specified_stereocenters=stereo(right)[0],official_stereo_bonds=stereo(left)[1],external_stereo_bonds=stereo(right)[1],official_stereo_preserving_tautomer_key=lk,external_stereo_preserving_tautomer_key=rk)
 relations.append(row)
pd.DataFrame(relations).to_csv(ROOT/'tautomer-pair-chemical-details.csv',index=False)
observations=[];file_checks=[]
for cohort in ['own750','briford529']:
 for member in ['union18','mtaux8','2d6isoform6','2d6single']:
  path=DATA/cohort/'prepared'/f'{member}.csv';spec=json.loads(path.with_suffix('.json').read_text());digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==spec['data_sha256']
  df=pd.read_csv(path,keep_default_na=False);targets=spec['targets'];names=set(df.molecule_name)
  file_checks.append({'cohort':cohort,'member':member,'path':str(path),'sha256':digest,'rows':len(df),'spec_hash_matches':True})
  for relation in relations:
   if relation[cohort]!='outer_holdout':continue
   aliases=mapdf[(mapdf.request_id==relation['external_request_id'])&(mapdf.source==member)]
   for alias in aliases.to_dict('records'):
    found=df[df.molecule_name==alias['Molecule_Name']]
    for row in found.to_dict('records'):
     expected=Chem.MolToSmiles(Chem.MolFromSmiles(relation['external_smiles']),isomericSmiles=True)
     actual=Chem.MolToSmiles(Chem.MolFromSmiles(row['smiles']),isomericSmiles=True)
     values={t:row[t] for t in targets if row[t]!='' and pd.notna(row[t])}
     observations.append({'cohort':cohort,'member':member,'heldout_official_id':relation['official_ids'],'training_molecule_name':row['molecule_name'],'external_request_id':relation['external_request_id'],'source_smiles_match':expected==actual,'stereo_preserving_tautomer_key_equal':relation['stereo_preserving_tautomer_key_equal'],'nonmissing_endpoints':list(values),'values':values,'heldout_smiles':relation['official_smiles'],'training_smiles':row['smiles']})
(ROOT/'frozen-pool-tautomer-membership.json').write_text(json.dumps({'verified_prepared_files':file_checks,'retained_training_aliases_of_outer_holdout_tautomers':observations},indent=2)+'\n')
flat=[]
for x in observations:
 for endpoint,value in x['values'].items():flat.append({k:v for k,v in x.items() if k not in ('values','nonmissing_endpoints')}|{'endpoint':endpoint,'value':value})
pd.DataFrame(flat).to_csv(ROOT/'frozen-pool-tautomer-endpoints.csv',index=False)
summary={'tautomer_pairs':len(relations),'stereo_preserving_normalization_equal':sum(x['stereo_preserving_tautomer_key_equal'] for x in relations),'pairs_with_stereo_specification_difference':[x['official_ids'] for x in relations if x['official_specified_stereocenters']!=x['external_specified_stereocenters'] or x['official_stereo_bonds']!=x['external_stereo_bonds']],'retained_alias_rows':len(observations),'retained_by_cohort':{c:len([x for x in observations if x['cohort']==c]) for c in ['own750','briford529']},'unique_heldout_ids_by_cohort':{c:sorted({x['heldout_official_id'] for x in observations if x['cohort']==c}) for c in ['own750','briford529']}}
(ROOT/'frozen-pool-tautomer-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
