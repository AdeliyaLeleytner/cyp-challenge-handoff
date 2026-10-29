"""Public PCBA provenance audit, to run only in the root's authorized ORX job.

No model fitting. Downloads one pinned ZIP, scans identities/labels, queries public
assay descriptions, and exports matched rows only. Historical checkpoint training
membership is NOT inferred from a raw-data match or from passing raw count filters.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import time
import urllib.request
import zipfile

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger, rdBase

from .public_data import normalize_parent_key, CachedHTTP, TOX21_CYP_ASSAYS

ZIP_URL = 'https://zenodo.org/api/records/8024997/files/pcba_1328.zip/content'
ZIP_MD5 = '7ae4c2f871fe86b07f4ec161023caa62'
ZIP_BYTES = 152820002
MEMBER = 'PCBA_1328_1564k.parquet'
MEMBER_BYTES = 150055049
MONROE_REVISION = 'de075eabe98e4adbbedbc86ca9e877f4bfd9b629'
SOURCE_HASHES = {
    'monroe/preprocessing/pcba_prep.py': '16536ae6b33404618b02f538dbc4ea8b98b629f26755c1bbfea0ddf825e1a026',
    'monroe/preprocessing/pm6_prep.py': '4acb6b644ff3e37a311983b639504ec9e245451a73ed7af85302e283ab2245b6',
    'monroe/assets/polaris_benchmarks.json': '0ce4f733fd85dddf8b3eb560d715c06a746f0b4580a5994ad4110fcd2dcbb770'}
CYP_TEXT = re.compile(r'\bCYP[\w-]*\b|cytochrome|\bP\s*-?\s*450\b', re.I)
_OFFICIAL_INCHI = {}
_OFFICIAL_PARENT = {}


def _hash(path, kind='sha256'):
    digest = hashlib.new(kind)
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')
    os.replace(temp, path)


def _log(event, **kwargs):
    print(json.dumps({'event': event, **kwargs}), flush=True)


def stage_parquet(cache, expected_sha256=None):
    cache = Path(cache); cache.mkdir(parents=True, exist_ok=True)
    archive = cache/'pcba_1328.zip'
    if not archive.exists():
        temp = archive.with_suffix('.download')
        try:
            request = urllib.request.Request(ZIP_URL, headers={'User-Agent':'CYP-PCBA-provenance-audit/1.0','Accept-Encoding':'identity'})
            with urllib.request.urlopen(request, timeout=120) as response, temp.open('wb') as output:
                total = 0
                while True:
                    chunk = response.read(4*1024*1024)
                    if not chunk: break
                    total += len(chunk)
                    if total > ZIP_BYTES: raise ValueError('ZIP exceeds pinned byte count')
                    output.write(chunk)
            actual_bytes=temp.stat().st_size; actual_md5=_hash(temp,'md5')
            _log('zip_download_integrity',actual_bytes=actual_bytes,expected_bytes=ZIP_BYTES,actual_md5=actual_md5,expected_md5=ZIP_MD5)
            if actual_bytes != ZIP_BYTES or actual_md5 != ZIP_MD5:
                raise ValueError('Downloaded ZIP differs from pinned Zenodo size/MD5')
            os.replace(temp, archive)
        finally:
            temp.unlink(missing_ok=True)
    if archive.stat().st_size != ZIP_BYTES or _hash(archive, 'md5') != ZIP_MD5:
        raise ValueError('Cached ZIP differs from pinned Zenodo size/MD5')
    sha = _hash(archive)
    if expected_sha256 is not None and sha != expected_sha256.lower():
        raise ValueError('ZIP SHA-256 differs from supplied pin')
    parquet = cache/MEMBER
    # Read only the named parquet member to a fixed path; never extractall or load .pt.
    with zipfile.ZipFile(archive) as z:
        entries = [x for x in z.infolist() if x.filename == MEMBER]
        if len(entries) != 1 or entries[0].file_size != MEMBER_BYTES:
            raise ValueError('Unexpected parquet ZIP member metadata')
        temp = parquet.with_suffix('.extract')
        try:
            with z.open(entries[0]) as source, temp.open('wb') as output:
                shutil.copyfileobj(source, output, 4*1024*1024)
            if temp.stat().st_size != MEMBER_BYTES: raise ValueError('Parquet size mismatch')
            os.replace(temp, parquet)
        finally:
            temp.unlink(missing_ok=True)
    return parquet, {'url':ZIP_URL, 'zip_size':ZIP_BYTES, 'zip_md5':ZIP_MD5,
                     'zip_sha256':sha, 'zip_sha256_supplied':expected_sha256 is not None,
                     'parquet_sha256':_hash(parquet), 'parquet_size':parquet.stat().st_size}


def _identities(smi):
    try:
        mol = Chem.MolFromSmiles(smi) if isinstance(smi, str) else None
        inchi = Chem.MolToInchi(mol) if mol is not None else None
        inchi = inchi or None
    except Exception:
        inchi = None
    parent = normalize_parent_key(smi) if isinstance(smi, str) else None
    return inchi, parent


def _init_workers(inchis, parents):
    global _OFFICIAL_INCHI, _OFFICIAL_PARENT
    _OFFICIAL_INCHI, _OFFICIAL_PARENT = inchis, parents
    RDLogger.DisableLog('rdApp.*')


def _match_chunk(payload):
    offset, smiles = payload
    matches = []; invalid_inchi = invalid_parent = 0; invalid_examples = []
    for i, smi in enumerate(smiles):
        inchi, parent = _identities(smi)
        invalid_inchi += inchi is None; invalid_parent += parent is None
        if (inchi is None or parent is None) and len(invalid_examples)<3:
            invalid_examples.append({'row_index':offset+i, 'SMILES':smi, 'inchi_failed':inchi is None, 'parent_failed':parent is None})
        exact = _OFFICIAL_INCHI.get(inchi, []) if inchi is not None else []
        normalized = _OFFICIAL_PARENT.get(parent, []) if parent is not None else []
        if exact or normalized:
            matches.append({'row_index':offset+i, 'pcba_SMILES':smi, 'pcba_inchi':inchi,
                'pcba_parent_key':parent, 'exact_official_ids':exact, 'parent_official_ids':normalized})
    return matches, invalid_inchi, invalid_parent, invalid_examples


def match_identities(parquet, official, workers=8, chunk_size=4096):
    import pyarrow.parquet as pq
    inchis = defaultdict(list); parents = defaultdict(list)
    for row in official.to_dict('records'):
        inchi, parent = _identities(row['SMILES'])
        if inchi is None or parent is None:
            raise ValueError(f'Cannot normalize official structure {row["Molecule_Name"]}')
        inchis[inchi].append(row['Molecule_Name']); parents[parent].append(row['Molecule_Name'])
    pf = pq.ParquetFile(parquet)
    def batches():
        offset = 0
        for batch in pf.iter_batches(batch_size=chunk_size, columns=['SMILES']):
            values = batch.column(0).to_pylist()
            yield offset, values
            offset += len(values)
    matched=[]; failures={'inchi_failed':0,'parent_failed':0,'examples':[]}; processed=0
    if workers < 1: raise ValueError('workers must be positive')
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_workers,
                             initargs=(dict(inchis),dict(parents))) as pool:
        for found, ni, np_, examples in pool.map(_match_chunk, batches()):
            matched.extend(found); failures['inchi_failed']+=ni;failures['parent_failed']+=np_
            failures['examples'] = (failures['examples']+examples)[:20]
            processed=min(processed+chunk_size,pf.metadata.num_rows)
            if processed % (chunk_size*20)==0 or processed==pf.metadata.num_rows:
                _log('pcba_identity_progress', rows=processed, total=pf.metadata.num_rows, matched_rows=len(matched))
    return matched, failures


def scan_labels(parquet, assays, matches, batch_size=2048):
    import pyarrow.parquet as pq
    by_row = {r['row_index']:r for r in matches}
    positive=np.zeros(len(assays),dtype=np.int64);negative=positive.copy();other=positive.copy()
    offset=0
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=batch_size,columns=assays):
        values=batch.to_pandas().to_numpy(dtype=float)
        positive+=(values==1).sum(axis=0);negative+=(values==0).sum(axis=0)
        other+=(np.isfinite(values)&(values!=0)&(values!=1)).sum(axis=0)
        for local in range(len(values)):
            if offset+local in by_row:
                keep=np.flatnonzero(np.isfinite(values[local]))
                by_row[offset+local]['nonmissing_assay_labels']={assays[j]:float(values[local,j]) for j in keep}
        offset+=len(values)
    stats=[]
    for i,assay in enumerate(assays):
        necessary=bool(positive[i]>=100 and negative[i]>=100 and positive[i]+negative[i]>=1000)
        stats.append({'assay_id':assay,'raw_positive':int(positive[i]),'raw_negative':int(negative[i]),
                      'raw_nonbinary_finite':int(other[i]),'raw_valid_binary':int(positive[i]+negative[i]),
                      'retained_training_head_status':'unknown' if necessary else 'cannot_pass_published_thresholds_on_any_subset',
                      'raw_counts_pass_necessary_thresholds':necessary})
    return stats


def assay_metadata(assays, cache, batch_size=20, known_only=False):
    present = {int(x.removeprefix('assayID-')) for x in assays}
    known = {1851, *TOX21_CYP_ASSAYS.values()}
    ordered=sorted(known)+sorted(present-known)
    if known_only: ordered=sorted(known)
    client=CachedHTTP(Path(cache)/'pubchem',timeout=60,retries=3,min_interval=.4)
    records={}; failures=[]
    for start in range(0,len(ordered),batch_size):
        ids=ordered[start:start+batch_size]
        url='https://pubchem.ncbi.nlm.nih.gov/rest/pug/assay/aid/'+','.join(map(str,ids))+'/description/JSON'
        try:
            path=client.fetch(url, f'description-{hashlib.sha256(url.encode()).hexdigest()[:20]}.json')
            raw=json.loads(path.read_text()); got=set()
            for item in raw.get('PC_AssayContainer',[]):
                desc=item.get('assay',{}).get('descr',{})
                aid=desc.get('aid',{}).get('id')
                if aid is None: continue
                aid=int(aid);got.add(aid)
                haystack=json.dumps(desc,ensure_ascii=False)
                hits=sorted(set(x.group(0) for x in CYP_TEXT.finditer(haystack)))
                records[aid]={'aid':aid,'assay_id':f'assayID-{aid}','present_in_raw_pcba':aid in present,
                    'title':desc.get('name',''),'potential_CYP_text':bool(hits),'CYP_text_hits':hits,
                    'known_CYP_assay':aid in known,'target':desc.get('target',[]),
                    'description_excerpt':' '.join(desc.get('description',[]))[:3000] if hits or aid in known else '',
                    'source_url':url,'response_sha256':_hash(path),'status':'retrieved'}
            for aid in set(ids)-got: failures.append({'aid':aid,'error':'missing_from_API_response','url':url})
        except Exception as exc:
            failures.extend({'aid':aid,'error':f'{type(exc).__name__}: {exc}','url':url} for aid in ids)
        _log('pcba_assay_metadata_progress', requested=min(start+batch_size,len(ordered)), total=len(ordered), failures=len(failures))
    return records, {'requested':len(ordered),'retrieved':len(records),'failures':failures,
        'all_raw_assays_queried':not known_only,'absence_claim_permitted':False,
        'note':'CYP regex is a broad retrieval flag, not an endpoint classification. Missing/failed descriptions remain unknown.'}


def conditional_hash_flags(matches):
    """Reproduce source expression for matched rows; historical DuckDB is unpinned."""
    try:
        import duckdb
        version=duckdb.__version__; con=duckdb.connect(':memory:')
        for row in matches:
            if row['pcba_inchi'] is not None:
                bucket=int(con.execute("SELECT abs(hash(? || '1')) % 100",[row['pcba_inchi']]).fetchone()[0])
                row['conditional_current_duckdb_bucket']=bucket
                row['conditional_hash_split']='validation' if bucket<10 else 'training_unless_benchmark_excluded'
            row['historical_checkpoint_training_membership']='unknown'
        con.close()
        return {'duckdb_version':version,'source_expression':"abs(hash(inchi || '1')) % 100 < 10",
                'historical_split_reconstructed':False,'reason':'Historical DuckDB version and actual benchmark exclusion set are unavailable; raw rows may also be InChI-deduplicated or fail graph building.'}
    except ImportError:
        for row in matches: row['historical_checkpoint_training_membership']='unknown'
        return {'historical_split_reconstructed':False,'reason':'DuckDB not installed; optional conditional hash check skipped.'}


def run_audit(args):
    import pyarrow.parquet as pq
    RDLogger.DisableLog('rdApp.*')
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    if (out/'audit.json').exists():raise FileExistsError('Audit outputs are frozen; use a new output directory')
    source=Path(args.monroe_source)
    for name,expected in SOURCE_HASHES.items():
        if _hash(source/name)!=expected:raise ValueError(f'Monroe pinned source mismatch: {name}')
    frames=[]; official_sources={}
    for split,path in [('train',args.official_train),('test',args.official_test)]:
        frame=pd.read_csv(path,usecols=['Molecule_Name','SMILES'],dtype=str);frame['split']=split
        if len(frame) != {'train':4905,'test':750}[split]:
            raise ValueError(f'Expected full official {split} cohort; got {len(frame)} rows')
        frames.append(frame);official_sources[split]={'path':str(Path(path).resolve()),'sha256':_hash(path),'rows':len(frame)}
    official=pd.concat(frames,ignore_index=True)
    if official.Molecule_Name.isna().any() or official.Molecule_Name.duplicated().any():raise ValueError('Official IDs must be unique and nonmissing across train/test')
    parquet,source_meta=stage_parquet(args.cache_root,args.zip_sha256)
    pf=pq.ParquetFile(parquet);columns=pf.schema_arrow.names
    assays=[c for c in columns if re.fullmatch(r'assayID-\d+',c)]
    if 'SMILES' not in columns or not assays:raise ValueError('Unexpected PCBA schema')
    schema={'rows':pf.metadata.num_rows,'columns':columns,'n_assays':len(assays),'source':source_meta}
    _json(out/'schema.json',schema);_log('pcba_schema',rows=schema['rows'],assays=len(assays))
    matches,identity_failures=match_identities(parquet,official,args.workers)
    # Intermediate matched identities are small and survive a later metadata outage.
    _json(out/'matched_identities.json',matches)
    stats=scan_labels(parquet,assays,matches,args.label_batch_size)
    _json(out/'assay_raw_counts.json',stats)
    descriptors,metadata_status=assay_metadata(assays,args.cache_root,known_only=args.known_assays_only)
    _json(out/'assay_descriptions.json',{str(k):v for k,v in descriptors.items()})
    _json(out/'assay_metadata_status.json',metadata_status)
    split_audit=conditional_hash_flags(matches)
    cyp_assays={v['assay_id'] for v in descriptors.values() if v['potential_CYP_text'] or v['known_CYP_assay']}
    cyp_assays |= {f'assayID-{aid}' for aid in {1851,*TOX21_CYP_ASSAYS.values()}}
    stats_map={x['assay_id']:x for x in stats}
    membership=defaultdict(lambda:{'exact_rows':[],'parent_rows':[],'nonmissing_assays':set(),'potential_cyp_assays':set(),
                                  'exact_cyp_assays':set(),'parent_cyp_assays':set()})
    for row in matches:
        labels=row.get('nonmissing_assay_labels',{})
        row['potential_CYP_labels']={k:v for k,v in labels.items() if k in cyp_assays}
        row['potential_CYP_head_status']={k:stats_map[k]['retained_training_head_status'] for k in row['potential_CYP_labels']}
        for kind,field in [('exact','exact_official_ids'),('parent','parent_official_ids')]:
            for identifier in row[field]:
                m=membership[identifier];m[kind+'_rows'].append(row['row_index'])
                m['nonmissing_assays'].update(labels);m['potential_cyp_assays'].update(row['potential_CYP_labels'])
                m[kind+'_cyp_assays'].update(row['potential_CYP_labels'])
    with gzip.open(out/'matched_rows.jsonl.gz','wt') as handle:
        for row in matches:handle.write(json.dumps(row,allow_nan=False)+'\n')
    rows=[]
    for original in official.to_dict('records'):
        m=membership[original['Molecule_Name']]
        if m['exact_rows'] or m['parent_rows']:
            rows.append({**original,'exact_pcba_rows':len(m['exact_rows']),'parent_pcba_rows':len(m['parent_rows']),
                'nonmissing_assay_count':len(m['nonmissing_assays']),
                'potential_CYP_assays':';'.join(sorted(m['potential_cyp_assays'])),
                'exact_inchi_CYP_assays':';'.join(sorted(m['exact_cyp_assays'])),
                'normalized_parent_CYP_assays':';'.join(sorted(m['parent_cyp_assays'])),
                'historical_checkpoint_training_membership':'unknown'})
    pd.DataFrame(rows,columns=['Molecule_Name','SMILES','split','exact_pcba_rows','parent_pcba_rows',
        'nonmissing_assay_count','potential_CYP_assays','exact_inchi_CYP_assays','normalized_parent_CYP_assays',
        'historical_checkpoint_training_membership']).to_csv(out/'matched_official_summary.csv',index=False)
    summary={}
    for split in ['train','test']:
        part=[r for r in rows if r['split']==split]
        summary[split]={'exact_inchi_overlap':sum(r['exact_pcba_rows']>0 for r in part),
            'normalized_parent_overlap':sum(r['parent_pcba_rows']>0 for r in part),
            'any_bioassay_label_overlap':sum(r['nonmissing_assay_count']>0 for r in part),
            'potential_CYP_label_overlap':sum(bool(r['potential_CYP_assays']) for r in part),
            'exact_inchi_CYP_label_overlap':sum(bool(r['exact_inchi_CYP_assays']) for r in part),
            'normalized_parent_CYP_label_overlap':sum(bool(r['normalized_parent_CYP_assays']) for r in part)}
    audit={'status':'completed_audit_membership_unresolved','created_utc':datetime.now(timezone.utc).isoformat(),
        'audit_source_sha256':_hash(Path(__file__)),
        'identity_normalization':{'source_sha256':_hash(Path(__file__).with_name('public_data.py')),
            'exact':'RDKit standard InChI of original parsed SMILES',
            'parent':'Existing FragmentParent + Uncharger + removal of stereochemistry; no tautomer canonicalization'},
        'monroe_revision':MONROE_REVISION,'monroe_source_hashes':SOURCE_HASHES,'source':source_meta,
        'official_sources':official_sources,'raw_pcba_rows':schema['rows'],'raw_pcba_assays':len(assays),
        'matched_pcba_rows':len(matches),'official_overlap':summary,'identity_failures':identity_failures,
        'assay_metadata':metadata_status,'conditional_split':split_audit,
        'potential_CYP_raw_assays':[v for v in descriptors.values() if v['present_in_raw_pcba'] and (v['potential_CYP_text'] or v['known_CYP_assay'])],
        'published_filter':{'training_only':True,'min_pos':100,'min_neg':100,'min_valid':1000,'reported_retained_heads':1089,
            'raw_assays_passing_necessary_thresholds':sum(x['raw_counts_pass_necessary_thresholds'] for x in stats),
            'reconstructed_exactly':False,'raw_count_note':'Failure on full raw counts proves failure on every training subset; passing raw counts does not establish historical head retention.'},
        'eligibility':'unresolved_requires_root_review_no_clean_pretraining_claim',
        'qualifications':[
            'Raw PCBA structure overlap is not itself proof of access to CYP labels.',
            'A nonmissing CYP-labelled raw match is potential supervised domain exposure; actual retained task and training membership remain unknown.',
            'Source excludes only collected Polaris/MoleculeACE test InChIs, with catch-and-continue load failures; no explicit challenge train/test exclusion appears.',
            'Actual historical benchmark exclusions, retained assay manifest, DuckDB version, InChI-dedup choice and successful graph membership are not shipped with the checkpoint.',
            'Binary PubChem activity outcomes differ from the challenge quantitative pIC50 labels; no equality of assay measurements is asserted.',
            'Do not declare absent CYP exposure merely from missing assay descriptions, IDs, parsing failures or absence of CYP text in column names.'],
        'versions':{'rdkit':rdBase.rdkitVersion,'numpy':np.__version__,'pandas':pd.__version__},
        'output_files':{p.name:{'sha256':_hash(p),'bytes':p.stat().st_size} for p in out.iterdir() if p.is_file()}}
    _json(out/'audit.json',audit);_log('pcba_audit_complete',overlap=summary,eligibility=audit['eligibility'])
    return audit


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--official-train',required=True);p.add_argument('--official-test',required=True)
    p.add_argument('--monroe-source',required=True);p.add_argument('--cache-root',required=True)
    p.add_argument('--output-dir',required=True);p.add_argument('--workers',type=int,default=8)
    p.add_argument('--label-batch-size',type=int,default=2048)
    p.add_argument('--zip-sha256',help='Optional previously verified SHA; publisher MD5 and byte count are always checked')
    p.add_argument('--known-assays-only',action='store_true',help='Quick incomplete metadata audit; never implies no other CYP assays')
    args=p.parse_args(argv)
    try:return run_audit(args)
    except Exception as exc:
        out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
        _json(out/'failure.json',{'status':'failed','error_type':type(exc).__name__,'error':str(exc)})
        raise


if __name__=='__main__':main()
