import json,unittest
from pathlib import Path
import numpy as np,pandas as pd
from night.h5_features import build_views
from night.admet_full_contract import ContractError
from night.tabpfn_admet import preprocess
ROOT=Path(__file__).resolve().parents[1]
class H5Tests(unittest.TestCase):
 def test_real_cache_identity_and_matched_views(self):
  cfg=json.loads((ROOT.parent/'local-preflight-config.json').read_text())
  data=pd.read_csv(cfg['embedding_assets']['adme_source_rows']['path']);ad=np.ones((4905,120))
  views,audit=build_views(data,ad,cfg);self.assertEqual(views['adme'].shape,(4905,600));self.assertEqual(views['adme_admet'].shape,(4905,720));np.testing.assert_array_equal(views['adme'],views['adme_admet'][:,:600]);self.assertEqual(audit['blind_embedding_rows'],0)
  changed=data.copy();changed.loc[0,'SMILES']='C'
  with self.assertRaisesRegex(ContractError,'SMILES/order'):build_views(changed,ad,cfg)
  with self.assertRaisesRegex(ContractError,'IDs/order'):build_views(data.iloc[::-1],ad,cfg)
 def test_matched_scaling_has_identical_embedding_prefix(self):
  rng=np.random.default_rng(42);a=rng.normal(size=(30,600));b=np.concatenate([a,rng.normal(size=(30,120))],axis=1)
  ax,aq,_,_=preprocess(a[:20],a[20:]);bx,bq,_,_=preprocess(b[:20],b[20:]);np.testing.assert_array_equal(ax,bx[:,:600]);np.testing.assert_array_equal(aq,bq[:,:600])
if __name__=='__main__':unittest.main()
