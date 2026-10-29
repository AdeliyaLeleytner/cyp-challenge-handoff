"""Prepare the documented web form shape. NEVER sends a request.

Output schema/task download routes are not live-verified for this web workflow.
This must not be used as a workaround for an active service/API rate limit.
"""
from html.parser import HTMLParser
from pathlib import Path
import json

class Form(HTMLParser):
    def __init__(self):super().__init__();self.inside=False;self.action=None;self.fields={};self.textarea=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='form':
            self.inside=attrs.get('id')=='form2'
            if self.inside:
                assert attrs.get('method','').lower()=='post';self.action=attrs.get('action')
        elif self.inside and tag=='input' and attrs.get('name'):
            self.fields[attrs['name']]=attrs.get('value','')
        elif self.inside and tag=='textarea':self.textarea=attrs.get('name')
    def handle_endtag(self,tag):
        if tag=='form':self.inside=False

def build_form_fields(html,smiles):
    if not 1<=len(smiles)<=1000:raise ValueError('Documented web limit:1..1000SMILES')
    if any(not isinstance(s,str) or not s.strip() or '\n' in s or '\r' in s for s in smiles):raise ValueError('One nonemptySMILES per row')
    form=Form();form.feed(html)
    assert form.action=='/server/screeningCal' and form.textarea=='smiles-list'
    assert form.fields.get('method')=='2' and form.fields.get('csrfmiddlewaretoken')
    return form.action,{**form.fields,form.textarea:'\n'.join(smiles)}

if __name__=='__main__':
    root=Path(__file__).resolve().parent
    action,fields=build_form_fields((root/'read-only-screening/response.html').read_text(),['CCO','CCN'])
    print(json.dumps({'dry_run':True,'network_requests':0,'action':action,'method':'POST','encoding':'application/x-www-form-urlencoded','payload_keys':list(fields),'method_field':fields['method'],'smiles_count':2,'max_smiles_per_documented_form':1000,'csrf_and_session_cookie_required_for_web_form':True,'current_api_requires_authentication':False,'output_contract':'unknown_without_an_authorized_form_submission','no_rate_limit_workaround':True},indent=2))
