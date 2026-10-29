"""One exact parent-reviewed proton-placement convention, not a general normalizer."""
import math
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

def verify_internal_proton_transfer(request,service,approval):
 errors=[]
 if (approval.get('raw_row_sha256')!='23581c841427c031deba5ce32c6a08315519a42ef5eb22ea0e6fdd47a0f49646' or approval.get('request_smiles')!='[N-]=[NH+]N=CC(=O)c1c[nH]c(=O)[nH]c1=O' or approval.get('service_smiles')!='N=NN=CC(=O)c1c[nH]c(=O)[nH]c1=O'):
  return ['unreviewed_proton_transfer_exact_binding']
 if request is None or service is None:return ['reviewed_proton_transfer_requires_sanitized_graphs']
 n=request.GetNumAtoms();mapping=approval.get('exact_atom_map')
 if n!=14 or service.GetNumAtoms()!=14 or mapping!=list(range(14)):
  return ['reviewed_proton_transfer_atom_map_changed']
 if approval.get('request_id')!='c144a5ae385f54b47f0a911da7ebb3ae9830ac594eb61a8654cf52535823ae26':
  return ['unreviewed_proton_transfer_request']
 expected=[{'atom':0,'delta_H':1,'delta_charge':1},{'atom':1,'delta_H':-1,'delta_charge':-1}]
 if approval.get('allowed_atom_changes')!=expected:return ['reviewed_proton_transfer_delta_approval_changed']
 actual=[]
 for i,j in enumerate(mapping):
  a=request.GetAtomWithIdx(i);b=service.GetAtomWithIdx(j)
  if (a.GetAtomicNum(),a.GetIsotope(),a.GetIsAromatic(),a.GetChiralTag(),a.GetNumRadicalElectrons())!=(b.GetAtomicNum(),b.GetIsotope(),b.GetIsAromatic(),b.GetChiralTag(),b.GetNumRadicalElectrons()):errors.append('reviewed_proton_transfer_atom_identity_or_stereo_changed')
  dh=b.GetTotalNumHs()-a.GetTotalNumHs();dq=b.GetFormalCharge()-a.GetFormalCharge()
  if dh or dq:actual.append({'atom':i,'delta_H':dh,'delta_charge':dq})
 if actual!=expected:errors.append('reviewed_proton_transfer_H_charge_changes_differ')
 def bonds(m):
  return sorted((min(b.GetBeginAtomIdx(),b.GetEndAtomIdx()),max(b.GetBeginAtomIdx(),b.GetEndAtomIdx()),b.GetBondTypeAsDouble(),b.GetIsAromatic(),str(b.GetStereo()),str(b.GetBondDir())) for b in m.GetBonds())
 if bonds(request)!=bonds(service):errors.append('reviewed_proton_transfer_heavy_bonds_or_stereo_changed')
 if rdMolDescriptors.CalcMolFormula(request)!=rdMolDescriptors.CalcMolFormula(service):errors.append('reviewed_proton_transfer_formula_changed')
 if not math.isclose(rdMolDescriptors.CalcExactMolWt(request),rdMolDescriptors.CalcExactMolWt(service),rel_tol=0,abs_tol=1e-9):errors.append('reviewed_proton_transfer_mass_changed')
 if Chem.GetFormalCharge(request)!=Chem.GetFormalCharge(service):errors.append('reviewed_proton_transfer_total_charge_changed')
 if sum(a.GetNumRadicalElectrons() for a in request.GetAtoms())!=sum(a.GetNumRadicalElectrons() for a in service.GetAtoms()):errors.append('reviewed_proton_transfer_radical_count_changed')
 return errors
