from pathlib import Path
import pandas as pd,json,hashlib
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize
p=Path(__file__).parent;out=p/'stage';out.mkdir(exist_ok=True);b=p.parent;G=Path('/Users/adeliyaleleytner/Documents/ChatGPT/CYP Inhibition/artifacts/goal-20261026');manifest=json.load(open(G/'model-audit/official-snapshot-18460/manifest.json'));cp=Path(manifest['files']['cohorts']['path']);coh=json.load(open(cp));mapping=pd.read_csv(manifest['files']['id_map']['path']);mapping=mapping[mapping.source=='official-train.csv'].set_index('Molecule_Name');fm=json.load(open(G/'submission-preparation/final-inputs/final-manifest.json'));pairs_path=Path(fm['files']['strict_pairs']['path']);pairs=pd.read_csv(pairs_path,dtype=str).fillna('');groups={}
for _,r in pairs.iterrows():
 if r.stereo_preserving_tautomer_key_equal=='True':
  ids=r.request_ids.split(';')
  for x in ids:groups[x]=min(ids)
d=pd.read_csv('/Users/adeliyaleleytner/autoresearch-runs/cyp-admet500-pilot-20261025/stage/official-train.csv');lookup=d.set_index('Molecule_Name');parent={};inchi={}
for r in d.itertuples():
 m=Chem.MolFromSmiles(r.SMILES);inchi[r.Molecule_Name]=Chem.MolToInchiKey(m).split('-')[0];m=rdMolStandardize.FragmentParent(m);m=rdMolStandardize.Uncharger().uncharge(m);Chem.RemoveStereochemistry(m);parent[r.Molecule_Name]=Chem.MolToSmiles(m,canonical=True,isomericSmiles=False)
strict={x:groups.get(v) for x,v in mapping.request_id.items()};result={}
for name in ['own750','briford529']:
 a=coh['cohorts'][name];test=a['test_ids'];train=a['train_ids'];assert not set(train)&set(test);pkeys={parent[x] for x in test};ikeys={inchi[x] for x in test};skeys={strict[x] for x in test if strict.get(x)};remove=[x for x in train if parent[x] in pkeys or inchi[x] in ikeys or (strict.get(x) and strict[x] in skeys)];kept=[x for x in train if x not in set(remove)];result[name]={'test_ids':test,'train_ids':kept,'original_train_rows':len(train),'extra_purged_ids':remove,'original_outer_parent_purged_ids':a['outer_parent_purged_ids'],'no_numeric_query_selection':True};print(name,'train',len(kept),'test',len(test),'extra purge',remove)
(out/'outer-cohorts.json').write_text(json.dumps({'cohorts':result,'sources':{str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [cp,Path(manifest['files']['id_map']['path']),pairs_path]},'policy':'Published frozenoutertraining IDs plus train-side normalizedparent/connectivity and13auditedstrictstereo-tautomer exclusion; no new queryselection','readout_labels':'officialprimaryonly'},indent=2)+'\n')
