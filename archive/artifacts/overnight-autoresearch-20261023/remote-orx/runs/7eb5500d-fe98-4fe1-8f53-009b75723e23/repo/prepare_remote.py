from pathlib import Path
import sys,json,hashlib,urllib.request,importlib.util,time,os,shutil
import numpy as np,pandas as pd,torch,requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor/src'))
from cyp_submission.splits import butina_kfold
from cyp_submission.features import featurize
from cyp_submission.paths import ensure_dirs,CHECKPOINTS_DIR,DATA_EXTERNAL
from cyp_submission.data import HF_DIR
OUT=ROOT/'outputs';OUT.mkdir(exist_ok=True)
CACHE=ROOT/'prepared';CACHE.mkdir(exist_ok=True)
ensure_dirs();CHECKPOINTS_DIR.mkdir(exist_ok=True);DATA_EXTERNAL.mkdir(exist_ok=True);HF_DIR.mkdir(exist_ok=True)
if (ROOT/'reuse_from.json').exists():
    previous=Path(json.loads((ROOT/'reuse_from.json').read_text())['path'])
    for rel in ['vendor/checkpoints','vendor/data/raw','vendor/data/external']:
        if (previous/rel).exists():shutil.copytree(previous/rel,ROOT/rel,dirs_exist_ok=True)
    print('REUSED_PUBLIC_DOWNLOADS',str(previous),flush=True)
assert torch.cuda.is_available()
from modeling import weight_path
weight_path()
print('HARDWARE',torch.__version__,[(i,torch.cuda.get_device_name(i)) for i in range(torch.cuda.device_count())],flush=True)
REV='d3a5549e0c98167435cbf8f5115c68a9a184ed7a'
HFREV='146282d2ce1532f1803679a834a9bec9dac1e482'
def fetch(url,path):
    if path.exists():return
    for attempt in range(4):
        try:
            urllib.request.urlretrieve(url,str(path)+'.part');Path(str(path)+'.part').replace(path);return
        except Exception:
            if attempt==3:raise
            time.sleep(2**attempt)
for name in ['chemprop_medium.pt','chemprop_chemeleon.pt']:
    fetch(f'https://raw.githubusercontent.com/jeremycheminf/openadmet_scripts/{REV}/CYP_Challenge/checkpoints/{name}',CHECKPOINTS_DIR/name)
fetch(f'https://raw.githubusercontent.com/jeremycheminf/openadmet_scripts/{REV}/CYP_Challenge/data/external/cyp_chembl.csv',DATA_EXTERNAL/'cyp_chembl.csv')
for src,name in [('official-train.csv','cyp-challenge-TRAIN_inhibition.csv'),('official-test.csv','cyp-challenge-TEST-BLINDED.csv'),('official-single.csv','cyp-challenge-single-concentration-TRAIN.csv')]:
    shutil.copy2(ROOT/'data'/src,HF_DIR/name)
for name in ['cyp-challenge-TRAIN_inhibition.csv','cyp-challenge-TEST-BLINDED.csv','cyp-challenge-single-concentration-TRAIN.csv']:
    fetch(f'https://huggingface.co/datasets/openadmet/cyp-challenge-train-test/resolve/{HFREV}/{name}',HF_DIR/name)
assert hashlib.sha256((HF_DIR/'cyp-challenge-TRAIN_inhibition.csv').read_bytes()).hexdigest()==hashlib.sha256((ROOT/'data/official-train.csv').read_bytes()).hexdigest()
# Reuse verified data preparation from the failed pre-training compatibility check.
if (ROOT/'prepared_cache.json').exists():
    previous=Path(json.loads((ROOT/'prepared_cache.json').read_text())['path'])
    shutil.copytree(previous,CACHE,dirs_exist_ok=True)
    cached=pd.read_csv(CACHE/'challenge.csv');original=pd.read_csv(ROOT/'data/official-train.csv')
    assert cached.Molecule_Name.tolist()==original.Molecule_Name.tolist()
    targetcols=[c for c in original if c.endswith('_direct_inhibition')]
    assert np.allclose(cached[targetcols],original[targetcols],equal_nan=True)
    print('REUSED_VERIFIED_PREPARATION',str(previous),flush=True)
