"""Read-only structural audit. No training, label changes, or source rewriting.

Compare source-cleaned graphs with the actual P10 model graph; first-block
InChIKey agreement alone is never used here to declare chemical equivalence.
Tautomer enumeration is diagnostic, stereo-preserving and completion-gated.
"""
from pathlib import Path
from functools import lru_cache
from collections import Counter, defaultdict
import csv, json, hashlib, time
from rdkit import Chem, RDLogger, rdBase
from rdkit.Chem.MolStandardize import rdMolStandardize as rms

RDLogger.DisableLog('rdApp.*')
OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
SRC=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026/chemistry-audit/external-source-provenance')
TABLE=ROOT/'p10/stage/common/table.csv'
def read(p):
    with p.open() as h: return list(csv.DictReader(h))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(m): return Chem.MolToSmiles(m,isomericSmiles=True)
def no_stereo(m):
    m=Chem.Mol(m); Chem.RemoveStereochemistry(m); return canon(m)
normalizer=rms.Normalizer(); uncharger=rms.Uncharger()
te=rms.TautomerEnumerator();te.SetRemoveSp3Stereo(False);te.SetRemoveBondStereo(False)
te.SetMaxTautomers(1000);te.SetMaxTransforms(1000)
@lru_cache(None)
def info(s):
    m=Chem.MolFromSmiles(s)
    assert m is not None
    norm=normalizer.normalize(Chem.Mol(m)); neutral=uncharger.uncharge(Chem.Mol(norm))
    return dict(canonical=canon(m),stereo_free=no_stereo(m),normalized=canon(norm),neutral=canon(neutral),
                fragments=len(Chem.GetMolFrags(m)),net_charge=Chem.GetFormalCharge(m),
                specified_centers=len(Chem.FindMolChiralCenters(m,includeUnassigned=False)),
                isotopes=sum(a.GetIsotope()!=0 for a in m.GetAtoms()))
@lru_cache(None)
def taut(s):
    m=Chem.MolFromSmiles(info(s)['neutral']); result=te.Enumerate(m)
    status=str(result.status)
    return (canon(te.PickCanonical(result)) if status=='Completed' else None),status
@lru_cache(None)
def classify(a,b):
    x,y=info(a),info(b)
    if x['canonical']==y['canonical']: return 'exact_isomeric_graph','not_needed','not_needed'
    if x['stereo_free']==y['stereo_free']: return 'stereo_only_difference','not_needed','not_needed'
    if x['normalized']==y['normalized']:return 'functional_normalization_match','not_needed','not_needed'
    if x['neutral']==y['neutral']:return 'normalization_and_uncharging_match','not_needed','not_needed'
    aa,sa=taut(a);bb,sb=taut(b)
    if aa is not None and bb is not None and aa==bb:return 'completed_stereo_preserving_tautomer_key_match',sa,sb
    return ('enumeration_incomplete' if aa is None or bb is None else 'unresolved_other_difference'),sa,sb

start=time.time();table=read(TABLE);byid={r['molecule_name']:r for r in table}
assert len(byid)==len(table)
structure_counts=Counter();keys=defaultdict(list)
for r in table:
    x=info(r['smiles']);keys[x['canonical']].append(r['molecule_name'])
    structure_counts['multicomponent']+=x['fragments']>1
    structure_counts['nonzero_net_charge']+=x['net_charge']!=0
    structure_counts['normalizer_changes_graph']+=x['canonical']!=x['normalized']
    structure_counts['normalize_then_uncharge_changes_graph']+=x['canonical']!=x['neutral']
    structure_counts['isotope_labeled']+=x['isotopes']>0
    structure_counts['specified_atom_stereo']+=x['specified_centers']>0
print(json.dumps({'phase':'all_current_structures_checked','rows':len(table)}),flush=True)

old=read(SRC/'classified-collapses.csv')
old620={r['prepared_id'] for r in old if r['class']=='different_cleaned_graphs_same_connectivity_key_review'}
if len(old620)!=620:
    print('classes',Counter(r['class'] for r in old),flush=True)
    # Exact class spelling is read from the saved audit, never inferred from names.
    possible={r['class'] for r in old if int(r['distinct_cleaned_graphs'])>1}
    chosen=[k for k in possible if sum(r['class']==k for r in old)==620]
    assert len(chosen)==1,possible
    old620={r['prepared_id'] for r in old if r['class']==chosen[0]}
edges=[];source_rows=read(SRC/'all-source-transformations.csv')
for r in source_rows:
    for dest in json.loads(r['prepared_ids']):
        if dest not in byid:continue
        model=byid[dest]['smiles'];kind,sa,sb=classify(r['cleaned_smiles'],model)
        edges.append(dict(prepared_id=dest,source=r['source'],source_id=r['source_id'],
            original_smiles=r['original_smiles'],source_cleaned_smiles=r['cleaned_smiles'],model_smiles=model,
            relation=kind,source_enum_status=sa,model_enum_status=sb,within_old620=dest in old620,
            official_id=dest.startswith('OCNT-')))
with (OUT/'source-to-model-edges.csv').open('w') as h:
    w=csv.DictWriter(h,fieldnames=list(edges[0]));w.writeheader();w.writerows(edges)
counts=Counter(r['relation'] for r in edges)
affected={k:sorted({r['prepared_id'] for r in edges if r['relation']==k}) for k in counts}
summary={'status':'complete_read_only','rdkit':rdBase.rdkitVersion,'seconds':time.time()-start,
    'current_rows':len(table),'unique_exact_isomeric_graphs':len(keys),'exact_duplicate_groups':sum(len(v)>1 for v in keys.values()),
    'current_structure_flags':dict(structure_counts),'historical620_groups':len(old620),
    'historical620_retained':len(old620&byid.keys()),'historical620_absent':sorted(old620-byid.keys()),
    'source_to_model_edges':len(edges),'source_to_model_relation_counts':dict(counts),
    'affected_destination_counts':{k:len(v) for k,v in affected.items()},
    'affected_official_destination_counts':{k:sum(x.startswith('OCNT-') for x in v) for k,v in affected.items()},
    'affected_ids_by_relation':affected,
    'tautomer_policy':'diagnostic only; Normalize then Uncharger then enumeration; removeSp3Stereo=False; removeBondStereo=False; maxTautomers=maxTransforms=1000; incomplete results never equated',
    'limitations':['Inherited source aggregate provenance; edge count is not independent assay count.',
                  'Stereo-only difference includes specified versus unspecified stereo, not only opposite enantiomers.',
                  'Matching diagnostic keys does not establish assay interchangeability or physiological protonation.',
                  'No general tautomer canonicalization applied to current model inputs.',
                  'Not a full source SDF/experimental specimen audit.'],
    'hashes':{str(p):sha(p) for p in [TABLE,SRC/'all-source-transformations.csv',SRC/'classified-collapses.csv',Path(__file__)]}}
(OUT/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['affected_ids_by_relation','hashes']},indent=2),flush=True)
