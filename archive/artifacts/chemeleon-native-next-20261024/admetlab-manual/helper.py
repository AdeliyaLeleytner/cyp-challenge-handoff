#!/usr/bin/env python3
"""Local manual ADMETlab desk. No outbound HTTP or automatic website submission."""
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qs
from types import SimpleNamespace
import argparse, csv, hashlib, io, json, secrets, subprocess, sys, time, webbrowser
from vendor.admetlab_web import parse_batch, export, PROVENANCE
from vendor.admetlab_features import save, sha

ROOT=Path(__file__).resolve().parent
SITE='https://admetlab3.scbdd.com/server/screening'

class Store:
    def __init__(self, root, batch_size=1000):
        self.root=Path(root);self.cfg=json.loads((self.root/'web-config.json').read_text())
        with (self.root/'queue.csv').open() as stream:
            self.rows=list(csv.DictReader(stream))
        assert len({r['SMILES'] for r in self.rows})==len(self.rows)==len({r['request_id'] for r in self.rows})
        assert all(hashlib.sha256(r['SMILES'].encode()).hexdigest()==r['request_id'] for r in self.rows)
        self.lookup={r['SMILES']:r for r in self.rows}
        self.cfg.update(queue_sha256=sha(self.root/'queue.csv'),id_map_path=str(self.root/'id-map.csv'),id_map_sha256=sha(self.root/'id-map.csv'))
        self.started=time.monotonic();self.results={};self.opened=set();self.batch_size=batch_size
        self.imports=self.root/'imports';self.imports.mkdir(exist_ok=True)
        self.batches=[]
        # Keep official compounds first, without crossing the priority boundary.
        for priority in sorted({r['priority'] for r in self.rows},key=int):
            group=[r for r in self.rows if r['priority']==priority]
            for start in range(0,len(group),batch_size):self.batches.append(group[start:start+batch_size])
        self.batch_dir=self.root/'batches';self.batch_dir.mkdir(exist_ok=True)
        for i,rows in enumerate(self.batches):
            with (self.batch_dir/f'batch-{i+1:03}.csv').open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['SMILES']);w.writerows([r['SMILES']] for r in rows)
        for path in sorted(self.imports.glob('*.csv')):self.import_bytes(path.read_bytes(),path.name,persist=False)
    def import_bytes(self, body, name, persist=True):
        digest=hashlib.sha256(body).hexdigest()
        if persist and (self.imports/(digest+'.csv')).exists():return {'message':'Этот файл уже учтён.','added':0}
        raw=list(csv.DictReader(io.StringIO(body.decode('utf-8-sig'))))
        if not raw:raise ValueError('Пустой CSV.')
        if len(body)>32*1024*1024:raise ValueError('Файл больше 32 МБ.')
        if any(r.get('raw_smiles') not in self.lookup for r in raw):raise ValueError('В CSV есть неизвестные молекулы или отсутствует raw_smiles. Нужна полная CSV-выгрузка веб-режима ADMETlab.')
        if len({r['raw_smiles'] for r in raw})!=len(raw):raise ValueError('Повторяющиеся raw_smiles в одном CSV.')
        inputs=[self.lookup[r['raw_smiles']] for r in raw]
        success,failed,audit=parse_batch(body,inputs,self.cfg,'manual-'+digest)
        if failed:raise ValueError('Сервис пропустил или отклонил молекулы: '+str(failed[:2]))
        shared_schema=success[0]['schema']
        for r in success:
            r['schema']=shared_schema
            old=self.results.get(r['request_id'])
            if old and any(old[k]!=r[k] for k in ('features','categories','service_smiles')):
                raise ValueError('Конфликт с ранее загруженным результатом. Файлы не смешаны; сохранён прежний результат.')
        added=sum(r['request_id'] not in self.results for r in success)
        if persist:
            target=self.imports/(digest+'.csv');tmp=target.with_suffix('.tmp');tmp.write_bytes(body);tmp.replace(target)
            save(self.imports/(digest+'.json'),{'original_filename':Path(name).name,'sha256':digest,'rows':len(success),
                'imported_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source_attestation':'user-selected web export; not independently authenticated',**PROVENANCE})
        for r in success:self.results[r['request_id']]=r
        return {'added':added,'message':f'Добавлено молекул: {added}. Всего: {len(self.results)} / {len(self.rows)}.'}
    def status(self):
        return {'total':len(self.rows),'done':len(self.results),'site':SITE,'batches':[
            {'id':i+1,'n':len(rows),'done':sum(r['request_id'] in self.results for r in rows),
             'priority':rows[0]['priority'],'opened':i+1 in self.opened} for i,rows in enumerate(self.batches)]}
    def export(self):
        if not self.results:raise ValueError('Сначала добавьте CSV-результаты.')
        out=self.root/'admetlab_web_all';out.mkdir(exist_ok=True)
        state='complete' if len(self.results)==len(self.rows) else 'partial_manual_import'
        report=export(out,self.rows,self.results,[],self.cfg,SimpleNamespace(requests=0,reason=None),self.started,state)
        report.update(acquisition_method='manual_browser_csv',new_successes_per_second=None,
                      estimated_remaining_seconds=None,global_requests_per_second=None,max_inflight=None)
        save(out/'status.json',report)
        save(out/'id-map-provenance.json',{'path':str(self.root/'id-map.csv'),'sha256':self.cfg['id_map_sha256']})
        if state=='complete':
            save(out/'complete.json',dict(status='complete',queue_sha256=self.cfg['queue_sha256'],rows=len(self.rows),
                features_sha256=sha(out/'features.csv'),no_endpoint_filtering=True,**PROVENANCE))
        return {'message':f'Сохранено {len(self.results)} / {len(self.rows)}. '+('Полный набор готов.' if state=='complete' else 'Набор неполный; обучение ещё не готово.'),
                'path':str(out/'features.csv')}

