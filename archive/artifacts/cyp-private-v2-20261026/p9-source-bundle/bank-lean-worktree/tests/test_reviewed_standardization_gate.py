"""Final-only gate: one pinned representation convention is distinct from exclusion."""
import copy,hashlib,json,unittest
from night.admet_full_contract_v1 import ContractError
from night.admet_outcome_contract import PINNED_PROTON_TRANSFER,validate_reviewed_bindings,validate_status_flags

class Tests(unittest.TestCase):
    def fixtures(self):
        rejected=[{'request_id':'68bd1bd95ba465c01242172601c742e27c193936ade6718ca7f8c8b4764c40d4'},{'request_id':'8ce86a6ae65d3692e7305e2c58ac62eebd97d3d943e093f577da25c36988246b'}]
        excluded=[{'request_id':'3488cefb9a5eaad40d36431e5760123e7ee1738496efb2ac00a5204f00afeed1'}];standard=[dict(PINNED_PROTON_TRANSFER)]
        items=[('service-rejections.json','service_rejections',rejected,'service_rejected_requests','service_rejected'),('feature-eligibility-exclusions.json','feature_exclusions',excluded,'feature_identity_excluded_requests','unresolved_service_structure'),('reviewed-standardizations.json','reviewed_standardizations',standard,'reviewed_standardization_requests','reviewed_internal_proton_transfer')]
        files={key:{'sha256':hashlib.sha256(key.encode()).hexdigest()} for _,key,_,_,_ in items};policy={'files':{filename:files[key] for filename,key,_,_,_ in items}};binding={'exceptions':[]}
        for filename,key,records,policy_key,kind in items:
            policy[policy_key]=[r['request_id'] for r in records]
            binding['exceptions'] += [{**r,'kind':kind,'approval_manifest_sha256':files[key]['sha256']} for r in records]
        return policy,binding,files,rejected,excluded,standard
    def test_exact_standardization_is_eligible_not_excluded(self):
        reviewed,reject,exclude,standard=validate_reviewed_bindings(*self.fixtures())
        rid=PINNED_PROTON_TRANSFER['request_id'];self.assertIn(rid,standard);self.assertNotIn(rid,reject|exclude);self.assertEqual(len(reviewed),4)
    def test_standardization_cannot_be_mapped_to_exclusion(self):
        args=self.fixtures();args[1]['exceptions'][-1]['kind']='unresolved_service_structure'
        with self.assertRaisesRegex(ContractError,'kind/disposition'):validate_reviewed_bindings(*args)
    def test_standardization_requires_its_own_manifest_pin(self):
        args=self.fixtures();args[1]['exceptions'][-1]['approval_manifest_sha256']=args[2]['feature_exclusions']['sha256']
        with self.assertRaisesRegex(ContractError,'approval hash'):validate_reviewed_bindings(*args)
    def test_no_generic_acceptance_of_another_proton_transfer(self):
        args=self.fixtures();args[5][0]['request_id']='unreviewed';args[0]['reviewed_standardization_requests']=['unreviewed'];args[1]['exceptions'][-1]['request_id']='unreviewed'
        with self.assertRaisesRegex(ContractError,'Only the exact'):validate_reviewed_bindings(*args)
    def test_exact_raw_hash_and_both_strings_must_remain_unchanged(self):
        for field in ('raw_row_sha256','request_smiles','service_smiles'):
            args=self.fixtures();args[1]['exceptions'][-1][field]='changed'
            with self.assertRaisesRegex(ContractError,'row/strings changed'):validate_reviewed_bindings(*args)
    def test_duplicate_or_overlapping_categories_are_rejected(self):
        args=self.fixtures();args[1]['exceptions'].append(args[1]['exceptions'][-1])
        with self.assertRaisesRegex(ContractError,'duplicate'):validate_reviewed_bindings(*args)
        args=self.fixtures();args[4].append({'request_id':PINNED_PROTON_TRANSFER['request_id']});args[0]['feature_identity_excluded_requests'].append(PINNED_PROTON_TRANSFER['request_id'])
        with self.assertRaisesRegex(ContractError,'overlap'):validate_reviewed_bindings(*args)
    def test_raw_numeric_change_still_breaks_exact_row_binding(self):
        raw={'raw_smiles':PINNED_PROTON_TRANSFER['request_smiles'],'smiles':PINNED_PROTON_TRANSFER['service_smiles'],**{'endpoint'+str(i):'0.5' for i in range(120)}}
        columns={'endpoint'+str(i):'ADMETLAB::'+str(i) for i in range(120)};feature={'request_id':PINNED_PROTON_TRANSFER['request_id'],**{v:'0.5' for v in columns.values()}}
        # Component test of row-hash enforcement; policy-level tests above enforce the real fixed hash.
        entry={**PINNED_PROTON_TRANSFER,'kind':'reviewed_internal_proton_transfer','raw_row_sha256':hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()}
        approved={entry['request_id']:entry};self.assertFalse(validate_status_flags(raw,feature,columns,approved))
        raw['endpoint0']='0.6'
        with self.assertRaisesRegex(ContractError,'Reviewed exception changed'):validate_status_flags(raw,feature,columns,approved)
    def test_standardization_does_not_waive_numeric_finiteness(self):
        raw={'raw_smiles':'request','smiles':'service',**{'endpoint'+str(i):'0.5' for i in range(120)}};columns={'endpoint'+str(i):'ADMETLAB::'+str(i) for i in range(120)}
        feature={'request_id':'test',**{v:'0.5' for v in columns.values()}};entry={'kind':'reviewed_internal_proton_transfer','request_smiles':'request','service_smiles':'service','raw_row_sha256':hashlib.sha256(json.dumps(raw,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()};feature['ADMETLAB::0']='nan'
        with self.assertRaisesRegex(ContractError,'Nonfinite'):validate_status_flags(raw,feature,columns,{'test':entry})
if __name__=='__main__':unittest.main()
