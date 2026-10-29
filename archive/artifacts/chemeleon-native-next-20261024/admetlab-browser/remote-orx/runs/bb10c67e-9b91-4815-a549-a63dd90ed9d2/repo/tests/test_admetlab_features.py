import copy,csv,json,tempfile,threading,time,unittest
from pathlib import Path
from night import admetlab_features as a

FIXTURE=Path(__file__).parent/'admetlab_fixture/cco-response.json'
class Fake:
 def __init__(self,events=None):self.calls=[];self.lock=threading.Lock();self.events=list(events or [])
 def call(self,payload,endpoint=None):
  with self.lock:
   self.calls.append((time.monotonic(),copy.deepcopy(payload),endpoint))
   event=self.events.pop(0) if self.events else None
  if event:return event
  if endpoint=='/api/single/admetFile':return 200,{},FIXTURE.with_suffix('.csv').read_bytes()
  response=json.loads(FIXTURE.read_text());response['data']['raw_smiles']=payload['SMILES']
  return 200,{},json.dumps(response).encode()

def config(tmp,n=1):
 root=Path(tmp);q=root/'queue.csv'
 with q.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['request_id','SMILES','priority']);w.writeheader()
  for i in range(n):w.writerow({'request_id':f'id{i}','SMILES':'CCO','priority':i%2})
 c=json.loads(Path('admetlab_config.json').read_text());c.update(queue_path=str(q),queue_sha256=a.sha(q),output_dir=str(root/'out'),id_map_path=str(root/'absent.csv'),id_map_sha256=None,queue_poll_seconds=.01)
 return c

class Tests(unittest.TestCase):
 def test_actual119_schema_and_no_invented_uncertainty(self):
  x=json.loads(FIXTURE.read_text());v=a.flatten_success(x,'CCO')
  self.assertEqual(v['endpoint_count'],119);self.assertEqual(len(v['features']),119)
  self.assertEqual(v['features']['ADMETLAB::distribution::PPB'],-0.11753691668567967)
  self.assertIn('ADMETLAB::metabolism::CYP2D6-inh',v['features'])
  self.assertFalse(any('uncertain' in k for k in v['features']))
  with self.assertRaises(a.ContractError):a.flatten_success(x,'CCN')
 def test_extra_uncertainty_categories_and_missing_retained(self):
  x=json.loads(FIXTURE.read_text());x['data']['data']['physicochemical'][0]['uncertainty']={'epistemic':.7}
  x['data']['data']['physicochemical'][1]['value']=None
  x['data']['data']['toxicityrule'][0]['value']=['alertA','-']
  v=a.flatten_success(x,'CCO');self.assertEqual(v['features']['ADMETLAB::physicochemical::MW::uncertainty::epistemic'],.7)
  self.assertIn('ADMETLAB::physicochemical::Vol',v['missing'])
  self.assertTrue(any(k.endswith('::count') and z==1 for k,z in v['features'].items()))
  self.assertFalse(any('::contains=' in k for k in v['features']))
 def test_atomic_cache_resume_and_identity(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=config(tmp,2);f=Fake();r=a.run(c,f);self.assertEqual(r['status'],'complete');self.assertEqual(len(f.calls),4)
   self.assertTrue((Path(c['output_dir'])/'priority0_milestone.json').exists())
   g=Fake();r=a.run(c,g);self.assertEqual(r['cached_successes'],2);self.assertEqual(len(g.calls),0)
   rows=list(csv.DictReader((Path(c['output_dir'])/'features.csv').open()));self.assertEqual([x['request_id'] for x in rows],['id0','id1'])
   raw,meta=a.paths(Path(c['output_dir']),'id0');m=json.loads(meta.read_text());m['submitted_SMILES']='CCN';a.save(meta,m)
   with self.assertRaises(a.ContractError):a.cached(Path(c['output_dir']),{'request_id':'id0','SMILES':'CCO','priority':'0'},c)
 def test_global_rate_and_retry_after(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=config(tmp,4);f=Fake();a.run(c,f);times=[x[0] for x in f.calls]
   self.assertTrue(all(b-a>=.24 for a,b in zip(times,times[1:])))
  with tempfile.TemporaryDirectory() as tmp:
   c=config(tmp);f=Fake([(429,{'Retry-After':'.6'},b'temporarily throttled')]);r=a.run(c,f)
   self.assertEqual(r['status'],'complete');self.assertEqual(len(f.calls),3);self.assertGreaterEqual(f.calls[1][0]-f.calls[0][0],.6)
 def test_circuit_breaker_and_failures_not_fake_success(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=config(tmp,10);c['max_inflight']=3
   f=Fake([(500,{},b'error')]*20);r=a.run(c,f)
   self.assertEqual(r['status'],'stopped_partial');self.assertEqual(r['successes'],0);self.assertEqual(len(f.calls),3)
   self.assertEqual(len(list((Path(c['output_dir'])/'errors').glob('*.json'))),3)
   self.assertFalse((Path(c['output_dir'])/'complete.json').exists())
 def test_csv_extra_endpoint_and_missing_legacy_columns(self):
  prediction=a.flatten_success(json.loads(FIXTURE.read_text()),'CCO')
  merged=a.merge_csv(prediction,FIXTURE.with_suffix('.csv').read_bytes())
  self.assertEqual(merged['features']['ADMETLAB::csv_extra::Other_assay_interference'],0.6620000004768372)
  self.assertIsNone(merged['features']['ADMETLAB::csv_extra::cl-int'])
  self.assertEqual(merged['csv_name_mapping']['CYP2D6-inh'],'CYP2D6-inh')
  self.assertEqual(merged['endpoint_count'],123)
  self.assertFalse(any('::contains=' in k for k in merged['features']))
 def test_resume_only_csv_after_prediction_succeeded(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=config(tmp);f=Fake([None,(500,{},b'error'),(500,{},b'error'),(500,{},b'error')]);r=a.run(c,f)
   self.assertEqual(r['status'],'stopped_partial');self.assertEqual(sum('SMILES' in call[1] for call in f.calls),1)
   g=Fake();r=a.run(c,g);self.assertEqual(r['status'],'complete');self.assertEqual(len(g.calls),1);self.assertIn('taskId',g.calls[0][1])
 def test_missing_endpoint_opens_schema_circuit(self):
  with tempfile.TemporaryDirectory() as tmp:
   c=config(tmp);x=json.loads(FIXTURE.read_text());x['data']['data']['metabolism'].pop()
   f=Fake([(200,{},json.dumps(x).encode())]);r=a.run(c,f)
   self.assertEqual(r['status'],'stopped_partial');self.assertEqual(r['successes'],0)

if __name__=='__main__':unittest.main()
