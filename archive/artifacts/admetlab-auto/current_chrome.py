"""Automate one owned tab in the user's ordinary macOS Google Chrome session."""
import json,subprocess,time,uuid,hashlib
from urllib.parse import urlsplit,urljoin
from collect import StopRun,save,now,retry_time,sha

def quoted(value):
    return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('\r','\\r').replace('\n','\\n')+'"'

class CurrentChrome:
    def __init__(self,base_url):
        self.base=base_url.rstrip('/')
        result=self.applescript('''tell application "Google Chrome"
set chosenId to missing value
repeat with candidateWindow in windows
 repeat with candidateTab in tabs of candidateWindow
  if URL of candidateTab starts with "https://admetlab3.scbdd.com/" then
   try
    execute candidateTab javascript "JSON.stringify(true)"
    set chosenId to id of candidateWindow
    exit repeat
   end try
  end if
 end repeat
 if chosenId is not missing value then exit repeat
end repeat
if chosenId is missing value then
 if (count of windows) is 0 then make new window
 set chosenId to id of front window
 execute active tab of (first window whose id is chosenId) javascript "JSON.stringify(true)"
end if
set targetWindow to first window whose id is chosenId
set ownedTab to make new tab at end of tabs of targetWindow with properties {URL:"about:blank"}
return (chosenId as text) & "," & (id of ownedTab as text)
end tell''')
        self.window_id,self.tab_id=map(int,result.split(','))
    def applescript(self,source):
        result=subprocess.run(['osascript','-'],input=source,capture_output=True,text=True,timeout=30)
        if result.returncode:raise StopRun('Chrome: '+result.stderr.strip())
        return result.stdout.strip()
    def command(self,action):
        return self.applescript(f'''tell application "Google Chrome"
set w to first window whose id is {self.window_id}
set t to first tab of w whose id is {self.tab_id}
{action}
end tell''')
    def evaluate(self,expression):
        wrapped='JSON.stringify((()=>{try{return {ok:true,value:('+expression+')}}catch(e){return {ok:false,error:String(e)}}})())'
        value=self.command('execute t javascript '+quoted(wrapped))
        try:result=json.loads(value)
        except ValueError:raise StopRun('Chrome не вернул ожидаемый ответ скрипту: '+value[:200])
        if not result.get('ok'):raise StopRun('Chrome JavaScript: '+result.get('error','unknown error'))
        return result.get('value')
    def view(self):
        origin=urlsplit(self.base);allowed=origin.scheme+'://'+origin.netloc
        return self.evaluate('''(()=>{const u=location.href;const allowed=location.origin==='''+json.dumps(allowed)+''';
return {url:u,title:document.title,ready:document.readyState,
status:performance.getEntriesByType('navigation')[0]?.responseStatus||0,
text:(allowed||u.startsWith('chrome-error:'))&&document.body?document.body.innerText.slice(0,3000):''};})()''')
    def goto(self,url,timeout=60):
        if not url.startswith(self.base+'/'):raise StopRun('Неожиданный адрес навигации.')
        self.command('set URL of t to '+quoted(url))
        return self.wait(timeout,after_submit=False,expected=url)
    def wait(self,timeout,after_submit=False,expected=None):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            loading=self.command('return loading of t')=='true'
            state=self.view();url=state['url']
            if url.startswith('chrome-error:'):raise StopRun('Chrome не открыл сайт: '+state['text'][:700])
            if not loading and state['ready'] in ('interactive','complete'):
                if after_submit:
                    if '/server/result/' in url or '/server/screeningCal' in url:return state
                elif url==expected or '/server/result/' in url:return state
            time.sleep(1)
        raise StopRun('Превышено время ожидания страницы. Повторный Submit не выполнен.')
    def fill(self,text):
        payload=json.dumps(text,ensure_ascii=True)
        return self.evaluate('''(()=>{
if(location.origin!=='''+json.dumps(self.base)+''')throw Error('Unexpected origin');
const tab=document.querySelector('#profile-tab');if(!tab)throw Error('SMILES tab missing');tab.click();
const f=document.querySelector('form#form2');
if(!f||f.getAttribute('action')!='/server/screeningCal'||f.getAttribute('method').toLowerCase()!=='post'||f.elements.method.value!=='2')throw Error('Text form contract changed');
const t=f.querySelector('textarea[name="smiles-list"]');if(!t)throw Error('SMILES field missing');
t.value='''+payload+''';t.dispatchEvent(new Event('input',{bubbles:true}));t.dispatchEvent(new Event('change',{bubbles:true}));
return t.value;})()''')
    def submit(self,text):
        return self.evaluate('''(()=>{
if(location.origin!=='''+json.dumps(self.base)+''')throw Error('Unexpected origin');
const expected='''+json.dumps(text,ensure_ascii=True)+''';const f=document.querySelector('form#form2');
const verify=()=>{const value=f.elements['smiles-list'].value;
if(value!==expected)throw Error('SMILES_INTEGRITY_MISMATCH');
const decoded=new URLSearchParams(new FormData(f)).get('smiles-list').replaceAll(String.fromCharCode(13,10),String.fromCharCode(10));
if(decoded!==expected)throw Error('FORM_ENCODING_MISMATCH');};
verify();
const original=f.submit;f.submit=function(){verify();return original.call(f);};
f.addEventListener('submit',e=>{try{verify();}catch(error){e.preventDefault();throw error;}},{once:true});
const buttons=[...f.querySelectorAll('button')].filter(b=>(b.getAttribute('aria-label')||b.textContent).trim()==='Submit');
if(buttons.length!==1)throw Error('Submit button changed');buttons[0].click();return true;})()''')
    def csv_link(self):
        links=self.evaluate("[...document.querySelectorAll('a[href*=\"/download/csv\"]')].map(a=>a.href)")
        unique=set(links)
        if len(unique)!=1:raise StopRun('Не найдена однозначная ссылка CSV результата.')
        url=next(iter(unique))
        if not url.startswith(self.base+'/server/result/'):raise StopRun('Неожиданный адрес CSV.')
        return url
    def download(self,url,timeout=120):
        key='__admet_download_'+uuid.uuid4().hex;k=json.dumps(key)
        if not url.startswith(self.base+'/server/result/'):raise StopRun('Неожиданный адрес скачивания.')
        self.evaluate('''(()=>{window['''+k+''']={state:'loading'};
fetch('''+json.dumps(url)+''',{credentials:'same-origin'}).then(async r=>{
window['''+k+''']={state:'done',status:r.status,retry_after:r.headers.get('Retry-After'),text:await r.text()};
}).catch(e=>{window['''+k+''']={state:'error',error:String(e)};});return true;})()''')
        deadline=time.monotonic()+timeout
        try:
            while time.monotonic()<deadline:
                state=self.evaluate('(()=>{const d=window['+k+'];return d?{state:d.state,status:d.status,error:d.error}:null;})()')
                if state and state['state']=='done':return self.evaluate('window['+k+']')
                if state and state['state']=='error':raise StopRun('Ошибка скачивания: '+state['error'])
                time.sleep(1)
            raise StopRun('Скачивание не завершилось; URL результата сохранён.')
        finally:
            try:self.evaluate('(()=>{delete window['+k+'];return true;})()')
            except Exception:pass
    def close_owned_tab(self):
        self.command('close t')