def handler_factory(store,token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def valid(self):
            expected=f'127.0.0.1:{self.server.server_port}'
            origin=self.headers.get('Origin')
            return self.headers.get('Host')==expected and (origin is None or origin=='http://'+expected) and parse_qs(urlsplit(self.path).query).get('token')==[token]
        def send(self,status,body,kind='application/json',filename=None):
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
            self.end_headers();self.wfile.write(body)
        def json(self,obj,status=200):self.send(status,json.dumps(obj,ensure_ascii=False).encode())
        def do_GET(self):
            if not self.valid():return self.json({'error':'Forbidden'},403)
            path=urlsplit(self.path).path
            if path=='/':return self.send(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8')
            if path=='/status':return self.json(store.status())
            if path.startswith('/batch/'):
                try:
                    i=int(path.split('/')[-1]);assert 1<=i<=len(store.batches)
                except (ValueError,AssertionError):return self.json({'error':'Unknown batch'},404)
                return self.send(200,(store.batch_dir/f'batch-{i:03}.csv').read_bytes(),'text/csv; charset=utf-8',f'batch-{i:03}.csv')
            return self.json({'error':'Not found'},404)
        def do_POST(self):
            if not self.valid():return self.json({'error':'Forbidden'},403)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<40*1024*1024:raise ValueError('Invalid request size')
                obj=json.loads(self.rfile.read(length));path=urlsplit(self.path).path
                if path=='/import':
                    if obj.get('source')!='web_default':raise ValueError('Нужна выгрузка веб-режима ADMETlab3.')
                    result=store.import_bytes(obj['text'].encode(),obj['name'])
                elif path=='/export':result=store.export()
                elif path=='/opened':
                    ids=obj['ids']
                    if not isinstance(ids,list) or any(type(i)!=int or not 1<=i<=len(store.batches) for i in ids):raise ValueError('Invalid batch')
                    store.opened.update(ids);result={'ok':True}
                elif path=='/folder':
                    if sys.platform!='darwin':raise ValueError('Открытие Finder доступно только на Mac.')
                    subprocess.run(['open',str(store.batch_dir)],check=True);result={'ok':True}
                else:return self.json({'error':'Not found'},404)
                self.json(result)
            except (ValueError,KeyError,UnicodeError,AssertionError) as e:self.json({'error':str(e)},400)
    return Handler

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--no-open',action='store_true');ap.add_argument('--port',type=int,default=0)
    ap.add_argument('--batch-size',type=int,default=1000);args=ap.parse_args()
    if not 1<=args.batch_size<=1000:ap.error('batch-size must be1..1000')
    import fcntl
    lock=(ROOT/'manual.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        info=json.loads((ROOT/'session.json').read_text())
        print('Помощник уже работает: '+info['url'])
        if not args.no_open:webbrowser.open(info['url'])
        return
    store=Store(ROOT,args.batch_size);token=secrets.token_urlsafe(24)
    server=HTTPServer(('127.0.0.1',args.port),handler_factory(store,token))
    url=f'http://127.0.0.1:{server.server_port}/?token={token}'
    save(ROOT/'session.json',{'url':url,'port':server.server_port})
    print('Помощник ADMETlab: '+url,flush=True)
    print('Оставьте это окно открытым. Ctrl+C завершает помощник. Загрузка на сайт — только вручную.',flush=True)
    if not args.no_open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
