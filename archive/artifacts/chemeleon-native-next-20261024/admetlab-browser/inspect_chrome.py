from pathlib import Path
import json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent
with sync_playwright() as p:
 context=p.chromium.launch_persistent_context(str(root/'chrome-profile'),channel='chrome',headless=False,accept_downloads=True)
 page=context.pages[0] if context.pages else context.new_page()
 try:
  response=page.goto('https://admetlab3.scbdd.com/server/screening',wait_until='domcontentloaded',timeout=30000)
  print(json.dumps({'status':response.status,'url':page.url,'title':page.title(),'forms':page.locator('form').evaluate_all('(forms)=>forms.map(f=>({id:f.id,action:f.getAttribute("action"),method:f.method,fields:[...f.elements].map(e=>({tag:e.tagName,type:e.type,name:e.name,text:e.textContent}))}))')}),flush=True)
 except Exception as e:print(json.dumps({'error':str(e),'url':page.url}),flush=True)
 page.screenshot(path=str(root/'chrome-inspect.png'))
 (root/'chrome-inspect.html').write_text(page.content())
 context.close()
