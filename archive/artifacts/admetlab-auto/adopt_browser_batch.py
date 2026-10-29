"""Validate browser-downloaded CSV and checkpoint externally clicked batches."""
import argparse,shutil
from pathlib import Path
from collect import Collector,save,sha,now,StopRun
from chrome_routed import check_route
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('action',choices=['begin','adopt','failed']);p.add_argument('batch',type=int)
p.add_argument('--csv',type=Path);p.add_argument('--url');p.add_argument('--reason')
a=p.parse_args();c=Collector(ROOT/'../../cyp-admet500-pilot-20261025/next-official-5155.csv',Path.home()/'Downloads/ADMETlab-Chrome-direct-500',500);i=a.batch-1
try:
 if not 0<=i<len(c.batches):raise StopRun('Invalid batch number')
 if a.action=='begin':
  if c.state(i)['phase']!='pending':raise StopRun('Not pending; refuse repeated submission')
  save(c.folder(i)/'normal-click-route.json',check_route());c.payload(i)
  c.set_state(i,phase='submitting',submission_mode='normal_browser_click_after_pause',attempt=int(c.state(i).get('attempt',0))+1,error=None)
 elif a.action=='adopt':
  if not a.csv or not a.url or not c.result_url(a.url):raise StopRun('CSV and valid result URL required')
  c.validate(i,a.csv)
  target=c.folder(i)/'result.csv';shutil.copy2(a.csv,target)
  save(c.folder(i)/'download.json',{'sha256':sha(target),'result_url':a.url,'download_url':a.url+'/download/csv','utc':now(),'acquisition':'Chrome native download after normal browser click'})
  c.adopt_download(i);c.merge()
 else:c.set_state(i,phase='rate_limited' if a.reason=='HTTP429' else 'uncertain',error=a.reason)
 c.emit(a.action,**c.status())
finally:c.close()
