"""Official-only folds: same scaffold assignment and parent purge as evaluated cohorts."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from .public_data import normalize_parent_key
from .admet_full_contract_v1 import require,digest

def strict_groups(path):
    rows=pd.read_csv(path,dtype=str).fillna('');groups={}
    for _,r in rows.iterrows():
        if r['stereo_preserving_tautomer_key_equal']!='True':continue
        require(r['official_normalization_status']==r['external_normalization_status']=='Completed','Uncertified strict group')
        ids=r['request_ids'].split(';');key=min(ids)
        for rid in ids:
            require(rid not in groups or groups[rid]==key,'Conflicting strict groups');groups[rid]=key
    require(len(set(groups.values()))==13,'Expected the13 audited strict groups; a changed audit needs reviewed code/config')
    return groups

def make_folds(data,request_ids,strict,seed=42):
    names=data.Molecule_Name.tolist();require(len(names)==len(set(names)),'Duplicate official ID')
    parents=[normalize_parent_key(s) for s in data.SMILES];require(all(p is not None for p in parents),'Invalid official parent')
    scaff=[];mapping={}
    for s in data.SMILES:
        m=Chem.MolFromSmiles(s);require(m is not None,'Invalid official SMILES')
        key=Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(m))
        if key not in mapping:mapping[key]=len(mapping)
        scaff.append(mapping[key])
    scaff=np.array(scaff);unique,counts=np.unique(scaff,return_counts=True);loads=np.zeros(5,dtype=int);assignment={}
    for ix in np.random.default_rng(seed).permutation(len(unique)):
        f=int(np.argmin(loads));assignment[int(unique[ix])]=f;loads[f]+=int(counts[ix])
    labels=np.array([assignment[int(g)] for g in scaff]);strict_keys=[strict.get(r) for r in request_ids];folds=[]
    for f in range(5):
        val=np.flatnonzero(labels==f);vp={parents[i] for i in val};vs={strict_keys[i] for i in val if strict_keys[i] is not None}
        train=[i for i in range(len(names)) if labels[i]!=f and parents[i] not in vp and (strict_keys[i] is None or strict_keys[i] not in vs)]
        folds.append({'train_ids':[names[i] for i in train],'val_ids':[names[i] for i in val],'removed_train_ids':[names[i] for i in range(len(names)) if labels[i]!=f and i not in train]})
    return {'schema_version':1,'seed':seed,'policy':'Evaluated scaffold-greedy assignment plus normalized-parent and audited strict train-side purge','native_fold_note':'Native component fold maps differ; feature OOF joins by molecule identity, not native fold number','folds':folds}

def validate_folds(manifest,data,request_ids,strict):
    names=data.Molecule_Name.tolist();lookup={n:i for i,n in enumerate(names)};parents=[normalize_parent_key(s) for s in data.SMILES]
    require(len(manifest['folds'])==5,'Exactly five feature folds required');seen=[];result=[]
    for f in manifest['folds']:
        a,b=f['train_ids'],f['val_ids'];require(len(a)==len(set(a)) and len(b)==len(set(b)),'Duplicate fold IDs')
        require(set(a)<=set(names) and set(b)<=set(names) and not set(a)&set(b),'Fold ID leakage')
        tr=np.array([lookup[n] for n in a],int);va=np.array([lookup[n] for n in b],int)
        require(len(tr)>1 and len(va)>0,'Empty training/validation fold')
        require(not {parents[i] for i in tr}&{parents[i] for i in va},'Parent overlap')
        ag={strict[request_ids[i]] for i in tr if request_ids[i] in strict};bg={strict[request_ids[i]] for i in va if request_ids[i] in strict}
        require(not ag&bg,'Strict tautomer overlap')
        seen.extend(b);result.append((tr,va))
    require(sorted(seen)==sorted(names),'OOF must cover every official row exactly once')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--official',required=True);p.add_argument('--id-map',required=True);p.add_argument('--strict-pairs',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    data=pd.read_csv(a.official);mapping=pd.read_csv(a.id_map,dtype=str);chosen=mapping[mapping.source=='official-train.csv'].set_index('Molecule_Name')
    require(chosen.index.is_unique,'Duplicate official mapping');ids=chosen.loc[data.Molecule_Name].request_id.tolist()
    strict=strict_groups(a.strict_pairs);manifest=make_folds(data,ids,strict)
    manifest['input_sha256']={k:digest(v) for k,v in [('official_train',a.official),('id_map',a.id_map),('strict_pairs',a.strict_pairs)]}
    validate_folds(manifest,data,ids,strict);out=Path(a.output);require(not out.exists(),'Do not overwrite frozen folds');out.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'fold_manifest':str(out),'sha256':digest(out),'rows':len(data),'fits_started':0}))
if __name__=='__main__':main()
