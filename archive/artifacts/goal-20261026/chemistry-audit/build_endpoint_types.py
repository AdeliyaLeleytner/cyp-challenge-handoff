"""Pin endpoint types from already cached official ADMETlab documentation."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,re,csv
ROOT=Path(__file__).resolve().parent
DOC=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/admetlab-access/webbatch-docs/description.md')
API=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-chemeleon-native-20261024/admetlab-auto/page-code-audit/rendered-api-calculation.txt')
class Tables(HTMLParser):
 def __init__(self):super().__init__();self.tables=[];self.table=None;self.row=None;self.cell=None
 def handle_starttag(self,tag,attrs):
  if tag=='table':self.table=[]
  elif tag=='tr' and self.table is not None:self.row=[]
  elif tag in ('td','th') and self.row is not None:self.cell=[]
 def handle_data(self,text):
  if self.cell is not None:self.cell.append(text)
 def handle_endtag(self,tag):
  if tag in ('td','th') and self.cell is not None:self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
  elif tag=='tr' and self.row is not None:self.table.append(self.row);self.row=None
  elif tag=='table' and self.table is not None:self.tables.append(self.table);self.table=None
parser=Tables();parser.feed(DOC.read_text())
reg=[r[0] for r in parser.tables[1] if len(r)>1 and r[1]=='Test set'];classification=[r[0] for r in parser.tables[2] if len(r)>1 and r[1]=='Test set']
assert len(reg)==18 and len(classification)==59
mapping={'logD7.4':'logD','melting point':'mp','boiling point':'bp','pKa (acidic)':'pka_acidic','pKa (basic)':'pka_basic','Caco-2 Permeability':'caco2','MDCK Permeability':'MDCK','CL-plasma':'cl-plasma','T1/2':'t0.5','Bioconcentration Factor':'BCF','Pgp-inhibitor':'pgp_inh','Pgp-substrate':'pgp_sub','HIA':'hia','F20%':'f20','F30%':'f30','F50%':'f50','BCRP inhibitor':'BCRP','MRP1 inhibitor':'MRP1','OATP1B1inhibitor':'OATP1B1','OATP1B3 inhibitor':'OATP1B3','BSEP inhibitor':'BSEP','BBB Penetration':'BBB','HLM Stability':'LM-human','hERG Blockers':'hERG','Human Hepatotoxicity':'H-HT','AMES Mutagenicity':'Ames','Skin Sensitization':'SkinSen','Carcinogencity':'Carcinogenicity','Eye Corrosion':'EC','Eye Irritation':'EI','A549 Cytotoxicity':'A549','hERG Blocker (10um)':'hERG-10um','Hek293 Cytotoxicity':'HEK293','Drug-induced Nephrotoxicity':'Nephrotoxicity-DI','Drug-induced Neurotoxicity':'Neurotoxicity-DI','RPMI-8226 Immunitoxicity':'RPMI-8226'}
def column(name):return mapping.get(name,name.replace(' inhibitor','-inh').replace(' substrate','-sub') if name.startswith('CYP') else name)
with (ROOT/'raw-snapshot.csv').open() as f:raw=next(csv.reader(f))
entries={c:{'kind':'untyped_or_computed_rule','probability_bounds_checked':False} for c in raw if c not in ('raw_smiles','smiles')}
for name in reg:
 c=column(name);assert c in entries;entries[c]={'kind':'regression','probability_bounds_checked':False,'source':'official program description Table2','documented_name':name}
for name in classification:
 c=column(name);assert c in entries;entries[c]={'kind':'classification_probability','probability_bounds_checked':True,'bounds':[0,1],'source':'official program description Table3 + API value/decision distinction','documented_name':name}
for line in API.read_text().splitlines():
 if '- code: "' not in line:continue
 text=json.loads(line.split('- code: ',1)[1])
 for c,explanation in re.findall(r'"([^"\n]+)": "([^"\n]*probability[^"\n]*)"',text):
  if c in entries and '0 to 1' in explanation:entries[c]={'kind':'classification_probability','probability_bounds_checked':True,'bounds':[0,1],'source':'official API explanation example explicitly states probability in0..1','documented_explanation':explanation}
result={'sources':[{'path':str(DOC),'sha256':hashlib.sha256(DOC.read_bytes()).hexdigest(),'url':'https://admetlab3.scbdd.com/documentation/description.md'},{'path':str(API),'sha256':hashlib.sha256(API.read_bytes()).hexdigest(),'url':'https://admetlab3.scbdd.com/apis/#/two'}],'entries':entries,'policy':'Only documented classification probabilities receive0..1 bounds. Regression and untyped/computed/rule columns do not receive generic probability bounds; raw rule-list extraction and molecular mass/formal charge have separate checks.'}
(ROOT/'endpoint-types.json').write_text(json.dumps(result,indent=2)+'\n')
print({kind:sum(v['kind']==kind for v in entries.values()) for kind in sorted({v['kind'] for v in entries.values()})})
