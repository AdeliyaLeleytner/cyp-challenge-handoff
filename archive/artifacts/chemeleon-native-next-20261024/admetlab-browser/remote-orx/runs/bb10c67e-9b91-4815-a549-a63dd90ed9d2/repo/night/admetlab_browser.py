"""Autonomous ordinary-browser CSV upload/download. No stealth, proxy or CAPTCHA bypass."""
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from types import SimpleNamespace
import csv,json,time,hashlib,fcntl,sys,re
from playwright.sync_api import sync_playwright
from .admetlab_web import parse_batch,export,PROVENANCE
from .admetlab_features import save,sha,atomic_bytes,now

BASE='https://admetlab3.scbdd.com'
def own_url(url):
    p=urlsplit(url)
    return p.scheme=='https' and p.netloc=='admetlab3.scbdd.com'

def snapshot(page,directory,label):
    directory.mkdir(parents=True,exist_ok=True)
    try:
        text=page.locator('body').inner_text(timeout=3000)
        save(directory/(label+'.json'),{'url':page.url,'title':page.title(),'text':text[:12000],'utc':now()})
        page.screenshot(path=str(directory/(label+'.png')),timeout=10000)
    except Exception as e:save(directory/(label+'-capture-error.json'),{'error':str(e)})

def run(cfg):
    root=Path(cfg['output_dir']);root.mkdir(parents=True,exist_ok=True)
    lock=(root/'dispatch.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert sha(cfg['queue_path'])==cfg['queue_sha256'] and sha(cfg['id_map_path'])==cfg['id_map_sha256']
    with Path(cfg['queue_path']).open() as f:rows=list(csv.DictReader(f))
    assert len({r['request_id'] for r in rows})==len(rows)==len({r['SMILES'] for r in rows})
    cfg={**cfg,'source_mode':'web_default','backend':'documented_web_batch','api_probe_vectors_used':False}
    save(root/'config.json',cfg);save(root/'id-map-provenance.json',{'path':cfg['id_map_path'],'sha256':cfg['id_map_sha256']})
    batches=[]
    for priority in sorted({r['priority'] for r in rows},key=int):
        group=[r for r in rows if r['priority']==priority]
        if not batches:batches.append(group[:100]);group=group[100:]
        batches.extend(group[i:i+1000] for i in range(0,len(group),1000))
    results={};errors=[];started=time.monotonic();client=SimpleNamespace(requests=0,reason=None);status='running'
    page=None;directory=root
    try:
        with sync_playwright() as playwright:
            # Headed browser on the leased machine's virtual display; unchanged browser UA.
            context=playwright.chromium.launch_persistent_context(str(root/'browser-profile'),headless=False,
                accept_downloads=True,viewport={'width':1280,'height':900})
            page=context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(20000)
            save(root/'browser-version.json',{'version':context.browser.version if context.browser else 'persistent Chromium',
                'headless':False,'proxy_configured':False,'automation':'Playwright1.64.1','workflow':'visible file input, Submit button, result CSV link',**PROVENANCE})
            for index,batch in enumerate(batches):
                if time.monotonic()-started>cfg['maximum_runtime_seconds']:raise RuntimeError('Bounded runtime reached')
                directory=root/'batches'/f'{index:04}';directory.mkdir(parents=True,exist_ok=True)
                csv_path=directory/'result.csv';metadata=directory/'download.json'
                if csv_path.exists() and metadata.exists():
                    meta=json.loads(metadata.read_text());assert sha(csv_path)==meta['sha256']
                    assert json.loads((directory/'inputs.json').read_text())==batch
                else:
                    save(directory/'inputs.json',batch)
                    upload=directory/'upload.csv'
                    with upload.open('w',newline='') as f:
                        writer=csv.writer(f);writer.writerow(['SMILES']);writer.writerows([r['SMILES']] for r in batch)
                    if (directory/'post-attempt.json').exists():
                        if not (directory/'result-page.json').exists():raise RuntimeError('Previous submission outcome uncertain; no duplicate POST will be sent')
                        result_url=json.loads((directory/'result-page.json').read_text())['url']
                        assert own_url(result_url)
                        response=page.goto(result_url,wait_until='domcontentloaded',timeout=60000)
                    else:
                        response=page.goto(BASE+'/server/screening',wait_until='domcontentloaded',timeout=60000)
                        client.requests+=1;snapshot(page,directory,'form')
                        if response is None or response.status!=200:raise RuntimeError('Screening page HTTP '+str(response.status if response else None))
                        if not own_url(page.url):raise RuntimeError('Unexpected browser origin')
                        form=page.locator('form#form1')
                        if form.count()!=1 or form.get_attribute('action')!='/server/screeningCal' or form.get_attribute('method').lower()!='post':raise RuntimeError('Observed file-upload form contract changed')
                        if form.locator('input[name="method"]').input_value()!='1' or form.locator('input[name="is_example"]').input_value()!='0':raise RuntimeError('Unexpected upload mode')
                        form.locator('input[type="file"][name="uploadfile"]').set_input_files(str(upload))
                        save(directory/'post-attempt.json',{'utc':now(),'rows':len(batch),'upload_sha256':sha(upload),'url':page.url,'method':'browser_file_upload','no_automatic_post_retry':True})
                        print(json.dumps({'event':'browser_batch_submit','batch':index,'rows':len(batch),'completed':len(results)}),flush=True)
                        with page.expect_navigation(wait_until='domcontentloaded',timeout=600000) as navigation:
                            form.get_by_role('button',name='Submit',exact=True).click(no_wait_after=True)
                        response=navigation.value;client.requests+=1
                    snapshot(page,directory,'result')
                    if response is None or response.status!=200:
                        save(directory/'http-error.json',{'status':response.status if response else None,'url':page.url,
                            'retry_after':response.headers.get('retry-after') if response else None,'utc':now()})
                        raise RuntimeError('Result page HTTP '+str(response.status if response else None)+'; no endpoint/IP switching or automatic retry')
                    if not own_url(page.url) or '/server/result/' not in page.url:raise RuntimeError('No official result page; inspect saved browser evidence')
                    save(directory/'result-page.json',{'url':page.url,'utc':now()})
                    links=page.locator('a[href*="/download/csv"]')
                    if links.count()!=1:raise RuntimeError('Expected one observed result CSV download link')
                    url=urljoin(page.url,links.first.get_attribute('href'));assert own_url(url)
                    with page.expect_download(timeout=120000) as waiting:links.first.click(no_wait_after=True)
                    download=waiting.value
                    if download.failure():raise RuntimeError('CSV download failed: '+str(download.failure()))
                    temporary=csv_path.with_suffix('.partial');download.save_as(str(temporary));temporary.replace(csv_path);client.requests+=1
                    meta={'url':url,'result_url':page.url,'sha256':sha(csv_path),'utc':now(),'suggested_filename':download.suggested_filename,**PROVENANCE}
                    save(metadata,meta)
                success,failed,audit=parse_batch(csv_path.read_bytes(),batch,cfg,meta['result_url'].rstrip('/').split('/')[-1])
                save(directory/'identity-audit.json',audit)
                if failed:save(directory/'failed-rows.json',failed);raise RuntimeError('Missing/invalid returned molecules; no silent row dropping')
                shared_schema=success[0]['schema']
                for r in success:r['schema']=shared_schema;results[r['request_id']]=r
                report=export(root,rows,results,errors,cfg,client,started,'running')
                save(directory/'complete.json',{'rows':len(success),'csv_sha256':sha(csv_path),'utc':now()})
                print(json.dumps({'event':'browser_batch_complete','batch':index,'completed':len(results),'total':len(rows),'seconds':round(time.monotonic()-started,1)}),flush=True)
                time.sleep(2)
            status='complete'
            context.close()
    except Exception as exc:
        status='blocked_or_failed';client.reason=str(exc);errors.append({'error':str(exc),'utc':now()})
        print(json.dumps({'event':'browser_acquisition_stopped','reason':str(exc),'completed':len(results)}),flush=True)
    finally:
        report=export(root,rows,results,errors,cfg,client,started,status)
        report['acquisition_method']='browser_csv_file_upload';save(root/'run-summary.json',report)
        if status=='complete':save(root/'complete.json',{'status':'complete','rows':len(rows),'queue_sha256':cfg['queue_sha256'],'features_sha256':sha(root/'features.csv'),'no_endpoint_filtering':True,**PROVENANCE})
        fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
    return status

if __name__=='__main__':
    cfg=json.loads(Path('admetlab_web_config.json').read_text())
    sys.exit(0 if run(cfg)=='complete' else 2)
