"""Strict per-row output adjudication. No imputation, molecule repair or fitting."""
import ast,hashlib,json,math
from rdkit import Chem
from rdkit.Chem import Descriptors
from rdkit.Chem.MolStandardize import rdMolStandardize

def sha(b):return hashlib.sha256(b).hexdigest()
def row_sha(row):return sha(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
def canon(m):return Chem.MolToSmiles(m,canonical=True,isomericSmiles=True)
def adjudicate(raw,feature,column_map,probability_columns,reviewed):
 rid=sha(raw['raw_smiles'].encode());errors=[]
 out={'request_id':rid,'status':'unadjudicated','numeric_endpoint_complete':False,'chemistry_eligible':False,'relation':None,'errors':errors}
 if feature.get('request_id')!=rid or feature.get('SMILES')!=raw['raw_smiles'] or feature.get('service_smiles')!=raw['smiles']:
  errors.append('raw_feature_identity_mismatch');return out
 allowed=reviewed.get(rid)
 if allowed and (allowed['request_smiles']!=raw['raw_smiles'] or allowed['service_smiles']!=raw['smiles'] or allowed['raw_row_sha256']!=row_sha(raw)):
  errors.append('reviewed_exception_evidence_changed');return out
 rejected=[c for c in column_map if raw.get(c)=='Invalid Molecule']
 if rejected and len(rejected)!=len(column_map):errors.append('unreviewed_partial_service_rejection')
 fullreject=len(rejected)==len(column_map)
 if fullreject and (not allowed or allowed['kind']!='service_rejected'):errors.append('unlisted_service_rejection')
 if allowed and allowed['kind']=='service_rejected' and not fullreject:errors.append('reviewed_rejection_outcome_changed')
 numeric={};alert_lists=[]
 for col,fc in column_map.items():
  text=raw.get(col);fv=feature.get(fc);flagname=fc+'::category=Invalid%20Molecule';flag=feature.get(flagname,'')
  try:flagnum=float(flag) if flag else 0.0
  except (TypeError,ValueError):flagnum=None
  if flagnum!=float(text=='Invalid Molecule'):errors.append('category_flag_mismatch:'+col)
  if text=='Invalid Molecule':
   if fv not in ('',None):errors.append('rejection_has_numeric_value:'+col)
   if flagname not in feature:errors.append('rejection_flag_missing:'+col)
   continue
  try:
   actual=float(fv)
   if not math.isfinite(actual):raise ValueError()
   if text.startswith('['):
    items=ast.literal_eval(text)
    if not isinstance(items,(list,tuple)):raise ValueError()
    expected=float(sum(x not in (None,'','-') for x in items));alert_lists.append((col,items))
   else:expected=float(text)
   if not math.isfinite(expected) or not math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-12):errors.append('raw_numeric_mismatch:'+col)
   numeric[col]=actual
  except (TypeError,ValueError,SyntaxError,AttributeError):errors.append('missing_or_nonnumeric_unrejected_endpoint:'+col)
 for col in probability_columns:
  if col in numeric and not 0<=numeric[col]<=1:errors.append('probability_out_of_bounds:'+col)
 out['numeric_endpoint_complete']=len(numeric)==len(column_map)
 if fullreject:
  out['status']='service_rejected';out['relation']='not_predicted';return out
 out['status']='numeric_returned'
 req=Chem.MolFromSmiles(raw['raw_smiles']);srv=Chem.MolFromSmiles(raw['smiles'])
 if req is None:errors.append('invalid_requested_smiles')
 if allowed and allowed['kind']=='unresolved_service_structure':
  out['status']='numeric_returned_unresolved_service_structure';out['relation']='exact_reviewed_exception'
  # Positional alert checks are still possible without endorsing an unsanitized graph.
  if srv is None:srv=Chem.MolFromSmiles(raw['smiles'],sanitize=False)
 elif allowed and allowed['kind']=='reviewed_internal_proton_transfer':
  from standardization import verify_internal_proton_transfer
  violations=verify_internal_proton_transfer(req,srv,allowed);errors.extend(violations)
  out['relation']='exact_reviewed_internal_proton_transfer' if not violations else 'reviewed_proton_transfer_check_failed'
 elif srv is None:
  errors.append('unlisted_invalid_service_graph');out['relation']='parse_failure'
 elif req is not None:
  if canon(req)==canon(srv):out['relation']='same_isomeric_graph'
  elif canon(rdMolStandardize.Normalize(Chem.Mol(req)))==canon(rdMolStandardize.Normalize(Chem.Mol(srv))):out['relation']='strict_stereo_functional_normalization'
  else:
   uncharger=rdMolStandardize.Uncharger()
   if canon(uncharger.uncharge(Chem.Mol(req)))==canon(uncharger.uncharge(Chem.Mol(srv))):out['relation']='strict_stereo_charge_protonation'
   else:errors.append('unreviewed_service_graph_or_stereo_change');out['relation']='unresolved_difference'
 if srv is not None:
  for col,items in alert_lists:
   for x in items:
    if x in (None,'','-'):continue
    if not isinstance(x,(tuple,list)) or any(not isinstance(i,int) or i<0 or i>=srv.GetNumAtoms() for i in x):errors.append('alert_atom_index_error:'+col)
  if not (allowed and allowed['kind']=='unresolved_service_structure'):
   if 'MW' in numeric and not math.isclose(numeric['MW'],round(Descriptors.ExactMolWt(srv),2),abs_tol=1e-8,rel_tol=0):errors.append('service_MW_mismatch')
   if 'fChar' in numeric and numeric['fChar']!=Chem.GetFormalCharge(srv):errors.append('service_formal_charge_mismatch')
 out['chemistry_eligible']=not errors and not (allowed and allowed['kind']=='unresolved_service_structure')
 return out
