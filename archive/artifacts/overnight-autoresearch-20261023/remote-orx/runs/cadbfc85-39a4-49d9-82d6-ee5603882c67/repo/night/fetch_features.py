"""Fetch public revision-pinned assets, then extract structure-only features in ORX."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time,tarfile,io
import requests
import pandas as pd

ROOT=Path('/workspace/cyp-night/assets')
OUT=Path('/workspace/cyp-night/results/F0_features')
MONROE='de075eabe98e4adbbedbc86ca9e877f4bfd9b629'
MOLFORMER='361063d0ad524ef77cf39b08469f6be770dc550f'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for c in iter(lambda:f.read(8*1024*1024),b''):h.update(c)
    return h.hexdigest()

def fetch(url,path,expected=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and (expected is None or sha(path)==expected):return sha(path)
    for attempt in range(3):
        try:
            with requests.get(url,stream=True,timeout=(30,180)) as r:
                r.raise_for_status()
                temp=Path(str(path)+'.partial')
                with temp.open('wb') as f:
                    for c in r.iter_content(1024*1024):f.write(c)
            digest=sha(temp)
            if expected and digest!=expected:raise ValueError(f'Hash mismatch: {path.name}')
            os.replace(temp,path)
            print(json.dumps({'event':'asset_downloaded','file':str(path),'bytes':path.stat().st_size,'sha256':digest}),flush=True)
            return digest
        except Exception:
            if attempt==2:raise
            time.sleep(2**attempt)

def bundle(directory,suffixes):
    return {str(p.relative_to(directory)):sha(p) for p in directory.rglob('*') if p.is_file() and p.suffix in suffixes and '.git' not in p.parts}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    frames=[pd.read_csv(ROOT/f,usecols=['Molecule_Name','SMILES']) for f in ['official-train.csv','official-test.csv']]
    bank=pd.concat(frames,ignore_index=True)
    assert len(bank)==5655 and not bank.Molecule_Name.duplicated().any()
    bank.to_csv(ROOT/'all_molecules.csv',index=False)
    manifest={'encoders':{'chemeleon_foundation':{'model_asset':{'path':'weights/chemeleon_mp.pt','sha256':'c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651'}}}}
    (ROOT/'encoder_manifest.json').write_text(json.dumps(manifest,indent=2))
    # First produce the cheap known-provenance bank even if an optional provider fails later.
    extract('chemeleon_foundation')
    tfm='tabicl-regressor-v2-20260212.ckpt'
    fetch('https://huggingface.co/jingang/TabICL/resolve/4dcd344ece2c00be9e831fdd35bed57b5ad83e19/'+tfm,ROOT/'weights'/tfm,
          '0db9cb538f114e79026bf08f45f41ad8dd7ad2de2aaca9a5ca8cd3bd9748ae7a')
    errors=[]
    try:
        repo='ibm-research/MoLFormer-XL-both-10pct'
        response=requests.get(f'https://huggingface.co/api/models/{repo}/revision/{MOLFORMER}',timeout=60);response.raise_for_status()
        files=[x['rfilename'] for x in response.json()['siblings']]
        directory=ROOT/'weights/molformer'
        for name in files:
            if '/' in name:continue
            if Path(name).suffix not in {'.json','.py','.txt','.model','.safetensors'}:continue
            expected='0795977fe7192c4acdaf052f0e8464af57bc4bb59211271c5e61aaba2637b9c6' if name=='model.safetensors' else None
            fetch(f'https://huggingface.co/{repo}/resolve/{MOLFORMER}/{name}',directory/name,expected)
        manifest['encoders']['molformer']={'model_dir':str(directory.relative_to(ROOT)),'revision':MOLFORMER,'files_sha256':bundle(directory,{'.json','.py','.txt','.model','.safetensors','.bin'})}
        (ROOT/'encoder_manifest.json').write_text(json.dumps(manifest,indent=2))
        extract('molformer')
    except Exception as e:
        errors.append({'encoder':'molformer','error':repr(e)});print(errors[-1],flush=True)
    try:
        archive=ROOT/f'sources/Monroe-{MONROE}.tar.gz'
        fetch(f'https://codeload.github.com/blazejba/Monroe/tar.gz/{MONROE}',archive)
        source=ROOT/'sources/Monroe';source.mkdir(parents=True,exist_ok=True)
        with tarfile.open(archive) as tar:
            for m in tar.getmembers():
                if not m.isfile():continue
                parts=Path(m.name).parts[1:]
                if not parts or '..' in parts:raise ValueError('Unsafe source archive path')
                dest=source.joinpath(*parts)
                if dest.suffix not in {'.py','.json','.csv','.toml','.md'}:continue
                dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(m).read())
        weight=ROOT/'weights/monroe/weights.pt';cfg=ROOT/'weights/monroe/config.json'
        wh=fetch(f'https://media.githubusercontent.com/media/blazejba/Monroe/{MONROE}/checkpoint/weights.pt',weight,'df996e8e98b12a3cda5fe5acbef3e1e9a4ea31946d3736461cd07e53a5bf205a')
        ch=fetch(f'https://raw.githubusercontent.com/blazejba/Monroe/{MONROE}/checkpoint/config.json',cfg)
        manifest['encoders']['monroe']={'source_dir':str(source.relative_to(ROOT)),'revision':MONROE,'files_sha256':bundle(source,{'.py','.json','.csv'}),'model_asset':{'path':str(weight.relative_to(ROOT)),'sha256':wh},'config_asset':{'path':str(cfg.relative_to(ROOT)),'sha256':ch}}
        (ROOT/'encoder_manifest.json').write_text(json.dumps(manifest,indent=2));extract('monroe')
    except Exception as e:
        errors.append({'encoder':'monroe','error':repr(e)});print(errors[-1],flush=True)
    (OUT/'status.json').write_text(json.dumps({'optional_errors':errors,'feature_manifest':json.loads((ROOT/'feature_manifest.json').read_text())},indent=2))
    if errors:raise RuntimeError('Optional encoder failure; successful immutable banks retained')

def extract(name):
    existing=ROOT/'feature_manifest.json'
    if existing.exists() and name in json.loads(existing.read_text()).get('features',{}):
        print(json.dumps({'event':'reuse_pinned_feature','name':name}),flush=True);return
    config=OUT/f'{name}-config.json';config.write_text(json.dumps({'seed':42,'batch_size':32,'num_workers':8,'device':'cuda','failure_policy':'raise'}))
    subprocess.run([sys.executable,'-u','-m','night.encoders','--molecules',str(ROOT/'all_molecules.csv'),'--encoder',name,'--asset-root',str(ROOT),'--asset-key',name,'--expected-rows','5655','--config',str(config),'--audit-path',str(OUT/f'{name}-audit.json')],check=True)

if __name__=='__main__':main()
