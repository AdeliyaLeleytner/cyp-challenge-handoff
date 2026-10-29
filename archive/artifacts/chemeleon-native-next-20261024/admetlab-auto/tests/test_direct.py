import csv,io,json,sys,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from urllib.parse import parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collect import Collector,ROOT,StopRun
from direct_http import Direct

class Tests(unittest.TestCase):
 def test_roundtrip_resume_and_limits(self):
  with (ROOT/'tests/response.csv').open(encoding='utf-8-sig') as f:records=list(csv.DictReader(f))
  for mode in ('ok','429','bad_identity'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);posts=[]
    class Handler(BaseHTTPRequestHandler):
     def log_message(self,*a):pass
     def send(self,status,data,**headers):
      self.send_response(status)
      for k,v in headers.items():self.send_header(k.replace('_','-'),v)
      self.end_headers();self.wfile.write(data)
     def do_GET(self):
      if self.path=='/server/screening':return self.send(200,b'<form id="form2" action="/server/screeningCal" method="post"><input name="method" value="2"></form>')
      if self.path.endswith('download/csv'):
       rows=[dict(r) for r in records[::-1]]
       if mode=='bad_identity':rows[0]['raw_smiles']='BROKEN'
       text=io.StringIO();writer=csv.DictWriter(text,fieldnames=records[0]);writer.writeheader();writer.writerows(rows)
       return self.send(200,text.getvalue().encode())
      return self.send(200,b'<a href="/server/result/1/download/csv">CSV</a>')
     def do_POST(self):
      posts.append(parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())['smiles-list'][0])
      if mode=='429':return self.send(429,b'limit',Retry_After='120')
      self.send(303,b'',Location='/server/result/1')
    server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    path=root/'input.csv'
    with path.open('w') as f:
     w=csv.writer(f);w.writerow(['SMILES']);w.writerows([[r['raw_smiles']] for r in records])
    c=Collector(path,root/'out',500,base_url='http://127.0.0.1:'+str(server.server_port));d=Direct(c,'lo0',10)
    try:
     if mode=='ok':
      d.process(0);d.process(0);self.assertTrue(c.completed(0));self.assertEqual(len(posts),1)
      self.assertEqual(posts[0].splitlines(),[r['raw_smiles'] for r in records])
     else:
      with self.assertRaises(Exception):d.process(0)
      with self.assertRaises(StopRun):d.process(0)
      self.assertEqual(len(posts),1);self.assertFalse(c.completed(0))
    finally:c.close();server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
