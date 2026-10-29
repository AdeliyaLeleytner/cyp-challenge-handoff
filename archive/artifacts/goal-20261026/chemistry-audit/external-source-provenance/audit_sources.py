#!/usr/bin/env python3
"""Read-only external original -> cleaned -> actual prepared source-provenance audit."""
from pathlib import Path
from functools import lru_cache
from collections import Counter,defaultdict
import hashlib,json,datetime
import pandas as pd
from rdkit import Chem,RDLogger,rdBase
from rdkit.Chem.MolStandardize import rdMolStandardize
RDLogger.DisableLog('rdApp.*')
OUT=Path(__file__).resolve().parent
BASE=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/fullfit-strae-prep/stage/original_full')
TRANSITION=set(range(21,31))|set(range(39,49))|set(range(57,81))|set(range(89,113))
OTHER_METALS={3,4,11,12,13,19,20,31,37,38,49,50,55,56,81,82,83,87,88}
uncharger=rdMolStandardize.Uncharger()
@lru_cache(None)
def mol(s):return Chem.MolFromSmiles(s)
def can(m):return Chem.MolToSmiles(m,isomericSmiles=True)
@lru_cache(None)
def canonical(s):return can(mol(s)) if mol(s) else None
@lru_cache(None)
def key(s):return Chem.MolToInchiKey(mol(s)).split('-')[0] if mol(s) else None
def elements(m):return Counter(a.GetAtomicNum() for a in m.GetAtoms())
def symbols(c):return {Chem.GetPeriodicTable().GetElementSymbol(k):v for k,v in sorted(c.items())}
@lru_cache(None)
def info(orig,clean):
 a,b=mol(orig),mol(clean)
 if a is None or b is None:return {'relation':'parse_failure','original_parse':a is not None,'cleaned_parse':b is not None}
 ea,eb=elements(a),elements(b);lost=ea-eb;gain=eb-ea
 frags=Chem.GetMolFrags(a,asMols=True,sanitizeFrags=True)
 fc=[can(x) for x in frags];uc=[can(uncharger.uncharge(Chem.Mol(x))) for x in frags]
 bc=can(b)
 if can(a)==bc:relation='same_isomeric_graph'
 elif bc in fc:relation='selected_original_fragment'
 elif bc in uc:relation='selected_original_fragment_after_uncharging'
 elif can(uncharger.uncharge(Chem.Mol(a)))==bc:relation='whole_entity_uncharged'
 else:relation='other_transformation'
 return {'relation':relation,'original_parse':True,'cleaned_parse':True,'original_fragments':len(frags),'cleaned_fragments':len(Chem.GetMolFrags(b)),'original_heavy_atoms':a.GetNumHeavyAtoms(),'cleaned_heavy_atoms':b.GetNumHeavyAtoms(),'original_carbon':ea[6],'cleaned_carbon':eb[6],'original_elements':symbols(ea),'lost_elements':symbols(lost),'gained_elements':symbols(gain),'lost_transition_elements':symbols({k:v for k,v in lost.items() if k in TRANSITION}),'lost_other_metal_elements':symbols({k:v for k,v in lost.items() if k in OTHER_METALS}),'original_metal_bonds':sum(x.GetBeginAtom().GetAtomicNum() in TRANSITION|OTHER_METALS or x.GetEndAtom().GetAtomicNum() in TRANSITION|OTHER_METALS for x in a.GetBonds()),'original_fragment_smiles':fc,'original_fragment_uncharged':uc,'original_canonical':can(a),'cleaned_canonical':bc}
