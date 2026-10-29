"""Verified ADMETlab web CSV decoder, extracted from fe3a466; no networking."""
import ast,csv,io,math,datetime
from urllib.parse import quote
PROVENANCE={'source_mode':'web_default','backend':'documented_web_batch','api_probe_vectors_used':False}
class ContractError(ValueError):pass
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def parse_batch(body,inputs,cfg,taskid):
 reader=csv.DictReader(io.StringIO(body.decode('utf-8-sig')));fields=reader.fieldnames or []
 if len(set(fields))!=len(fields):raise ContractError('DuplicateCSVheaders')
 if not {'raw_smiles','smiles'}<=set(fields):raise ContractError('WebCSVmustcarryraw_smilesandsmiles')
 if set(cfg['forbidden_api_legacy_columns'])&set(fields):raise ContractError('UnexpectedAPIlegacycolumns;source-regimereviewrequired')
 mapping=cfg['web_column_to_endpoint'];required=set(mapping)
 if not required<=set(fields):raise ContractError('Missingwebendpointcolumns:'+','.join(sorted(required-set(fields))))
 expected={r['SMILES']:r for r in inputs}
 if len(expected)!=len(inputs):raise ContractError('InputSMILESnotunique')
 seen=set();success=[];failed=[];associations=[]
 for index,row in enumerate(reader):
  raw=row['raw_smiles']
  if raw not in expected:raise ContractError('Unknownraw_smilesinreturnedCSV')
  if raw in seen:raise ContractError('Duplicatedraw_smilesinreturnedCSV')
  seen.add(raw);source=expected[raw];features={};categories={};missing=[];schema=[]
  for col,text in row.items():
   if col in {'raw_smiles','smiles'}:continue
   group,name=mapping.get(col,['csv_extra',col]);prefix='ADMETLAB::'+group+'::'+name
   schema.append({'category':group,'name':name,'web_column':col,'value_type':'web_csv','extra_fields':[]})
   if text is None or text.strip()=='':features[prefix]=None;missing.append(prefix)
   elif text.startswith('['):
    try:items=ast.literal_eval(text)
    except (ValueError,SyntaxError):raise ContractError('InvalidCSVrulelist:'+col)
    if not isinstance(items,list):raise ContractError('CSVrulevalueisnotlist')
    categories[prefix]=items;features[prefix]=float(len([x for x in items if x not in (None,'','-')]))
   else:
    try:value=float(text)
    except ValueError:
     categories[prefix]=text;features[prefix+'::category='+quote(text,safe='')]=1.
    else:
     features[prefix]=value if math.isfinite(value) else None
     if not math.isfinite(value):missing.append(prefix)
  identity={'request_id':source['request_id'],'SMILES':raw,'priority':source['priority'],'service_smiles':row['smiles'],'taskid':taskid}
  if not row['smiles'] or 'invalid' in row['smiles'].lower():
   failed.append({**identity,'reason':'service_reported_invalid_smiles','returned_row_index':index});continue
  success.append({**identity,'features':features,'categories':categories,'missing':missing,'schema':schema,'endpoint_count':len(schema),'cached':False,'received_utc':now(),**PROVENANCE})
  associations.append({'request_id':source['request_id'],'input_index':inputs.index(source),'returned_row_index':index,'raw_smiles':raw,'service_smiles':row['smiles'],'association':'exactraw_smiles'})
 for raw in expected.keys()-seen:failed.append({**expected[raw],'reason':'service_omitted_input_row'})
 return success,failed,{'input_count':len(inputs),'returned_count':len(seen),'mapped_count':len(success),'failed_count':len(failed),'associations':associations,'columns':fields}
