import csv,hashlib,io,json,threading,tempfile,unittest,sys
from pathlib import Path
from urllib.parse import parse_qs
from http.server import HTTPServer,BaseHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect import Collector,StopRun,ROOT
from playwright.sync_api import sync_playwright

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=None;cls.browser=None
    @classmethod
    def tearDownClass(cls):
        if cls.browser:cls.browser.close();cls.pw.stop()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
        with (ROOT/'tests/response.csv').open(encoding='utf-8-sig') as f:self.raw=list(csv.DictReader(f))
        self.values={r['raw_smiles']:r for r in self.raw};self.posts=[];self.post_texts=[];self.jobs={};self.mode='ok'
        with (self.path/'input.csv').open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['SMILES']);w.writerows([r['raw_smiles']] for r in self.raw)
        outer=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def send(self,status,body,kind='text/html',headers=None):
                self.send_response(status);self.send_header('Content-Type',kind)
                for k,v in (headers or {}).items():self.send_header(k,v)
                self.end_headers();self.wfile.write(body)
            def do_GET(self):
                if self.path=='/server/screening':
                    html='''<button id="profile-tab" role="tab" onclick="document.getElementById('form2').hidden=false">Enter a list of SMILES</button><form hidden id="form2" action="/server/screeningCal" method="post"><input type="hidden" name="method" value="2"><textarea name="smiles-list"></textarea><button type="submit">Submit</button></form>'''
                    if outer.mode=='alter_on_submit':
                        html+="<script>document.querySelector('form').addEventListener('submit',()=>{let t=document.querySelector('textarea');t.value=t.value.replace('+',' ');});</script>"
                    return self.send(200,html.encode())
                if self.path.startswith('/server/result/'):
                    job=self.path.split('/')[3]
                    if self.path.endswith('/download/csv'):
                        columns=list(outer.raw[0])
                        if outer.mode=='missing_column':columns.remove('MW')
                        s=io.StringIO();w=csv.DictWriter(s,fieldnames=columns,extrasaction='ignore');w.writeheader()
                        result=[dict(outer.values[x]) for x in outer.jobs[job][::-1]]
                        if outer.mode=='wrong_identity':result[0]['raw_smiles']='unknown-compound'
                        w.writerows(result)
                        return self.send(200,s.getvalue().encode(),'text/csv',{'Content-Disposition':f'attachment; filename="{job}.csv"'})
                    return self.send(200,f'<a href="/server/result/{job}/download/csv">Download CSV</a>'.encode())
                self.send(404,b'not found')
            def do_POST(self):
                body=self.rfile.read(int(self.headers['Content-Length']))
                fields=parse_qs(body.decode('utf-8'),keep_blank_values=True)
                assert fields['method']==['2']
                text=fields['smiles-list'][0];outer.post_texts.append(text)
                smiles=text.replace('\r\n','\n').split('\n');outer.posts.append(smiles)
                if outer.mode=='integrity_only':return self.send(200,b'<p>accepted</p>')
                if outer.mode=='429':return self.send(429,b'<h1>429 Too Many Requests</h1>',headers={'Retry-After':'120'})
                job=str(len(outer.jobs)+1);outer.jobs[job]=smiles
                self.send(303,b'',headers={'Location':'/server/result/'+job})
        self.server=HTTPServer(('127.0.0.1',0),Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        self.collector=Collector(self.path/'input.csv',self.path/'output',2,base_url=self.base)
        cls=type(self)
        if self._testMethodName.startswith('test_current_user_chrome'):
            if cls.browser:cls.browser.close();cls.pw.stop();cls.browser=None;cls.pw=None
            self.context=None;self.page=None
        else:
            if cls.browser is None:
                cls.pw=sync_playwright().start();cls.browser=cls.pw.chromium.launch(channel='chrome',headless=True)
            self.context=cls.browser.new_context(accept_downloads=True);self.page=self.context.new_page()
    def tearDown(self):
        if self.context:self.context.close()
        self.collector.close();self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def test_actual_chrome_text_download_merge_and_restart(self):
        for i in range(2):self.collector.process(self.page,i,10000)
        report=self.collector.merge();self.assertEqual(report['status'],'complete');self.assertEqual(report['successes'],3)
        with (self.path/'output/results/admetlab_merged.csv').open() as f:merged=list(csv.DictReader(f))
        self.assertEqual({r['Molecule_SMILES'] for r in merged},set(self.values))
        self.assertEqual(len(merged),3);self.assertEqual(len(self.posts),2)
        self.collector.close();self.collector=Collector(self.path/'input.csv',self.path/'output',2,base_url=self.base)
        for i in range(2):self.collector.process(self.page,i,10000)
        self.assertEqual(len(self.posts),2,'Restart must not resubmit completed batches')
        self.assertTrue((self.path/'output/results/complete.json').is_file())
    def test_429_stops_and_honors_retry_after(self):
        self.mode='429'
        with self.assertRaises(StopRun):self.collector.process(self.page,0,10000)
        self.assertEqual(len(self.posts),1);self.assertEqual(self.collector.state(0)['phase'],'rate_limited')
        with self.assertRaises(StopRun):self.collector.process(self.page,0,10000,retry_rejected=True)
        self.assertEqual(len(self.posts),1)
        self.assertIsNone(self.collector.merge());self.assertFalse((self.path/'output/results/complete.json').exists())
    def test_uncertain_submission_not_repeated_and_result_url_recovers(self):
        self.collector.set_state(0,phase='uncertain')
        with self.assertRaises(StopRun):self.collector.process(self.page,0,10000)
        self.assertEqual(len(self.posts),0)
        self.jobs['owned']=[r['SMILES'] for r in self.collector.batches[0]]
        self.collector.recover_url('1='+self.base+'/server/result/owned')
        self.collector.process(self.page,0,10000)
        self.assertEqual(len(self.posts),0);self.assertTrue(self.collector.completed(0))
        self.assertEqual(self.collector.merge()['status'],'partial')
    def test_detects_changed_saved_result(self):
        self.collector.process(self.page,0,10000)
        with (self.collector.folder(0)/'result.csv').open('a') as f:f.write('corrupted\n')
        with self.assertRaises(StopRun):self.collector.process(self.page,0,10000)
    def test_missing_endpoint_rejected(self):
        self.mode='missing_column'
        with self.assertRaises(ValueError):self.collector.process(self.page,0,10000)
        self.assertEqual(self.collector.state(0)['phase'],'invalid_result')
        self.assertIsNone(self.collector.merge())
    def test_unknown_molecule_rejected(self):
        self.mode='wrong_identity'
        with self.assertRaises(ValueError):self.collector.process(self.page,0,10000)
        self.assertEqual(self.collector.state(0)['phase'],'invalid_result')
        self.assertIsNone(self.collector.merge())
    def test_rejects_changed_inputs_for_existing_plan(self):
        self.collector.close()
        with self.assertRaises(StopRun):Collector(self.path/'input.csv',self.path/'output',1,base_url=self.base)
        self.collector=Collector(self.path/'input.csv',self.path/'output',2,base_url=self.base)
    def test_submit_time_mutation_is_blocked_before_network(self):
        self.mode='alter_on_submit'
        self.assertTrue(any('+' in r['SMILES'] for r in self.collector.batches[0]))
        with self.assertRaises(StopRun):self.collector.process(self.page,0,10000)
        self.assertEqual(self.posts,[])
        self.assertEqual(self.collector.state(0)['phase'],'integrity_error')
    def test_special_smiles_survive_text_form_and_download(self):
        special=['F/C=C\\F','N[C@@H](C)C(=O)O','[NH4+].[Cl-]','C%12CCCCC%12','C#N','c1cc[nH]c1']
        self.collector.close()
        with (self.path/'special.csv').open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['SMILES']);w.writerows([s] for s in special)
        self.values={s:{**self.raw[0],'raw_smiles':s,'smiles':s} for s in special}
        self.collector=Collector(self.path/'special.csv',self.path/'special-output',980,base_url=self.base)
        self.collector.process(self.page,0,10000)
        self.assertEqual(self.posts,[special])
        rows,_=self.collector.validate(0)
        self.assertEqual({r['SMILES'] for r in rows},set(special))
    def test_all_32421_smiles_roundtrip_through_real_chrome(self):
        self.mode='integrity_only';self.collector.close()
        self.collector=Collector(ROOT/'data/molecules.csv',self.path/'full-output',500,base_url=self.base)
        self.assertEqual(len(self.collector.rows),32421);self.assertEqual(len(self.collector.batches),65)
        for i,batch in enumerate(self.collector.batches):
            self.page.goto(self.base+'/server/screening')
            form=self.collector.fill_text_form(self.page,i)
            with self.page.expect_navigation(wait_until='domcontentloaded'):
                form.get_by_role('button',name='Submit',exact=True).click(no_wait_after=True)
            self.assertEqual(self.posts[-1],[r['SMILES'] for r in batch])
            self.assertEqual(self.post_texts[-1].replace('\r\n','\n'),self.collector.payload(i))
        actual=[s for batch in self.posts for s in batch]
        expected=[r['SMILES'] for batch in self.collector.batches for r in batch]
        self.assertEqual(actual,expected)
        report={'source_queue_sha256':hashlib.sha256((ROOT/'data/molecules.csv').read_bytes()).hexdigest(),
            'molecules':len(actual),'batches':len(self.posts),'max_batch':max(map(len,self.posts)),
            'exact_match':True,'verified_stages':['source SMILES','saved UTF8 list','Chrome textarea input_value','decoded HTTP form received by local test server'],
            'transport':'application/x-www-form-urlencoded; CRLF/LF separators normalized only',
            'character_counts':{c:sum(s.count(c) for s in actual) for c in ['\\','/','@','+','-','#','%','[',']','.','(',')']},
            'external_admetlab_requests':0}
        (ROOT/'smiles-integrity-check.json').write_text(json.dumps(report,indent=2)+'\n')
    @unittest.skipUnless(sys.platform=='darwin','Native Google Chrome control requires macOS')
    def test_current_user_chrome_submit_download_and_merge(self):
        from current_chrome import CurrentChrome,process
        chrome=CurrentChrome(self.base)
        try:
            for i in range(2):process(self.collector,chrome,i,20,False)
            self.assertEqual(len(self.posts),2)
            self.assertEqual(self.collector.merge()['status'],'complete')
            for i,batch in enumerate(self.collector.batches):self.assertEqual(self.posts[i],[r['SMILES'] for r in batch])
        finally:chrome.close_owned_tab()
    @unittest.skipUnless(sys.platform=='darwin','Native Google Chrome control requires macOS')
    def test_current_user_chrome_all_32421_smiles_exact(self):
        from current_chrome import CurrentChrome
        chrome=CurrentChrome(self.base)
        try:
            chrome.goto(self.base+'/server/screening')
            with (ROOT/'data/molecules.csv').open() as stream:rows=list(csv.DictReader(stream))
            for i in range(0,len(rows),500):
                expected='\n'.join(r['SMILES'] for r in rows[i:i+500]);self.assertEqual(chrome.fill(expected),expected)
            specials='F/C=C\\F\n[NH4+].[Cl-]\nN[C@@H](C)C(=O)O\nC%12CCCCC%12\nC#N'
            self.assertEqual(chrome.fill(specials),specials)
            report={'molecules':len(rows),'batches':(len(rows)+499)//500,'batch_size':500,
                    'browser':'ordinary user Google Chrome via Apple Events','exact_character_match':True,
                    'extra_stereo_charge_ring_tests':True,'external_admetlab_requests':0}
            (ROOT/'native-chrome-integrity-check.json').write_text(json.dumps(report,indent=2)+'\n')
        finally:chrome.close_owned_tab()
if __name__=='__main__':unittest.main()
