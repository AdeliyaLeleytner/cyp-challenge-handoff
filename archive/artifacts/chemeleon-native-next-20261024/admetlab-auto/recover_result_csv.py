"""Retrieve an accepted task's known CSV endpoint directly; never submit molecules."""
import sys,json
from pathlib import Path
from collect import Collector,save,sha,now,StopRun
from direct_http import Direct
from scheduled_queue import ROOT,INPUT,merge_all
folder=Path(sys.argv[1]).resolve()
if not folder.is_relative_to(ROOT/'probes'):raise StopRun('Expected a saved probe folder')
main=Collector(INPUT,ROOT,500);pc=Collector(folder/'input.csv',folder/'run',500)
try:
 if not pc.completed(0):
  result=pc.state(0).get('result_url')
  if not result or not pc.result_url(result):raise StopRun('No accepted result URL; no new POST allowed')
  url=result.rstrip('/')+'/download/csv'
  status,headers,body=Direct(pc,timeout=60).request(0,url)
  if status!=200:raise StopRun('Result CSV returned HTTP'+str(status))
  rows,_=pc.validate(0,body)
  dest=pc.folder(0)/'result.csv';dest.write_bytes(body.read_bytes())
  save(pc.folder(0)/'download.json',{'utc':now(),'sha256':sha(dest),'result_url':result,'download_url':url,'acquisition':'Direct Wi-Fi download of accepted Shifter prediction; no new POST','rows':len(rows)})
  pc.adopt_download(0)
finally:pc.close()
try:print(json.dumps(merge_all(main),indent=2))
finally:main.close()
