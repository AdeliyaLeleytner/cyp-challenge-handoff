import csv, hashlib, io, json, shutil, tempfile, threading, unittest, urllib.request, urllib.error
from pathlib import Path
from http.server import HTTPServer
from helper import Store, ROOT, handler_factory
from vendor.admet_feature_contract import verify_ready

class ManualTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
        shutil.copy(ROOT/'web-config.json',self.p/'web-config.json')
        self.body=(ROOT/'test-example.csv').read_bytes()
        self.raw=list(csv.DictReader(io.StringIO(self.body.decode('utf-8-sig'))))
        self.queue=[dict(request_id=hashlib.sha256(r['raw_smiles'].encode()).hexdigest(),SMILES=r['raw_smiles'],priority='0') for r in self.raw]
        with (self.p/'queue.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['request_id','SMILES','priority']);w.writeheader();w.writerows(self.queue)
        (self.p/'id-map.csv').write_text('molecule_name,SMILES,request_id\n')
        self.store=Store(self.p,2)
    def tearDown(self):self.tmp.cleanup()
    def csv(self,rows):
        s=io.StringIO();w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);return s.getvalue().encode()
    def test_reorder_duplicate_restart_and_export_contract(self):
        r=self.store.import_bytes(self.csv(self.raw[::-1]),'download.csv');self.assertEqual(r['added'],3)
        self.assertEqual(self.store.import_bytes(self.csv(self.raw[::-1]),'download.csv')['added'],0)
        restored=Store(self.p,2);self.assertEqual(len(restored.results),3);restored.export()
        cfg=restored.cfg.copy();mapping=cfg['web_column_to_endpoint']
        cfg.update(initialization='scratch',feature_cache_dir=str(self.p/'admetlab_web_all'),assets=str(self.p),
                   expected_endpoint_identities=['::'.join(v) for v in mapping.values() if v[0]!='csv_extra'],
                   expected_csv_extra_names=['Other_assay_interference'])
        shutil.copy(self.p/'queue.csv',self.p/'admetlab-queue.csv');shutil.copy(self.p/'id-map.csv',self.p/'admetlab-id-map.csv')
        result=verify_ready(cfg);self.assertEqual(result['rows'],3);self.assertGreaterEqual(result['feature_count'],120)
    def test_partial_export_never_marks_complete(self):
        self.store.import_bytes(self.csv(self.raw[:1]),'partial.csv');self.store.export()
        self.assertFalse((self.p/'admetlab_web_all/complete.json').exists())
        self.assertEqual(sum(b['done'] for b in self.store.status()['batches']),1)
    def test_reject_unknown_duplicate_missing_and_conflict(self):
        bad=[dict(self.raw[0])];bad[0]['raw_smiles']='not a queued molecule'
        with self.assertRaises(ValueError):self.store.import_bytes(self.csv(bad),'bad.csv')
        with self.assertRaises(ValueError):self.store.import_bytes(self.csv([self.raw[0],self.raw[0]]),'dup.csv')
        bad=[dict(r) for r in self.raw]
        for r in bad:del r['MW']
        with self.assertRaises(ValueError):self.store.import_bytes(self.csv(bad),'missing.csv')
        self.store.import_bytes(self.body,'good.csv');bad=[dict(r) for r in self.raw];bad[0]['MW']='9999'
        with self.assertRaises(ValueError):self.store.import_bytes(self.csv(bad),'conflict.csv')
        self.assertEqual(len(list(self.store.imports.glob('*.csv'))),1)
    def test_http_local_auth_download_and_import(self):
        server=HTTPServer(('127.0.0.1',0),handler_factory(self.store,'secret'))
        t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(base+'/status')
            self.assertEqual(json.load(urllib.request.urlopen(base+'/status?token=secret'))['total'],3)
            self.assertTrue(urllib.request.urlopen(base+'/batch/1?token=secret').read().startswith(b'SMILES'))
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(base+'/batch/../helper.py?token=secret')
            payload=json.dumps({'source':'web_default','name':'x.csv','text':self.body.decode('utf-8-sig')}).encode()
            req=urllib.request.Request(base+'/import?token=secret',data=payload,headers={'Content-Type':'application/json','Origin':'https://example.org'})
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(req)
            req=urllib.request.Request(base+'/import?token=secret',data=payload,headers={'Content-Type':'application/json','Origin':base})
            self.assertEqual(json.load(urllib.request.urlopen(req))['added'],3)
        finally:server.shutdown();server.server_close();t.join()
if __name__=='__main__':unittest.main()