else:
    # The participant's downloader is retained, with retrying HTTP transport only.
    spec=importlib.util.spec_from_file_location('download_author',ROOT/'vendor/scripts/01_download_data.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    session=requests.Session();retry=Retry(total=5,backoff_factor=1,status_forcelist=[429,500,502,503,504],allowed_methods=['GET','POST']);session.mount('https://',HTTPAdapter(max_retries=retry));mod.requests=session
    if (ROOT/'data/pubchem.csv').exists():shutil.copy2(ROOT/'data/pubchem.csv',DATA_EXTERNAL/'pubchem_cyp_qhts_aid1851.csv')
    mod.download_pubchem_qhts()
    train=pd.read_csv(ROOT/'data/official-train.csv');test=pd.read_csv(ROOT/'data/official-test.csv')
    cols=[f'{c}_pIC50_direct_inhibition' for c in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
    sc=pd.read_csv(HF_DIR/'cyp-challenge-single-concentration-TRAIN.csv').pivot_table(index='Molecule_Name',columns='enzyme',values='log2fc_estimate');sc.columns=[c+'_log2fc' for c in sc.columns]
    challenge=train.merge(sc,on='Molecule_Name',how='left',validate='one_to_one')
    iso=['CYP1A2','CYP2C9','CYP2D6','CYP3A4'];pciso=iso+['CYP2C19']
    logcols=[c+'_log2fc' for c in iso];chcols=[c+'_ChEMBL_PIC50' for c in iso];pccols=[c+'_PubChem_qHTS' for c in pciso]
    allcols=cols+logcols+chcols+pccols
    for c in chcols+pccols:challenge[c]=np.nan
    # Stronger than the author's raw SMILES exclusion, without using any activity.
    uncharger=rdMolStandardize.Uncharger()
    def parent(s):
        m=Chem.MolFromSmiles(s)
        if m is None:return None
        m=rdMolStandardize.FragmentParent(m);m=uncharger.uncharge(m);Chem.RemoveStereochemistry(m)
        return Chem.MolToSmiles(m,isomericSmiles=False)
    challenge_keys=[parent(s) for s in train.SMILES]
    (CACHE/'parent-keys.json').write_text(json.dumps(challenge_keys))
    excluded=set(challenge_keys)|{parent(s) for s in test.SMILES}
    chembl=pd.read_csv(DATA_EXTERNAL/'cyp_chembl.csv');pubchem=pd.read_csv(DATA_EXTERNAL/'pubchem_cyp_qhts_aid1851.csv')
    aux=[];audit={}
    for tag,df,targets,sourcecols in [('chembl',chembl,chcols,[c+'_IC50_PIC50' for c in iso]),('pubchem',pubchem,pccols,[c+'_pIC50' for c in pciso])]:
        keys=df.smiles.map(parent);keep=keys.notna()&~keys.isin(excluded)
        audit[tag]={'input':len(df),'invalid':int(keys.isna().sum()),'official_parent_overlap':int(keys.isin(excluded).sum()),'retained':int(keep.sum())}
        df=df.loc[keep].copy();x=pd.DataFrame({'SMILES':df.smiles,'Molecule_Name':[f'{tag}_{i}' for i in range(len(df))]})
        for c in allcols:x[c]=np.nan
        for c,src in zip(targets,sourcecols):x[c]=pd.to_numeric(df[src],errors='coerce') if src in df else np.nan
        x=x.loc[x[targets].notna().any(axis=1)]
        aux.append(x)
        excluded.update(keys.loc[keep].tolist())
    aux=pd.concat(aux,ignore_index=True);aux.to_csv(CACHE/'aux.csv',index=False);challenge.to_csv(CACHE/'challenge.csv',index=False)
    (CACHE/'aux-audit.json').write_text(json.dumps(audit,indent=2))
    roles={};id_to_idx={v:i for i,v in enumerate(train.Molecule_Name)}
    roles['our_fixed_750']={k:[id_to_idx[x] for x in pd.read_csv(ROOT/f'data/{f}.csv').Molecule_Name] for k,f in [('fit','train'),('val','validation'),('test','holdout')]}
    folds=pd.read_csv(ROOT/'data/jeremy-folds.csv');assert folds.Molecule_Name.tolist()==train.Molecule_Name.tolist();folds=folds.fold.to_numpy()
    assert len(folds)==len(train)
    for f in range(5):roles[f'jeremy_{f}']={'fit':np.flatnonzero(~np.isin(folds,[f,(f+1)%5])).tolist(),'val':np.flatnonzero(folds==(f+1)%5).tolist(),'test':np.flatnonzero(folds==f).tolist()}
    for name,r in roles.items():
        dev=sorted(r['fit']+r['val']);r['dev']=dev
        assert set(dev).isdisjoint(r['test']) and len(dev)+len(r['test'])==len(train)
        assert {challenge_keys[i] for i in dev}.isdisjoint({challenge_keys[i] for i in r['test']})
        assert {challenge_keys[i] for i in r['fit']}.isdisjoint({challenge_keys[i] for i in r['val']})
        r['inner_folds']=butina_kfold(train.iloc[dev].SMILES.tolist(),n_folds=5,cutoff=.6,seed=42).tolist()
        for f in range(5):
            left={challenge_keys[i] for i,ff in zip(dev,r['inner_folds']) if ff==f}
            right={challenge_keys[i] for i,ff in zip(dev,r['inner_folds']) if ff!=f}
            assert left.isdisjoint(right),(name,f,'inner parent overlap')
    (CACHE/'roles.json').write_text(json.dumps(roles))
    (CACHE/'target-columns.json').write_text(json.dumps({'primary':cols,'all':allcols}))
    print('ROLES_READY',{n:{k:len(r[k]) for k in ['fit','val','test']} for n,r in roles.items()},'AUX_AUDIT',audit,flush=True)
    X=featurize(train.SMILES.tolist());X=X.replace([np.inf,-np.inf],np.nan);np.save(CACHE/'classical.npy',X.to_numpy(np.float32));(CACHE/'feature-columns.json').write_text(json.dumps(X.columns.tolist()))
audit_path=CACHE/'aux-audit.json'
audit=json.loads(audit_path.read_text())
if 'official_parent_overlap' in audit['pubchem']:
    audit['pubchem']['overlap_official_or_earlier_chembl']=audit['pubchem'].pop('official_parent_overlap')
audit_path.write_text(json.dumps(audit,indent=2))
print('AUX_AUDIT',json.dumps(audit),flush=True)
train=pd.read_csv(ROOT/'data/official-train.csv')
# Inference-only shared encoder features. Original checkpoints are never fine-tuned here.
from chemprop import data,featurizers
from chemprop.data.collate import collate_batch
from chemprop.models.model import MPNN
for tag,file in [('adme_pretrain','chemprop_medium.pt'),('chemeleon','chemprop_chemeleon.pt')]:
    model=MPNN.load_from_file(str(CHECKPOINTS_DIR/file)).eval().to('cuda:0')
    ds=data.MoleculeDataset([data.MoleculeDatapoint.from_smi(s,[0.]) for s in train.SMILES],featurizers.SimpleMoleculeMolGraphFeaturizer());ds.cache=True
    dl=torch.utils.data.DataLoader(ds,num_workers=0,batch_size=256,shuffle=False,drop_last=False,collate_fn=collate_batch)
    emb=[]
    with torch.inference_mode():
        for b in dl:
            bmg,Vd,Xd,*_=b;bmg.to('cuda:0');Vd=Vd.to('cuda:0') if Vd is not None else None;Xd=Xd.to('cuda:0') if Xd is not None else None
            emb.append(model.fingerprint(bmg,Vd,Xd).cpu().numpy())
    emb=np.concatenate(emb);assert len(emb)==len(train) and np.isfinite(emb).all();np.save(CACHE/f'{tag}.npy',emb)
    del model,ds,dl;torch.cuda.empty_cache();print('EMBEDDED',tag,emb.shape,flush=True)
# Preflight default TabPFN once, before expensive training. Pin actual downloaded version/hash in evidence.
tabmeta=json.loads((ROOT/'tabpfn-transfer.json').read_text())
assert hashlib.sha256(Path(tabmeta['path']).read_bytes()).hexdigest()==tabmeta['sha256']
from tabpfn import TabPFNRegressor
import importlib.metadata
reg=TabPFNRegressor(n_estimators=8,device='cuda',random_state=42)
reg.fit(np.random.default_rng(42).normal(size=(30,5)),np.arange(30,dtype=float))
assert np.isfinite(reg.predict(np.zeros((2,5)))).all()
record={'torch':torch.__version__,'tabpfn':importlib.metadata.version('tabpfn'),'gpu_count':torch.cuda.device_count(),'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list(CHECKPOINTS_DIR.glob('*.pt'))+list(DATA_EXTERNAL.glob('*.csv'))+list(HF_DIR.glob('*.csv'))},'pretraining_membership':'Unknown for participant encoders; external-table exclusion cannot remove prior checkpoint exposure.'}
(OUT/'preparation.json').write_text(json.dumps(record,indent=2)+'\n')
print('PREPARATION_COMPLETE',json.dumps(record),flush=True)