def check_page(collector,i,state,stage):
    save(collector.folder(i)/(stage+'-page.json'),state)
    status=int(state.get('status') or 0)
    if state.get('title','').startswith('429') or state.get('text','').strip().startswith('429 Too Many Requests'):status=429
    if status==429:
        collector.set_state(i,phase='rate_limited',http_status=429,stage=stage,retry_not_before=None)
        raise StopRun('Сайт вернул HTTP429; прогресс сохранён.')
    if status>=400:
        collector.set_state(i,phase='service_error',http_status=status,stage=stage)
        raise StopRun('Сайт вернул HTTP'+str(status))
    if not collector.own(state['url']):raise StopRun('Вкладка перешла на другой сайт; действия остановлены.')

def process(collector,chrome,i,timeout,retry_rejected):
    if collector.completed(i) or collector.adopt_download(i):return
    folder=collector.folder(i);state=collector.state(i);saved_url=state.get('result_url')
    if state['phase'] in ('uncertain','submitting') and not saved_url:raise StopRun(f'Исход пакета{i+1} неизвестен; нужен --result-url, без повторного Submit.')
    if state['phase'] in ('invalid_result','integrity_error'):raise StopRun('Пакет требует проверки: '+state['phase'])
    if state['phase'] in ('rate_limited','service_error'):
        if not retry_rejected:raise StopRun('Пакет ранее отклонён. После восстановления доступа используйте --retry-rejected.')
        if state.get('retry_not_before') and time.time()<state['retry_not_before']:raise StopRun('Retry-After ещё не истёк.')
        if state.get('stage')=='submit' and state.get('http_status',429)!=429:raise StopRun('Исход отправки неизвестен; нужен URL результата.')
    if saved_url:
        if not collector.result_url(saved_url):raise StopRun('Неверный сохранённый URL.')
        result=chrome.goto(saved_url,timeout)
    else:
        collector.emit('opening_screening',batch=i+1,browser='current_user_chrome')
        check_page(collector,i,chrome.goto(collector.base+'/server/screening'),'screening')
        expected=collector.payload(i);actual=chrome.fill(expected)
        if actual!=expected:raise StopRun('SMILES в Chrome отличаются от исходных. Submit не нажат.')
        save(folder/'textarea-integrity.json',{'utc':now(),'rows':len(collector.batches[i]),'exact_character_and_order_match':True,
            'source_utf8_sha256':hashlib.sha256(expected.encode()).hexdigest(),'textarea_utf8_sha256':hashlib.sha256(actual.encode()).hexdigest()})
        attempt=int(state.get('attempt',0))+1
        collector.set_state(i,phase='submitting',attempt=attempt,stage='submit')
        save(folder/f'attempt-{attempt:03}.json',{'utc':now(),'smiles_text_sha256':sha(folder/'smiles.txt'),'browser':'current_user_chrome'})
        collector.emit('submit',batch=i+1,rows=len(collector.batches[i]),browser='current_user_chrome')
        try:
            chrome.submit(expected);result=chrome.wait(timeout,after_submit=True)
        except BaseException:
            try:view=chrome.view()
            except Exception:view={}
            collector.set_state(i,phase='uncertain',result_url=view.get('url') if collector.result_url(view.get('url','')) else None)
            raise
    check_page(collector,i,result,'submit' if not saved_url else 'existing_result')
    if not collector.result_url(result['url']):raise StopRun('Не найдена страница результата; повторная отправка не выполнена.')
    collector.set_state(i,phase='result_ready',result_url=result['url'])
    url=chrome.csv_link();download=chrome.download(url)
    if download['status']==429:
        collector.set_state(i,phase='rate_limited',http_status=429,stage='download',retry_not_before=retry_time(download.get('retry_after')))
        raise StopRun('Скачивание вернуло HTTP429; URL расчёта сохранён.')
    if download['status']!=200:raise StopRun('Ошибка скачивания HTTP'+str(download['status']))
    partial=folder/'result.csv.partial';partial.write_bytes(download['text'].encode('utf-8'))
    save(folder/'download.json',{'utc':now(),'sha256':sha(partial),'result_url':result['url'],'download_url':url,
         'acquisition':'same-origin CSV link fetched inside the user Chrome tab; UTF8 text saved locally'})
    partial.replace(folder/'result.csv')
    try:collector.adopt_download(i)
    except Exception:collector.set_state(i,phase='invalid_result');raise
    collector.emit('batch_complete',batch=i+1,**collector.status())
