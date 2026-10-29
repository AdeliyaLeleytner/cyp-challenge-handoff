#!/usr/bin/env python3
"""Same ADMETlab web form via curl bound to Wi-Fi; no global VPN changes."""
import argparse, hashlib, subprocess, time, sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin
from collect import Collector, StopRun, save, sha, now, retry_time

class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.form=None; self.active=False; self.fields={}; self.links=[]
        self.feed(html)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='form':
            self.active=a.get('id')=='form2'
            if self.active:self.form=a
        if tag=='input' and self.active and a.get('name'):
            self.fields[a['name']]=a.get('value','')
        if tag=='a' and a.get('href'):self.links.append(a['href'])
    def handle_endtag(self,tag):
        if tag=='form':self.active=False

class Direct:
    def __init__(self,c,interface='en0',timeout=900):
        self.c=c; self.interface=interface; self.timeout=timeout; self.counter=0
        self.cookie=c.root/'cookies.txt'; self.cookie.touch(mode=0o600,exist_ok=True)
        self.cookie.chmod(0o600)
    def transport_args(self):return ['--interface',self.interface,'--noproxy','*']
    def curl_stdin(self):return None
    def request(self,i,url,payload=None):
        c=self.c
        if not c.own(url):raise StopRun('Cross-origin URL refused: '+url)
        self.counter+=1; stem=c.folder(i)/f'http-{time.time_ns()}-{self.counter}'
        body=stem.with_suffix('.body'); headers=stem.with_suffix('.headers')
        cmd=['/usr/bin/curl',*self.transport_args(),'--silent','--show-error',
             '--connect-timeout','20','--max-time',str(self.timeout),'--proto','=https' if url.startswith('https:') else '=http',
             '--cookie',str(self.cookie),'--cookie-jar',str(self.cookie),'--dump-header',str(headers),
             '--output',str(body),'--write-out','%{http_code}\t%{local_ip}\t%{remote_ip}\t%{http_connect}\t%{time_appconnect}\t%{size_upload}\t%{time_total}\t%{http_version}',
             '--referer',c.base+'/server/screening']
        if payload is not None:
            payload_path=stem.with_suffix('.form');payload_path.write_bytes(payload.encode('ascii'))
            payload_path.chmod(0o600)
            cmd+=['--header','Content-Type: application/x-www-form-urlencoded','--data-binary','@'+str(payload_path)]
        p=subprocess.run(cmd+[url],input=self.curl_stdin(),capture_output=True,text=True)
        parts=p.stdout.strip().split('\t');status=int(parts[0] or 0) if parts else 0
        meta={'utc':now(),'url':url,'method':'POST' if payload is not None else 'GET','interface':self.interface,
              'http_status':status,'curl_exit':p.returncode,'local_ip':parts[1] if len(parts)>1 else None,
              'remote_ip':parts[2] if len(parts)>2 else None,'error':p.stderr,
              'proxy_connect_status':parts[3] if len(parts)>3 else None,
              'tls_handshake_seconds':parts[4] if len(parts)>4 else None,
              'uploaded_bytes':parts[5] if len(parts)>5 else None,
              'total_seconds':parts[6] if len(parts)>6 else None,
              'http_version':parts[7] if len(parts)>7 else None}
        save(stem.with_suffix('.json'),meta)
        hs={}
        if headers.exists():
            for line in headers.read_text().splitlines():
                if ':' in line:
                    k,v=line.split(':',1);hs[k.lower()]=v.strip()
        if status==429:
            c.set_state(i,phase='rate_limited',http_status=429,retry_after=hs.get('retry-after'),
                        retry_not_before=retry_time(hs.get('retry-after')))
            raise StopRun('HTTP429: остановлено; срок Retry-After сохранён. Автоповторов нет.')
        if p.returncode:
            if payload is not None and status==0 and ((p.returncode==56 and 'CONNECT tunnel failed, response' in p.stderr) or (p.returncode==28 and 'SSL connection timeout' in p.stderr)):
                c.set_state(i,phase='pending',not_submitted=True,error_stage='pre_origin_connect_or_tls',error=p.stderr.strip())
            raise StopRun('Ошибка прямого соединения: '+p.stderr.strip())
        if status>=400:raise StopRun('HTTP'+str(status)+'; повторная отправка запрещена до проверки.')
        return status,hs,body
    def follow(self,i,url,response=None):
        for _ in range(6):
            status,headers,body=response or self.request(i,url);response=None
            if status in (301,302,303):
                if not headers.get('location'):raise StopRun('Redirect без Location')
                url=urljoin(url,headers['location'])
                if not self.c.own(url):raise StopRun('Redirect на другой origin')
                if self.c.result_url(url):self.c.set_state(i,phase='result_ready',result_url=url)
                continue
            if status!=200:raise StopRun('Неожиданный HTTP'+str(status))
            return url,body
        raise StopRun('Слишком много перенаправлений')
    def process(self,i):
        c=self.c
        if c.completed(i) or c.adopt_download(i):return
        state=c.state(i);url=state.get('result_url')
        if state['phase']=='rate_limited':raise StopRun('Сохранён HTTP429: автоматического повтора нет.')
        if state['phase']=='invalid_result':raise StopRun('Результат требует проверки.')
        if not url:
            if state['phase']!='pending':raise StopRun('Исход предыдущей отправки неизвестен; повторный POST запрещён.')
            start=c.base+'/server/screening';_,body=self.follow(i,start)
            page=Page(body.read_text())
            if not page.form or page.form.get('method','').lower()!='post' or page.form.get('action')!='/server/screeningCal' or page.fields.get('method')!='2':
                raise StopRun('Изменилась форма ADMETlab; отправка отменена.')
            fields=dict(page.fields);fields['smiles-list']=c.payload(i)
            payload=urlencode(fields)
            audit=c.verify_form_request(payload,'application/x-www-form-urlencoded',i)
            save(c.folder(i)/'request-integrity.json',audit)
            c.set_state(i,phase='submitting',transport='curl_interface_'+self.interface)
            c.emit('submit_direct',batch=i+1,rows=len(c.batches[i]),interface=self.interface)
            target=urljoin(start,page.form['action'])
            url,body=self.follow(i,target,self.request(i,target,payload))
        else:url,body=self.follow(i,url)
        links={urljoin(url,x) for x in Page(body.read_text()).links if '/download/csv' in x}
        if len(links)!=1:raise StopRun('CSV-ссылка ещё не найдена; HTML сохранён. Новый POST не отправляется.')
        download=next(iter(links))
        if not c.result_url(url):raise StopRun('Неожиданный URL результата: '+url)
        c.set_state(i,phase='result_ready',result_url=url)
        _,csvbody=self.follow(i,download)
        partial=c.folder(i)/'result.csv.partial';partial.write_bytes(csvbody.read_bytes())
        try:c.validate(i,partial)
        except Exception:
            c.set_state(i,phase='invalid_result');raise
        save(c.folder(i)/'download.json',{'sha256':sha(partial),'result_url':url,'download_url':download,'utc':now()})
        partial.replace(c.folder(i)/'result.csv');c.adopt_download(i)
        c.emit('batch_complete_direct',batch=i+1,rows=len(c.batches[i]))
        c.merge()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--max-batches',type=int,default=11);ap.add_argument('--delay',type=float,default=20)
    ap.add_argument('--status',action='store_true')
    args=ap.parse_args()
    if args.max_batches<1 or args.delay<2:ap.error('max-batches>=1, delay>=2')
    c=Collector(args.input,args.output,500)
    try:
        c.emit('status',**c.status())
        if args.status:return 0
        d=Direct(c)
        pending=[i for i in range(len(c.batches)) if not c.completed(i)][:args.max_batches]
        for n,i in enumerate(pending):
            d.process(i)
            if n+1<len(pending):time.sleep(args.delay)
        c.emit('finished',**c.status());return 0
    except (Exception,KeyboardInterrupt) as e:
        c.emit('stopped',error=str(e),**c.status());return 2
    finally:c.close()
if __name__=='__main__':sys.exit(main())
