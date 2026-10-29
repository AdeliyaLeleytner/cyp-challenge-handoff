#!/usr/bin/env python3
"""Read-only chemical/identity audit of a self-consistent ADMETlab snapshot.
No molecules are rewritten in source data. Standardizations below classify differences only.
"""
from pathlib import Path
import argparse,ast,csv,datetime as dt,hashlib,io,json,math,platform,sys,time
from collections import Counter,defaultdict
import numpy as np,pandas as pd
from rdkit import Chem,rdBase
from rdkit.Chem import Descriptors,rdMolDescriptors
from rdkit.Chem.MolStandardize import rdMolStandardize

p=argparse.ArgumentParser();p.add_argument('--reuse-snapshot',action='store_true');p.add_argument('--endpoint-types',type=Path,default=Path(__file__).resolve().parent/'endpoint-types.json');p.add_argument('--root',type=Path,default=Path('/Users/adeliyaleleytner/Downloads/ADMETlab-Chrome-direct-500'));p.add_argument('--map',type=Path,default=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/stage/admetlab-id-map.csv'));p.add_argument('--out',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
if a.reuse_snapshot:
 manifest_bytes=(a.out/'collection-manifest.json').read_bytes();manifest=json.loads(manifest_bytes)
 raw_bytes=(a.out/'raw-snapshot.csv').read_bytes();feat_bytes=(a.out/'features-snapshot.csv').read_bytes()
 assert sha(raw_bytes)==manifest['raw_csv_sha256'] and sha(feat_bytes)==manifest['features_sha256']
else:
 for attempt in range(10):
  manifest_bytes=(a.root/'results/all-collected-manifest.json').read_bytes();manifest=json.loads(manifest_bytes)
  raw_bytes=(a.root/'results/all-collected.csv').read_bytes();feat_bytes=(a.root/'results/all-collected-features.csv').read_bytes()
  if manifest_bytes==(a.root/'results/all-collected-manifest.json').read_bytes() and sha(raw_bytes)==manifest['raw_csv_sha256'] and sha(feat_bytes)==manifest['features_sha256']:break
  time.sleep(.5)
 else:raise RuntimeError('Could not obtain a stable snapshot')
for name,body in [('raw-snapshot.csv',raw_bytes),('features-snapshot.csv',feat_bytes),('collection-manifest.json',manifest_bytes)]:
 target=a.out/name
 if target.exists() and target.read_bytes()!=body:raise RuntimeError('Output snapshot already exists with different contents; choose a new --out')
 target.write_bytes(body)
map_bytes=a.map.read_bytes();mapping=pd.read_csv(io.BytesIO(map_bytes),keep_default_na=False)
raw=list(csv.DictReader(io.StringIO(raw_bytes.decode('utf-8-sig'))));features=list(csv.DictReader(io.StringIO(feat_bytes.decode('utf-8-sig'))))
rawcols=list(raw[0]);featcols=list(features[0]);featurecols=[c for c in featcols if c.startswith('ADMETLAB::')]
byfeature={r['SMILES']:r for r in features}
schema_path=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/admetlab-auto/schema.json');schema=json.loads(schema_path.read_text())
charlist=[];issues=[];request_records=[];all_source_records=[];feature_errors=[];alert_index_errors=[];mass=[];categories=Counter();canonical_groups={'request':defaultdict(list),'service':defaultdict(list),'request_no_stereo':defaultdict(list),'service_no_stereo':defaultdict(list)}
parsed={};taut=rdMolStandardize.TautomerEnumerator();uncharger=rdMolStandardize.Uncharger()
def mol(smiles):
 if smiles not in parsed:parsed[smiles]=Chem.MolFromSmiles(smiles)
 return parsed[smiles]
def canon(m,isomeric=True):return Chem.MolToSmiles(m,canonical=True,isomericSmiles=isomeric)
def no_stereo(m):
 q=Chem.Mol(m);Chem.RemoveStereochemistry(q);return canon(q)
def parent(m):return rdMolStandardize.FragmentParent(Chem.Mol(m),skipStandardize=True)
def chirality(m):return {'specified_centers':sum(v!='?' for _,v in Chem.FindMolChiralCenters(m,includeUnassigned=True,useLegacyImplementation=False)),'possible_centers':len(Chem.FindMolChiralCenters(m,includeUnassigned=True,useLegacyImplementation=False)),'stereo_bonds':sum(b.GetStereo() not in (Chem.BondStereo.STEREONONE,Chem.BondStereo.STEREOANY) for b in m.GetBonds())}
def compare(left,right):
 if left is None or right is None:return 'parse_failure'
 if canon(left)==canon(right):return 'same_isomeric_graph'
 if no_stereo(left)==no_stereo(right):return 'stereochemistry_difference'
 if canon(rdMolStandardize.Normalize(Chem.Mol(left)))==canon(rdMolStandardize.Normalize(Chem.Mol(right))):return 'functional_group_normalization_equivalent'
 if canon(parent(left))==canon(parent(right)):return 'fragment_or_salt_difference'
 if no_stereo(uncharger.uncharge(Chem.Mol(left)))==no_stereo(uncharger.uncharge(Chem.Mol(right))):return 'charge_or_protonation_difference'
 if no_stereo(taut.Canonicalize(Chem.Mol(left)))==no_stereo(taut.Canonicalize(Chem.Mol(right))):return 'tautomer_equivalent_under_rdkit'
 return 'other_graph_difference'
map_by_id={k:g for k,g in mapping.groupby('request_id',sort=False)}
for idx,row in enumerate(raw):
 smi=row['raw_smiles'];service=row['smiles'];rid=sha(smi.encode());req=mol(smi);srv=mol(service);feat=byfeature.get(smi);relation=compare(req,srv);categories[relation]+=1
 group=map_by_id.get(rid)
 if group is None:issues.append({'row':idx,'issue':'request_id_not_in_source_map','request_id':rid})
 elif not (group.request_smiles==smi).all():issues.append({'row':idx,'issue':'request_hash_collision_or_map_mismatch','request_id':rid})
 if feat is None:issues.append({'row':idx,'issue':'missing_feature_row','request_id':rid});continue
 if feat['request_id']!=rid or feat['service_smiles']!=service:issues.append({'row':idx,'issue':'feature_identity_mismatch','request_id':rid})
 if req is None or srv is None:issues.append({'row':idx,'issue':'invalid_smiles','request_id':rid});continue
 official=group[group.source.str.startswith('official-')] if group is not None else pd.DataFrame()
 ids=official.Molecule_Name.tolist() if len(official) else []
 for which,m in [('request',req),('service',srv)]:
  canonical_groups[which][canon(m)].append(rid);canonical_groups[which+'_no_stereo'][no_stereo(m)].append(rid)
 details={'row':idx,'request_id':rid,'official_ids':';'.join(ids),'request_smiles':smi,'service_smiles':service,'text_equal':smi==service,'relation':relation,'request_canonical':canon(req),'service_canonical':canon(srv),'request_formula':rdMolDescriptors.CalcMolFormula(req),'service_formula':rdMolDescriptors.CalcMolFormula(srv),'request_formal_charge':Chem.GetFormalCharge(req),'service_formal_charge':Chem.GetFormalCharge(srv),'request_fragments':len(Chem.GetMolFrags(req)),'service_fragments':len(Chem.GetMolFrags(srv)),**{'request_'+k:v for k,v in chirality(req).items()},**{'service_'+k:v for k,v in chirality(srv).items()}}
 charlist.append(details)
 for original in group.to_dict('records') if group is not None else []:
  relation_to_source=compare(mol(original['SMILES']),req)
  all_source_records.append({'Molecule_Name':original['Molecule_Name'],'source':original['source'],'request_id':rid,'original_to_request_relation':relation_to_source})
 for original in official.to_dict('records'):
  om=mol(original['SMILES']);original_relation=compare(om,req)
  request_records.append({'Molecule_Name':original['Molecule_Name'],'source':original['source'],'request_id':rid,'original_smiles':original['SMILES'],'request_smiles':smi,'original_to_request_relation':original_relation,'text_equal':original['SMILES']==smi})
 for col,text in row.items():
  if col in ('raw_smiles','smiles'):continue
  cat,name=schema['web_column_to_endpoint'].get(col,['csv_extra',col]);target='ADMETLAB::'+cat+'::'+name
  if text is None or text.strip()=='':expected=None
  elif text.startswith('['):
   try:items=ast.literal_eval(text);expected=float(sum(x not in (None,'','-') for x in items))
   except (ValueError,SyntaxError,TypeError):feature_errors.append({'row':idx,'request_id':rid,'column':col,'issue':'invalid_rule_list'});continue
   for item in items:
    if item in (None,'','-'):continue
    if not isinstance(item,(tuple,list)) or any(not isinstance(atom,int) or atom<0 or atom>=srv.GetNumAtoms() for atom in item):
     alert_index_errors.append({'request_id':rid,'column':col,'service_atom_count':srv.GetNumAtoms(),'item':repr(item)})
  else:
   try:expected=float(text)
   except ValueError:feature_errors.append({'row':idx,'request_id':rid,'column':col,'issue':'unhandled_nonnumeric_value'});continue
  try:actual=float(feat[target]) if feat[target]!='' else None
  except (KeyError,ValueError):feature_errors.append({'row':idx,'request_id':rid,'column':col,'issue':'missing_or_nonnumeric_feature'});continue
  if expected is None and actual is None:continue
  if expected is None or actual is None or not math.isclose(expected,actual,rel_tol=1e-12,abs_tol=1e-12):feature_errors.append({'row':idx,'request_id':rid,'column':col,'issue':'value_mismatch','expected':expected,'actual':actual})
 if 'MW' in row:
  value=float(row['MW']);exact=Descriptors.ExactMolWt(srv);average=Descriptors.MolWt(srv)
  mass.append({'request_id':rid,'reported_MW':value,'exact_mass':exact,'average_MW':average,'difference_from_rounded_exact_mass':value-round(exact,2),'difference_from_rounded_average_MW':value-round(average,2),'reported_fChar':float(row['fChar']) if 'fChar' in row else None,'rdkit_formal_charge':Chem.GetFormalCharge(srv)})

def write_csv(name,records):
 if not records:(a.out/name).write_text('');return
 columns=list(dict.fromkeys(k for r in records for k in r))
 with (a.out/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(records)
write_csv('molecule-audit.csv',charlist);write_csv('service-structure-differences.csv',[r for r in charlist if r['relation']!='same_isomeric_graph']);write_csv('service-text-differences.csv',[r for r in charlist if not r['text_equal']]);write_csv('original-to-request.csv',request_records);write_csv('all-source-original-relations.csv',all_source_records);write_csv('alert-index-errors.csv',alert_index_errors);write_csv('feature-errors.csv',feature_errors);write_csv('molecular-mass-audit.csv',mass)
duplicates={k:{c:ids for c,ids in groups.items() if len(ids)>1} for k,groups in canonical_groups.items()}
(a.out/'chemical-duplicate-groups.json').write_text(json.dumps(duplicates,indent=2)+'\n')
fdf=pd.DataFrame(features);arr=fdf[featurecols].apply(pd.to_numeric,errors='coerce').to_numpy(dtype=float)
missing_counts={c:int((~np.isfinite(arr[:,i])).sum()) for i,c in enumerate(featurecols) if (~np.isfinite(arr[:,i])).any()}
metcols=[c for c in featurecols if c.startswith('ADMETLAB::metabolism::CYP')];cyprange={c:int(((pd.to_numeric(fdf[c])<0)|(pd.to_numeric(fdf[c])>1)).sum()) for c in metcols};cyprange={k:v for k,v in cyprange.items() if v}
type_bytes=a.endpoint_types.read_bytes();endpoint_types=json.loads(type_bytes)
probability_columns=[];regression_columns=[];untyped_columns=[]
for raw_column,entry in endpoint_types['entries'].items():
 if raw_column not in rawcols:continue
 cat,name=schema['web_column_to_endpoint'].get(raw_column,['csv_extra',raw_column]);feature='ADMETLAB::'+cat+'::'+name
 if entry['kind']=='classification_probability' and entry.get('probability_bounds_checked'):probability_columns.append(feature)
 elif entry['kind']=='regression':regression_columns.append(feature)
 else:untyped_columns.append(feature)
probability_errors={c:int(((pd.to_numeric(fdf[c])<0)|(pd.to_numeric(fdf[c])>1)).sum()) for c in probability_columns};probability_errors={k:v for k,v in probability_errors.items() if v}
if (a.out/'endpoint-types.json').resolve()!=a.endpoint_types.resolve():(a.out/'endpoint-types.json').write_bytes(type_bytes)
profile_groups=defaultdict(list)
for row in features:profile_groups[tuple(row[c] for c in featurecols)].append(row['request_id'])
profiles=[v for v in profile_groups.values() if len(v)>1]
(a.out/'identical-feature-profile-groups.json').write_text(json.dumps(profiles,indent=2)+'\n')
coverage=Counter(r['source'] for r in request_records)
original_categories=Counter(r['original_to_request_relation'] for r in request_records)
summary={'audited_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'snapshot_manifest_utc':manifest['utc'],'snapshot_rows':len(raw),'feature_rows':len(features),'raw_columns':len(rawcols),'numeric_feature_columns':len(featurecols),'raw_smiles_unique':len({r['raw_smiles'] for r in raw}),'feature_request_ids_unique':len({r['request_id'] for r in features}),'features_and_raw_order_equal':[r['raw_smiles'] for r in raw]==[r['SMILES'] for r in features],'source_id_map_rows':len(mapping),'source_id_map_unique_requests':mapping.request_id.nunique(),'source_map_sha256':sha(map_bytes),'raw_sha256':sha(raw_bytes),'feature_sha256':sha(feat_bytes),'raw_service_text_differences':sum(not r['text_equal'] for r in charlist),'request_to_service_relations':dict(categories),'original_to_request_relations':dict(original_categories),'collected_official_coverage':dict(coverage),'identity_issues':issues,'feature_value_errors':len(feature_errors),'alert_index_errors':len(alert_index_errors),'all_source_original_relations':dict(Counter(r['original_to_request_relation'] for r in all_source_records)),'nonfinite_feature_counts':missing_counts,'cyp_probability_out_of_range':cyprange,'endpoint_types_sha256':sha(type_bytes),'documented_probability_columns_checked':len(probability_columns),'documented_probability_out_of_range':probability_errors,'regression_columns_not_probability_bounded':len(regression_columns),'untyped_or_computed_rule_columns_not_probability_bounded':len(untyped_columns),'chemical_duplicate_group_counts':{k:len(v) for k,v in duplicates.items()},'identical_feature_profile_groups':len(profiles),'mw_check':{'rows':len(mass),'matches_exact_mass_rounded_2dp':sum(abs(x['difference_from_rounded_exact_mass'])<1e-8 for x in mass),'matches_average_MW_rounded_2dp':sum(abs(x['difference_from_rounded_average_MW'])<1e-8 for x in mass),'max_abs_difference_from_rounded_exact_mass':max(abs(x['difference_from_rounded_exact_mass']) for x in mass),'formal_charge_mismatches':sum(x['reported_fChar']!=x['rdkit_formal_charge'] for x in mass)},'runtime':{'python':sys.version,'rdkit':rdBase.rdkitVersion,'pandas':pd.__version__},'interpretation_limit':'These checks establish chemical representation and row integrity, not accuracy of ADMETlab predictions. RDKit standardization comparisons are diagnostic only; source molecules and feature values were not changed.'}
(a.out/'summary.json').write_text(json.dumps(summary,indent=2,default=int)+'\n');print(json.dumps(summary,indent=2,default=int))
