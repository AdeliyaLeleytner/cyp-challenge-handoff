import copy,json,tempfile,unittest,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from night.admet_full_contract_v1 import ContractError,digest
from night.external_tabpfn_contract import fixed_model_contract,require_fixed_model,SPECS
from night.final_adme_features import load_blind_bank,ENCODER_RUNTIME
ROOT=Path(__file__).resolve().parents[1]
class Tests(unittest.TestCase):
    def model(self,view='adme_admet'):
        m=json.loads((ROOT/'tabpfn_final_h5_config.template.json').read_text())['expected_tabpfn_model_contract']
        return fixed_model_contract(m['predictor_source_sha256'],m['license_sha256'],view,m['embedding_assets_sha256'])
    def test_view_and_encoder_are_part_of_model_identity(self):
        a=self.model('adme');b=self.model('adme_admet');self.assertEqual(a['feature_count'],600);self.assertEqual(b['feature_count'],720)
        with self.assertRaisesRegex(ContractError,'provenance mismatch'):require_fixed_model(a,b)
        pins=copy.deepcopy(a['embedding_assets_sha256']);pins['adme_checkpoint']='0'*64
        with self.assertRaisesRegex(ContractError,'provenance changed'):fixed_model_contract('a'*64,'b'*64,'adme',pins)
    def test_no_existing_blind_bank_is_not_silently_filled(self):
        with self.assertRaisesRegex(ContractError,'requires verified750'):load_blind_bank({},self.model(),pd.DataFrame(),'request','test')
    def test_blind_bank_protocol_runtime_and_order(self):
        model=self.model();pins=model['embedding_assets_sha256']
        blind=pd.DataFrame({'Molecule_Name':['id'+str(i) for i in range(750)],'SMILES':['CC']*750,'request_id':['req'+str(i) for i in range(750)]})
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);np.save(root/'matrix.npy',np.zeros((750,600),np.float32));blind.to_csv(root/'rows.csv',index=False)
            receipt=json.loads((ROOT/'adme_blind_receipt.template.json').read_text());identity=hashlib.sha256(json.dumps(blind[['Molecule_Name','SMILES']].to_dict('records'),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
            receipt.update(status='complete',approved=True,official_test_sha256='test',actual_runtime=ENCODER_RUNTIME,producer_run_id='run',producer_commit='commit',exact_input_ids_smiles_order_sha256=identity,output_ids_smiles_order_sha256=identity,output_matrix_sha256=digest(root/'matrix.npy'),shape_verified=True,all_finite=True)
            def repin():
                (root/'receipt.json').write_text(json.dumps(receipt));manifest={'schema_version':1,'producer_orx_run_id':'run','producer_commit':'commit','selection_query_request_sha256':'request','files':{k:{'path':str(root/name),'sha256':digest(root/name)} for k,name in [('matrix','matrix.npy'),('rows','rows.csv'),('receipt','receipt.json')]}}
                (root/'manifest.json').write_text(json.dumps(manifest));return {'adme_blind_embedding_manifest':str(root/'manifest.json'),'adme_blind_embedding_manifest_sha256':digest(root/'manifest.json')}
            cfg=repin();a,proof=load_blind_bank(cfg,model,blind,'request','test');self.assertEqual(a.shape,(750,600));self.assertEqual(proof['encoder_checkpoint_sha256'],pins['adme_checkpoint'])
            receipt['actual_runtime']={**ENCODER_RUNTIME,'torch':'2.6.0'};cfg=repin()
            with self.assertRaisesRegex(ContractError,'runtime differs'):load_blind_bank(cfg,model,blind,'request','test')
            receipt['actual_runtime']=ENCODER_RUNTIME;blind.iloc[::-1].to_csv(root/'rows.csv',index=False);cfg=repin()
            with self.assertRaisesRegex(ContractError,'ID/SMILES/order'):load_blind_bank(cfg,model,blind,'request','test')
if __name__=='__main__':unittest.main()
