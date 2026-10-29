from pathlib import Path
from urllib.parse import unquote,urlsplit
from html.parser import HTMLParser
import json,zipfile,xml.etree.ElementTree as E,hashlib
import pandas as pd
P=Path(__file__).resolve().parent;W=P/'outputs/01a16d31-5fea-7710-b157-221709646aea/CYP_dataset_comparison.xlsx';ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(W) as z:
 book=E.fromstring(z.read('xl/workbook.xml'));names=[x.attrib['name'] for x in book.findall('s:sheets/s:sheet',ns)];assert len(names)==12
 errors=[]
 for f in z.namelist():
  if f.startswith('xl/worksheets/sheet') and f.endswith('.xml'):
   t=E.fromstring(z.read(f));errors.extend((f,c.attrib['r']) for c in t.findall('.//s:c',ns) if c.attrib.get('t')=='e')
 assert not errors,errors
 c=E.fromstring(z.read('xl/worksheets/sheet1.xml'));cells={x.attrib['r']:x for x in c.findall('.//s:c',ns)}
 assert int(cells['C7'].find('s:v',ns).text)==60882
 assert abs(float(cells['K8'].find('s:v',ns).text)-205/4901)<1e-12
 assert cells['B26'].find('s:f',ns).text=='B7'
 chart_count=len([x for x in z.namelist() if '/charts/chart' in x and x.endswith('.xml')])
manifest=json.loads((P/'source_manifest.json').read_text());mismatches=[r['path'] for r in manifest if hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()!=r['sha256']];assert not mismatches
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.ids=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if tag=='a' and 'href' in a:self.links.append(a['href'])
x=Links();x.feed((P/'comparison.html').read_text());assert len(x.ids)==len(set(x.ids))
missing=[]
for link in x.links:
 if link.startswith(('https:','http:','data:')):continue
 if link.startswith('#'):
  if link[1:] not in x.ids:missing.append(link)
 elif link!='comparison_bundle.zip' and not (P/unquote(urlsplit(link).path)).exists():missing.append(link)
assert not missing,missing
u=pd.read_csv(P/'tables/user_rows_all_archive_membership.csv.gz');raw=json.loads((P/'all_archive_summary.json').read_text())
assert len(u)==60882 and u.iso.nunique()==28822
assert u.loc[u.new_key14_vs_all_raw_excluding_TEST,'iso_key'].str[:14].nunique()==raw['new_key14_excluding_TEST']==3323
assert u.loc[u.new_parent_vs_all_raw_excluding_TEST,'parent'].nunique()==raw['new_parent_excluding_TEST']==3927
assert u.relation.eq('upper_bound').sum()==13559
r={'xlsx_sheets':names,'xlsx_error_cells':errors,'saved_formula_check':'K8=205/4901; chart helper B26=B7','saved_user_rows':60882,'native_charts':chart_count,'input_files_hash_verified':len(manifest),'html_relative_links_missing':missing,'html_unique_element_ids':True,'novelty_counts_independently_checked':True,'figures_pdf':len(list((P/'figures').glob('*.pdf'))),'figures_svg':len(list((P/'figures').glob('*.svg'))),'browser_qa':'Native browser connection unavailable; every worksheet top view and generated figures inspected; HTML links and structure checked. No browser interaction test claimed.'}
(P/'qa/final_validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False))