pub=pd.read_csv(BASE/'raw/pubchem_all_isoforms.csv');ch=pd.read_csv(BASE/'raw/chembl_all_isoforms.csv');prepared=pd.read_csv(BASE/'prepared/union18.csv')
ch['join_key']=ch.inchi_key.str.split('-').str[0]
ch['selected_chembl_key']=~ch.join_key.duplicated()
# Producer's pivot_table sorts cleaned strings then keeps first connectivity key.
pubclean=pd.DataFrame({'smiles':sorted(pub.smiles.unique())});pubclean['join_key']=pubclean.smiles.map(key)
selected_pub=set(pubclean.drop_duplicates('join_key').smiles)
prepared['join_key']=prepared.smiles.map(key)
bykey={k:g.to_dict('records') for k,g in prepared.groupby('join_key')}
records=[]
for source,d,idcols in [('pubchem',pub,['sid','cid','smiles','orig_smiles']),('chembl',ch,['chembl_id','smiles','orig_smiles','join_key','selected_chembl_key'])]:
 unique=d.drop_duplicates(idcols)
 for row in unique.to_dict('records'):
  orig=row['orig_smiles'];clean=row['smiles'];k=key(clean) if source=='pubchem' else row['join_key']
  selected=clean in selected_pub if source=='pubchem' else bool(row['selected_chembl_key'])
  dest=bykey.get(k,[]) if selected else []
  r={'source':source,'source_id':str(row['sid']) if source=='pubchem' else row['chembl_id'],'cid':int(row['cid']) if source=='pubchem' else None,'pref_name':row.get('pref_name'),'original_smiles':orig,'cleaned_smiles':clean,'join_key':k,'selected_by_producer_key':selected,'prepared_ids':[x['molecule_name'] for x in dest],'prepared_smiles':[x['smiles'] for x in dest],'prepared_request_ids':[hashlib.sha256(x['smiles'].encode()).hexdigest() for x in dest],**info(orig,clean)}
  records.append(r)
def csvwrite(name,recs):
 def scalar(x):return json.dumps(x,sort_keys=True) if isinstance(x,(list,dict)) else x
 pd.DataFrame([{k:scalar(v) for k,v in r.items()} for r in recs]).to_csv(OUT/name,index=False)
csvwrite('all-source-transformations.csv',records)
lost=[r for r in records if r.get('lost_transition_elements') or r.get('lost_other_metal_elements')]
csvwrite('metal-loss-source-records.csv',lost)
csvwrite('carbon-free-source-records.csv',[r for r in records if r.get('cleaned_carbon')==0])
active=[r for r in records if r['prepared_ids']]
groups=defaultdict(list)
for r in active:
 for did in r['prepared_ids']:groups[did].append(r)
collapse=[]
for did,g in groups.items():
 originals={r.get('original_canonical') for r in g}
 if len(originals)>1:
  collapse.append({'prepared_id':did,'prepared_smiles':g[0]['prepared_smiles'][g[0]['prepared_ids'].index(did)],'distinct_original_graphs':len(originals),'source_records':len(g),'sources':sorted({r['source'] for r in g}),'original_graphs':sorted(x for x in originals if x is not None),'source_ids':[r['source']+':'+r['source_id'] for r in g],'any_transition_loss':any(bool(r.get('lost_transition_elements')) for r in g),'any_other_metal_loss':any(bool(r.get('lost_other_metal_elements')) for r in g),'cleaned_graphs':sorted({r.get('cleaned_canonical') for r in g if r.get('cleaned_canonical')})})
csvwrite('collapsed-original-entities.csv',collapse)
summary={'audited_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'raw_rows':{'pubchem':len(pub),'chembl':len(ch)},'source_records':len(records),'source_records_by_source':dict(Counter(r['source'] for r in records)),'relations':dict(Counter(r['relation'] for r in records)),'producer_selected_records_with_prepared_destination':len(active),'active_relations':dict(Counter(r['relation'] for r in active)),'metal_loss_source_records':len(lost),'transition_loss_records':sum(bool(r.get('lost_transition_elements')) for r in records),'transition_loss_active_records':sum(bool(r.get('lost_transition_elements')) for r in active),'transition_loss_prepared_ids':sorted({i for r in active if r.get('lost_transition_elements') for i in r['prepared_ids']}),'carbon_free_active_records':sum(r.get('cleaned_carbon')==0 for r in active),'collapse_groups_multiple_original_graphs':len(collapse),'rdkit':rdBase.rdkitVersion}
(OUT/'summary-initial.json').write_text(json.dumps(summary,indent=2)+'\n')
(OUT/'input-sha256.json').write_text(json.dumps({str(BASE/f):hashlib.sha256((BASE/f).read_bytes()).hexdigest() for f in ['raw/pubchem_all_isoforms.csv','raw/chembl_all_isoforms.csv','prepared/union18.csv']},indent=2)+'\n')
print(json.dumps(summary,indent=2))
