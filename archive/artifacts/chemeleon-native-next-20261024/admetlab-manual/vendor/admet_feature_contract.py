"""Standard-library-only readiness gate for the complete ADMETlab feature cache."""
from pathlib import Path
import argparse,csv,hashlib,json,math,sys

METADATA = ('request_id','SMILES','priority','service_smiles','taskid')

class CacheNotReady(ValueError):
    pass


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def read_json(path):
    path=Path(path)
    if not path.is_file():raise CacheNotReady(f'Required cache manifest missing: {path}')
    try:return json.loads(path.read_text())
    except (ValueError,OSError) as exc:raise CacheNotReady(f'Invalid cache manifest: {path}') from exc


def verify_ready(cfg):
    if cfg.get('initialization')!='scratch':
        raise CacheNotReady('This feature arm explicitly uses the native scratch MAE champion; CheMeleon requires its own child/configuration')
    root=Path(cfg['feature_cache_dir']);assets=Path(cfg['assets'])
    paths={'feature_table':root/'features.csv','feature_schema':root/'feature-schema.json',
           'id_map':assets/'admetlab-id-map.csv','queue':assets/'admetlab-queue.csv',
           'complete':root/'complete.json','status':root/'status.json',
           'pending':root/'missing-or-pending.csv','id_map_provenance':root/'id-map-provenance.json'}
    for name,path in paths.items():
        if not path.is_file():raise CacheNotReady(f'Required {name} file missing: {path}')
    digest={name:sha(path) for name,path in paths.items()}
    if digest['queue']!=cfg['queue_sha256'] or digest['id_map']!=cfg['id_map_sha256']:
        raise CacheNotReady('Frozen acquisition queue or source-ID map changed')
    done=read_json(paths['complete']);status=read_json(paths['status']);schema=read_json(paths['feature_schema'])
    id_source=read_json(paths['id_map_provenance'])
    if cfg.get('source_mode')!='web_default' or cfg.get('backend')!='documented_web_batch' or cfg.get('api_probe_vectors_used') is not False:
        raise CacheNotReady('This arm requires the consistent documented web_default regime, without API probe vectors')
    for label,manifest in [('completion',done),('status',status),('schema',schema)]:
        if manifest.get('source_mode')!=cfg['source_mode'] or manifest.get('backend')!=cfg['backend'] or manifest.get('api_probe_vectors_used') is not False:
            raise CacheNotReady('Mixed or unproven ADMETlab prediction regime in '+label)
    if done.get('status')!='complete' or status.get('status')!='complete':
        raise CacheNotReady('Feature acquisition is partial, running or failed; full four-member training waits for complete cache')
    if done.get('queue_sha256')!=cfg['queue_sha256'] or status.get('queue_sha256')!=cfg['queue_sha256']:
        raise CacheNotReady('Feature completion belongs to a different acquisition queue')
    if id_source.get('sha256')!=cfg['id_map_sha256']:
        raise CacheNotReady('Acquisition did not use this frozen source-ID mapping')
    if done.get('features_sha256')!=digest['feature_table']:
        raise CacheNotReady('Feature table does not match its completion hash')
    if done.get('no_endpoint_filtering') is not True:
        raise CacheNotReady('All-endpoint acquisition flag is absent')
    with paths['queue'].open() as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=['request_id','SMILES','priority']:raise CacheNotReady('Unexpected frozen queue header')
        queue={}
        for row in reader:
            req=row['request_id'];smi=row['SMILES']
            if not req or not smi or hashlib.sha256(smi.encode()).hexdigest()!=req:raise CacheNotReady('Queue request ID/SMILES mismatch')
            if req in queue:raise CacheNotReady('Duplicate acquisition request ID')
            queue[req]=smi
    n=len(queue)
    if not n or done.get('rows')!=n or status.get('queue_size')!=n or status.get('successes')!=n or status.get('remaining')!=0:
        raise CacheNotReady('Completion counts do not cover the entire frozen acquisition queue')
    with paths['pending'].open() as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=['request_id','SMILES','priority'] or next(reader,None) is not None:
            raise CacheNotReady('Missing or pending feature rows remain')
    columns=schema.get('feature_columns')
    if not isinstance(columns,list) or not columns or len(set(columns))!=len(columns) or any(not isinstance(c,str) or not c.startswith('ADMETLAB::') for c in columns):
        raise CacheNotReady('Explicit unique all-endpoint feature schema is missing')
    forbidden=set(cfg.get('forbidden_legacy_api_feature_columns',[]))&set(columns)
    if forbidden:raise CacheNotReady('Legacy API-only empty columns appeared in the fixed web_default contract; review source schema rather than fabricate/filter them: '+','.join(sorted(forbidden)))
    expected=set(cfg['expected_endpoint_identities'])|{'csv_extra::'+s for s in cfg['expected_csv_extra_names']}
    observed={e['category']+'::'+e['name'] for e in schema.get('endpoint_schema',[])}
    if not expected<=observed:raise CacheNotReady('Required endpoint identities missing: '+','.join(sorted(expected-observed)))
    for endpoint in expected:
        prefix='ADMETLAB::'+endpoint
        if not any(c==prefix or c.startswith(prefix+'::') for c in columns):
            raise CacheNotReady('Endpoint has no declared numeric input representation: '+endpoint)
    seen=set();missing_values=0
    with paths['feature_table'].open() as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=list(METADATA)+columns:raise CacheNotReady('Feature table/schema column order mismatch')
        for row in reader:
            req=row['request_id']
            if req not in queue or row['SMILES']!=queue[req] or req in seen:raise CacheNotReady('Feature request IDs/SMILES do not match the unique frozen queue')
            seen.add(req)
            for col in columns:
                value=row[col]
                if value=='':missing_values+=1;continue
                try:number=float(value)
                except (ValueError,TypeError) as exc:raise CacheNotReady('Non-numeric feature value: '+col) from exc
                if not math.isfinite(number):raise CacheNotReady('Nonfinite feature value: '+col)
    if seen!=set(queue):raise CacheNotReady('Feature cache does not cover every acquisition request')
    # The producer writes atomically; nevertheless reject a simultaneous change.
    for name in ['feature_table','feature_schema','id_map','queue','complete']:
        if sha(paths[name])!=digest[name]:raise CacheNotReady('Feature inputs changed during readiness validation: '+name)
    return {'status':'ready','rows':n,'feature_count':len(columns),'feature_columns':columns,
            'numeric_missing_values':missing_values,'input_sha256':digest,
            'source_paths':{k:str(v) for k,v in paths.items()},
            'teacher_training_membership':'unknown; own fold exclusions do not establish external teacher label independence',
            'schema_note':schema.get('schema_note',''),'source_mode':cfg['source_mode'],'backend':cfg['backend'],'api_probe_vectors_used':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',default='admet_feature_config.json');args=parser.parse_args()
    try:report=verify_ready(read_json(args.config))
    except CacheNotReady as exc:
        print(json.dumps({'event':'admet_feature_cache_not_ready','reason':str(exc)}),flush=True);raise SystemExit(2)
    print(json.dumps({'event':'admet_feature_cache_ready',**{k:v for k,v in report.items() if k not in ['feature_columns','source_paths']}}),flush=True)

if __name__=='__main__':main()
