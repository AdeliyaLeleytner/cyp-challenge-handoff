#!/usr/bin/env python3
"""ADMETlab textarea batches with exact SMILES checks, resume and CSV merge."""
from pathlib import Path
from urllib.parse import urlsplit, urljoin, parse_qs
from email.utils import parsedate_to_datetime
import argparse, csv, datetime as dt, fcntl, hashlib, io, json, os, sys, time
from parsing import parse_batch, PROVENANCE

ROOT=Path(__file__).resolve().parent
BASE='https://admetlab3.scbdd.com'
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n');tmp.replace(path)
def read(path,default=None):return json.loads(Path(path).read_text()) if Path(path).exists() else default
def retry_time(value):
    if not value:return None
    try:return time.time()+max(0,float(value))
    except ValueError:
        try:return parsedate_to_datetime(value).timestamp()
        except (ValueError,TypeError):return None
class StopRun(RuntimeError):pass

class Collector:
    def __init__(self,input_path,output,batch_size=500,base_url=BASE,schema_path=ROOT/'schema.json'):
        self.input=Path(input_path).resolve();self.root=Path(output).resolve();self.base=base_url.rstrip('/')
        self.schema=json.loads(Path(schema_path).read_text());self.results_dir=self.root/'results'
        if not 1<=batch_size<=1000:raise ValueError('Размер пакета должен быть1–1000.')
        with self.input.open(encoding='utf-8-sig',newline='') as f:raw=list(csv.DictReader(f))
        seen=set();self.rows=[]
        for row in raw:
            smi=row.get('SMILES') or row.get('smiles') or ''
            if not smi:raise ValueError('Входной CSV должен содержать непустой столбец SMILES.')
            if smi!=smi.strip() or any(c.isspace() for c in smi):
                raise ValueError('Пробельные символы внутри/вокруг SMILES: строка отклонена без изменения.')
            if smi in seen:continue
            seen.add(smi);req=hashlib.sha256(smi.encode()).hexdigest()
            if row.get('request_id') and row['request_id']!=req:raise ValueError('Не совпадает request_id/SMILES.')
            self.rows.append({'request_id':req,'SMILES':smi,'priority':str(int(row.get('priority') or 0))})
        if not self.rows:raise ValueError('Пустая очередь молекул.')
        # Exact contiguous lists previously supplied to the user, including their order.
        self.batches=[self.rows[i:i+batch_size] for i in range(0,len(self.rows),batch_size)]
        plan={'input_sha256':sha(self.input),'schema_sha256':sha(schema_path),'batch_size':batch_size,
              'rows':len(self.rows),'source_mode':'web_default','base_url':self.base,'transport':'textarea_method2','batching':'source_order',
              'batches':[[r['request_id'] for r in batch] for batch in self.batches]}
        self.root.mkdir(parents=True,exist_ok=True)
        self.lock=(self.root/'collector.lock').open('a')
        try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close();raise StopRun('С этой папкой уже работает другой процесс. Второй запуск остановлен.')
        if (self.root/'plan.json').exists() and read(self.root/'plan.json')!=plan:
            self.close()
            raise StopRun('Изменились входные данные, схема или размер пакета. Используйте прежние параметры либо другую папку --output.')
        save(self.root/'plan.json',plan)
        for i,batch in enumerate(self.batches):
            folder=self.folder(i);folder.mkdir(parents=True,exist_ok=True)
            path=folder/'smiles.txt'
            content='\n'.join(r['SMILES'] for r in batch)
            if path.exists() and path.read_bytes().decode('utf-8')!=content:
                self.close()
                raise StopRun('Изменён подготовленный список SMILES: '+str(path))
            if not path.exists():
                path.write_bytes(content.encode('utf-8'))
    def close(self):
        if not self.lock.closed:fcntl.flock(self.lock,fcntl.LOCK_UN);self.lock.close()
    def folder(self,i):return self.root/'batches'/f'{i+1:03}'
    def state(self,i):return read(self.folder(i)/'state.json',{'phase':'pending'})
    def set_state(self,i,**changes):
        state=self.state(i);state.update(changes,updated_utc=now());save(self.folder(i)/'state.json',state);return state
    def own(self,url):
        a,b=urlsplit(url),urlsplit(self.base)
        return a.scheme==b.scheme and a.netloc==b.netloc
    def result_url(self,url):return self.own(url) and urlsplit(url).path.startswith('/server/result/')
    def emit(self,event,**fields):
        record={'utc':now(),'event':event,**fields}
        with (self.root/'events.jsonl').open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
        print(json.dumps(record,ensure_ascii=False),flush=True)
    def status(self):
        phases={};completed=0
        for i,batch in enumerate(self.batches):
            phase=self.state(i)['phase'];phases[phase]=phases.get(phase,0)+1
            if phase=='complete':completed+=len(batch)
        return {'molecules':len(self.rows),'completed_molecules':completed,'batches':len(self.batches),'phases':phases,'output':str(self.root)}
    def validate(self,i,path=None):
        folder=self.folder(i);path=path or folder/'result.csv'
        rows,failed,audit=parse_batch(path.read_bytes(),self.batches[i],self.schema,f'browser-batch-{i+1:03}')
        if failed:raise StopRun('Неполный результат пакета '+str(i+1)+': '+json.dumps(failed[:3],ensure_ascii=False))
        if len(rows)!=len(self.batches[i]):raise StopRun('Число строк не совпадает с пакетом.')
        shared=rows[0]['schema']
        for row in rows:row['schema']=shared
        return rows,audit
    def completed(self,i):
        state=self.state(i)
        if state['phase']!='complete':return False
        path=self.folder(i)/'result.csv'
        if not path.exists() or sha(path)!=state['csv_sha256']:raise StopRun('Повреждён ранее сохранённый результат пакета '+str(i+1))
        return True
    def adopt_download(self,i):
        folder=self.folder(i);path=folder/'result.csv';meta=read(folder/'download.json')
        if not path.exists():return False
        if not meta or sha(path)!=meta['sha256']:raise StopRun('Скачанный CSV не совпадает с manifest пакета '+str(i+1))
        rows,audit=self.validate(i);save(folder/'identity-audit.json',audit)
        self.set_state(i,phase='complete',rows=len(rows),csv_sha256=sha(path),result_url=meta['result_url'])
        return True
    def screenshot(self,page,i,label):
        try:
            page.screenshot(path=str(self.folder(i)/(label+'.png')),timeout=5000)
            save(self.folder(i)/(label+'.json'),{'url':page.url,'title':page.title(),'text':page.locator('body').inner_text(timeout=3000)[:12000]})
        except Exception:pass
    def check_response(self,response,page,i,stage):
        if response is None:raise StopRun('Нет ответа на этапе '+stage)
        status=response.status
        if status==429:
            retry=response.headers.get('retry-after');not_before=retry_time(retry)
            self.set_state(i,phase='rate_limited',http_status=429,retry_after=retry,retry_not_before=not_before,stage=stage)
            raise StopRun('HTTP429. Отправки остановлены; прогресс сохранён. '+('Retry-After: '+retry if retry else 'Сайт не указал срок ожидания.'))
        if status>=400:
            self.set_state(i,phase='service_error',http_status=status,stage=stage)
            raise StopRun('Сервис ответил HTTP'+str(status)+' на этапе '+stage)
        if not self.own(page.url):raise StopRun('Браузер перешёл на другой сайт. Требуется проверка.')
    def recover_url(self,value):
        batch,url=value.split('=',1);i=int(batch)-1
        if not 0<=i<len(self.batches) or not self.result_url(url):raise ValueError('Нужен номер пакета и его URL вида /server/result/...')
        if self.completed(i):raise StopRun('Этот пакет уже готов.')
        self.set_state(i,phase='result_ready',result_url=url,recovered_by_user=True)
    def payload(self,i):
        expected='\n'.join(r['SMILES'] for r in self.batches[i])
        if (self.folder(i)/'smiles.txt').read_bytes()!=expected.encode('utf-8'):
            raise StopRun('Подготовленный текст отличается от исходных SMILES.')
        return expected
    def fill_text_form(self,page,i):
        tab=page.get_by_role('tab',name='Enter a list of SMILES',exact=True)
        if tab.count()!=1:raise StopRun('Не найдена вкладка Enter a list of SMILES.')
        tab.click()
        form=page.locator('form#form2')
        if form.count()!=1 or form.get_attribute('action')!='/server/screeningCal' or form.get_attribute('method').lower()!='post':
            raise StopRun('Изменилась текстовая форма сайта. Данные не отправлены.')
        if form.locator('input[name="method"]').input_value()!='2':raise StopRun('Неверный режим текстовой формы.')
        field=form.locator('textarea[name="smiles-list"]')
        expected=self.payload(i)
        field.fill(expected)
        actual=field.input_value()
        if actual!=expected or actual.split('\n')!=[r['SMILES'] for r in self.batches[i]]:
            self.set_state(i,phase='integrity_error')
            raise StopRun('Текст в браузере отличается от исходных SMILES. Submit не нажат.')
        save(self.folder(i)/'textarea-integrity.json',{'utc':now(),'rows':len(self.batches[i]),
             'source_utf8_sha256':hashlib.sha256(expected.encode()).hexdigest(),
             'textarea_utf8_sha256':hashlib.sha256(actual.encode()).hexdigest(),
             'exact_character_and_order_match':True,'line_separator':'LF','molecules_rewritten':False})
        return form
    def verify_form_request(self,post_data,content_type,i):
        if not content_type.lower().startswith('application/x-www-form-urlencoded'):
            raise StopRun('Неожиданный формат отправки текстовой формы.')
        fields=parse_qs(post_data or '',keep_blank_values=True,encoding='utf-8',errors='strict',max_num_fields=16)
        if fields.get('method')!=['2'] or len(fields.get('smiles-list',[]))!=1:
            raise StopRun('Поля запроса не соответствуют текстовому режиму.')
        # HTML forms serialize textarea line endings as CRLF. No molecular characters are normalized.
        decoded=fields['smiles-list'][0].replace('\r\n','\n')
        expected=self.payload(i)
        if decoded!=expected:raise StopRun('SMILES изменились при формировании запроса; запрос заблокирован до отправки.')
        return {'utc':now(),'rows':len(self.batches[i]),'utf8_sha256':hashlib.sha256(decoded.encode()).hexdigest(),
                'exact_molecule_strings_and_order_match':True,'transport_newlines':'CRLF normalized to LF only'}
    def process(self,page,i,timeout,retry_rejected=False):
        folder=self.folder(i)
        if self.completed(i) or self.adopt_download(i):return
        state=self.state(i);phase=state['phase'];saved_url=state.get('result_url')
        if phase in ('submitting','uncertain') and not saved_url:
            raise StopRun(f'Пакет {i+1} отправлялся, но исход неизвестен. Повторный POST не отправлен. Если результат есть в браузере, укажите --result-url "{i+1}=URL".')
        if phase=='invalid_result':raise StopRun(f'CSV пакета {i+1} не прошёл проверку. См. журнал; остальные результаты сохранены.')
        if phase in ('rate_limited','service_error'):
            if not retry_rejected:raise StopRun(f'Пакет {i+1} ранее отклонён сервисом. После восстановления доступа запустите с --retry-rejected.')
            if state.get('retry_not_before') and time.time()<state['retry_not_before']:
                raise StopRun('Срок Retry-After ещё не истёк: '+dt.datetime.fromtimestamp(state['retry_not_before']).astimezone().isoformat())
            if state.get('stage')=='submit' and state.get('http_status',429)!=429:
                raise StopRun('После ошибки отправки исход может быть неопределённым. Нужен URL результата; автоматический повтор запрещён.')
        if saved_url:
            if not self.result_url(saved_url):raise StopRun('Неверный сохранённый URL результата.')
            response=page.goto(saved_url,wait_until='domcontentloaded',timeout=timeout)
            self.check_response(response,page,i,'existing_result')
        else:
            self.emit('opening_screening',batch=i+1,total_batches=len(self.batches))
            response=page.goto(self.base+'/server/screening',wait_until='domcontentloaded',timeout=60000)
            self.check_response(response,page,i,'screening')
            form=self.fill_text_form(page,i)
            attempt=int(state.get('attempt',0))+1
            self.set_state(i,phase='submitting',attempt=attempt,retry_not_before=None,stage='submit')
            save(folder/f'attempt-{attempt:03}.json',{'utc':now(),'smiles_text_sha256':sha(folder/'smiles.txt'),'rows':len(self.batches[i]),'transport':'textarea_method2'})
            self.emit('submit',batch=i+1,rows=len(self.batches[i]))
            rejected=[]
            def check_before_send(route):
                request=route.request
                if request.method!='POST':route.continue_();return
                try:
                    audit=self.verify_form_request(request.post_data,request.headers.get('content-type',''),i)
                    save(folder/'request-integrity.json',audit)
                except Exception as exc:
                    rejected.append(str(exc));route.abort('blockedbyclient');return
                route.continue_()
            submit_url=self.base+'/server/screeningCal';page.route(submit_url,check_before_send)
            try:
                with page.expect_navigation(wait_until='domcontentloaded',timeout=timeout) as navigation:
                    form.get_by_role('button',name='Submit',exact=True).click(no_wait_after=True)
                response=navigation.value
            except BaseException:
                self.set_state(i,phase='integrity_error' if rejected else 'uncertain',result_url=page.url if self.result_url(page.url) else None)
                if rejected:raise StopRun(rejected[0])
                self.screenshot(page,i,'uncertain');raise
            finally:page.unroute(submit_url,check_before_send)
            self.screenshot(page,i,'response')
            self.check_response(response,page,i,'submit')
        if not self.result_url(page.url):
            self.set_state(i,phase='uncertain');raise StopRun('Не обнаружена страница результата; автоматический повтор не выполняется.')
        self.set_state(i,phase='result_ready',result_url=page.url)
        links=page.locator('a[href*="/download/csv"]')
        hrefs={urljoin(page.url,x) for x in links.evaluate_all('(xs)=>xs.map(x=>x.getAttribute("href"))')}
        if len(hrefs)!=1 or not all(self.result_url(u) for u in hrefs):raise StopRun('Не найдена однозначная ссылка на CSV этого результата.')
        result_url=page.url;download_url=next(iter(hrefs))
        responses=[]
        def observed(response):
            if response.url==download_url:responses.append(response)
        page.on('response',observed)
        try:
            with page.expect_download(timeout=120000) as pending:links.first.click(no_wait_after=True)
            download=pending.value
        except Exception:
            if responses:self.check_response(responses[-1],page,i,'download')
            raise
        finally:page.remove_listener('response',observed)
        failure=download.failure()
        if failure:raise StopRun('Ошибка скачивания: '+failure+'. URL результата сохранён.')
        partial=folder/'result.csv.partial';download.save_as(str(partial))
        save(folder/'download.json',{'sha256':sha(partial),'result_url':result_url,'download_url':download_url,'utc':now()})
        partial.replace(folder/'result.csv')
        try:self.adopt_download(i)
        except Exception:
            self.set_state(i,phase='invalid_result');raise
        self.emit('batch_complete',batch=i+1,**self.status())
    def merge(self):
        complete=[i for i in range(len(self.batches)) if self.completed(i)]
        if not complete:return None
        raw_columns=[];features=set();schema={}
        for i in complete:
            with (self.folder(i)/'result.csv').open(encoding='utf-8-sig',newline='') as f:cols=next(csv.reader(f))
            for col in cols:
                if col not in raw_columns:raw_columns.append(col)
            rows,_=self.validate(i)
            for row in rows:
                features.update(row['features'])
                for item in row['schema']:schema[(item['category'],item['name'])]=item
        self.results_dir.mkdir(exist_ok=True)
        columns=sorted(features);names=['request_id','SMILES','priority','service_smiles','taskid']
        known=set();count=0
        raw_tmp=self.results_dir/'admetlab_merged.csv.tmp';feature_tmp=self.results_dir/'features.csv.tmp'
        with raw_tmp.open('w',newline='') as rf,feature_tmp.open('w',newline='') as ff:
            rw=csv.DictWriter(rf,fieldnames=['request_id','Molecule_SMILES']+raw_columns);rw.writeheader()
            fw=csv.DictWriter(ff,fieldnames=names+columns);fw.writeheader()
            for i in complete:
                rows,_=self.validate(i);by_smiles={r['SMILES']:r for r in rows}
                with (self.folder(i)/'result.csv').open(encoding='utf-8-sig',newline='') as f:
                    for raw in csv.DictReader(f):
                        row=by_smiles[raw['raw_smiles']];req=row['request_id']
                        if req in known:raise StopRun('Повтор молекулы при объединении.')
                        known.add(req);count+=1
                        rw.writerow({'request_id':req,'Molecule_SMILES':row['SMILES'],**raw})
                        fw.writerow({**{k:row[k] for k in names},**{k:row['features'].get(k,0 if '::category=' in k else None) for k in columns}})
        raw_tmp.replace(self.results_dir/'admetlab_merged.csv');feature_tmp.replace(self.results_dir/'features.csv')
        with (self.results_dir/'missing-or-pending.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['request_id','SMILES','priority']);w.writeheader();w.writerows(r for r in self.rows if r['request_id'] not in known)
        report={'status':'complete' if count==len(self.rows) else 'partial','queue_size':len(self.rows),'successes':count,'remaining':len(self.rows)-count,
                'queue_sha256':sha(self.input),'updated_utc':now(),'acquisition_method':'browser_smiles_textarea','rows':count,**PROVENANCE}
        save(self.results_dir/'status.json',report)
        save(self.results_dir/'feature-schema.json',{'feature_columns':columns,'endpoint_schema':list(schema.values()),
             'schema_note':'All returned web-default endpoints retained; molecular matching by exact raw_smiles, rule lists represented by counts and preserved verbatim in raw CSV.',**PROVENANCE})
        if self.input==ROOT/'data/molecules.csv':save(self.results_dir/'id-map-provenance.json',{'path':str(ROOT/'data/id-map.csv'),'sha256':sha(ROOT/'data/id-map.csv')})
        if report['status']=='complete':save(self.results_dir/'complete.json',{**report,'features_sha256':sha(self.results_dir/'features.csv'),'no_endpoint_filtering':True})
        self.emit('merged',**report,path=str(self.results_dir/'admetlab_merged.csv'))
        return report

def main():
    parser=argparse.ArgumentParser(description='ADMETlab: вставка списков SMILES в Chrome, скачивание CSV и объединение.')
    parser.add_argument('--input',type=Path,default=ROOT/'data/molecules.csv')
    parser.add_argument('--output',type=Path,default=Path.home()/'Downloads/ADMETlab-results-500')
    parser.add_argument('--profile-dir',type=Path,default=ROOT/'output/chrome-profile',help='Рабочий профиль Chrome; позволяет сохранить одну сессию для отдельных сравнительных запусков.')
    parser.add_argument('--batch-size',type=int,default=500)
    parser.add_argument('--browser-mode',choices=['current-chrome','playwright'],default='current-chrome' if sys.platform=='darwin' else 'playwright',help='На Mac по умолчанию используется обычная сессия Google Chrome.')
    parser.add_argument('--delay',type=float,default=10,help='Пауза между успешными пакетами, секунд (минимум2).')
    parser.add_argument('--timeout',type=int,default=900,help='Ожидание расчёта одного пакета, секунд.')
    parser.add_argument('--prepare-only',action='store_true');parser.add_argument('--status',action='store_true');parser.add_argument('--merge-only',action='store_true')
    parser.add_argument('--retry-rejected',action='store_true',help='Одна новая попытка после восстановления доступа; соблюдает Retry-After.')
    parser.add_argument('--result-url',action='append',default=[],metavar='BATCH=URL',help='Продолжить скачивание уже рассчитанного пакета без повторной отправки.')
    args=parser.parse_args()
    if args.delay<2 or args.timeout<30:parser.error('Минимум --delay2 и --timeout30.')
    if args.status:
        root=args.output.resolve();plan=read(root/'plan.json')
        if not plan:print('Запуск ещё не подготовлен.');return 0
        phases={};done=0
        for i,ids in enumerate(plan['batches']):
            phase=read(root/'batches'/f'{i+1:03}'/'state.json',{'phase':'pending'})['phase']
            phases[phase]=phases.get(phase,0)+1
            if phase=='complete':done+=len(ids)
        print(json.dumps({'molecules':plan['rows'],'completed_molecules':done,'batches':len(plan['batches']),'phases':phases,'output':str(root)},ensure_ascii=False,indent=2))
        return 0
    collector=None;exit_code=0
    try:
        collector=Collector(args.input,args.output,args.batch_size)
        for value in args.result_url:collector.recover_url(value)
        print(json.dumps(collector.status(),ensure_ascii=False,indent=2),flush=True)
        if args.prepare_only or args.status:return 0
        if args.merge_only:collector.merge();return 0
        pending=[i for i in range(len(collector.batches)) if not collector.completed(i)]
        if not pending:print('Все пакеты уже готовы.');return 0
        if args.browser_mode=='current-chrome':
            if sys.platform!='darwin':raise StopRun('current-chrome требует macOS; используйте --browser-mode playwright.')
            from current_chrome import CurrentChrome,process
            chrome=CurrentChrome(collector.base)
            save(collector.root/'chrome-session.json',{'window_id':chrome.window_id,'tab_id':chrome.tab_id,'mode':'ordinary_user_Chrome','utc':now()})
            for i in pending:
                process(collector,chrome,i,args.timeout,args.retry_rejected)
                time.sleep(args.delay)
        else:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                profile=(args.profile_dir or collector.root/'chrome-profile').resolve()
                context=p.chromium.launch_persistent_context(str(profile),channel='chrome',headless=False,
                    accept_downloads=True,viewport={'width':1280,'height':900})
                page=context.pages[0] if context.pages else context.new_page();page.set_default_timeout(20000);current=None
                try:
                    for i in pending:
                        current=i
                        collector.process(page,i,args.timeout*1000,args.retry_rejected)
                        time.sleep(args.delay)
                finally:
                    # Preserve a returned result URL even if the user interrupts after submission.
                    if current is not None and collector.result_url(page.url) and collector.state(current)['phase'] in ('submitting','uncertain'):
                        collector.set_state(current,phase='result_ready',result_url=page.url)
                    context.close()
    except KeyboardInterrupt:
        print('\nОстановлено. Прогресс сохранён.');exit_code=130
    except Exception as exc:
        print('\nОСТАНОВЛЕНО: '+str(exc),file=sys.stderr,flush=True);exit_code=2
        if collector:collector.emit('stopped',error=str(exc),**collector.status())
    finally:
        if collector:
            try:
                if not (args.prepare_only or args.status or args.merge_only):collector.merge()
            except Exception as exc:print('Объединение остановлено: '+str(exc),file=sys.stderr);exit_code=2
            collector.close()
    return exit_code
if __name__=='__main__':sys.exit(main())
