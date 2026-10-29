#!/usr/bin/env python3
"""Diagnostic topology inventory only; it does not establish tautomer/stereo equivalence."""
from pathlib import Path
from functools import lru_cache
from collections import Counter,defaultdict
import json
import pandas as pd
from rdkit import Chem,RDLogger
RDLogger.DisableLog('rdApp.*')
OUT=Path(__file__).resolve().parent
d=pd.read_csv(OUT/'classified-source-transformations.csv',keep_default_na=False,low_memory=False)
@lru_cache(None)
def topology(s):
 m=Chem.MolFromSmiles(s);Chem.RemoveStereochemistry(m)
 for a in m.GetAtoms():a.SetIsAromatic(False);a.SetFormalCharge(0);a.SetNumExplicitHs(0);a.SetNoImplicit(True)
 for b in m.GetBonds():b.SetIsAromatic(False);b.SetBondType(Chem.BondType.SINGLE)
 return Chem.MolToSmiles(m,canonical=True,isomericSmiles=True)
refined=[]
for r in d.to_dict('records'):
 typ=r['transformation_class'];frags=json.loads(r['original_fragment_smiles'])
 if typ=='other_graph_change_unadjudicated':
  t=topology(r['cleaned_smiles']);match=[f for f in frags if topology(f)==t]
  if match:typ='same_atom_connectivity_bond_order_charge_or_stereo_rearrangement_candidate' if len(frags)==1 else 'fragment_retained_with_bond_order_charge_or_stereo_rearrangement_candidate'
 r['refined_class']=typ;refined.append(r)
pd.DataFrame(refined).to_csv(OUT/'refined-source-transformations.csv',index=False)
active=[r for r in refined if json.loads(r['prepared_ids'])]
groups=defaultdict(list)
for r in active:
 if r['source']=='pubchem':groups[r['cleaned_smiles']].append(r)
pcollapse=[]
for clean,g in groups.items():
 originals={r['original_canonical'] for r in g}
 if len(originals)>1:pcollapse.append({'cleaned_smiles':clean,'prepared_ids':g[0]['prepared_ids'],'distinct_original_graphs':len(originals),'distinct_cids':len({r['cid'] for r in g}),'source_records':len(g),'source_ids':';'.join(str(r['source_id']) for r in g),'originals':json.dumps(sorted(originals))})
pd.DataFrame(pcollapse).to_csv(OUT/'pubchem-pivot-original-collapses.csv',index=False)
other=[r for r in refined if r['refined_class']=='other_graph_change_unadjudicated']
pd.DataFrame(other).to_csv(OUT/'remaining-other-graph-changes.csv',index=False)
out={'all_classes':dict(Counter(r['refined_class'] for r in refined)),'active_classes':dict(Counter(r['refined_class'] for r in active)),'pubchem_pivot_multiple_original_graphs_groups':len(pcollapse),'pubchem_pivot_multiple_cids_groups':sum(r['distinct_cids']>1 for r in pcollapse),'single_fragment_heavy_atom_loss_without_metal_loss':sum(r['original_fragments']==1 and r['lost_elements']!='{}' and r['lost_transition_elements']=='{}' and r['lost_other_metal_elements']=='{}' for r in refined),'caution':'Topology diagnostic erases bond orders, aromaticity, formal charge and stereo but retains elements/isotopes/adjacency. Matching does NOT establish tautomer equivalence or justify merging isomers. No enumeration keys or transformed graphs enter fitting.'}
(OUT/'refined-summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
