"""No weights/downloads/training: extraction contracts with tiny fake encoders."""
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import torch

from night.encoders import extract_features, publish_features, ExtractionFailure, _sha, main
from night.features import build_features


class FakeTokenizer:
    def __call__(self, smiles, **kwargs):
        if isinstance(smiles, str):
            return {'input_ids': list(range(len(smiles)+2))}
        return {'input_ids': torch.tensor([[len(s), len(s)+1] for s in smiles])}


class FakeModel:
    def eval(self):
        return self
    def to(self, device):
        assert device == 'cpu'
        return self
    def __call__(self, input_ids):
        return types.SimpleNamespace(pooler_output=input_ids.float())


class EncoderContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.frame = pd.DataFrame({'Molecule_Name': ['b', 'a', 'c'], 'SMILES': ['CCO', 'CC', 'CCCCCCCC']})
        directory = self.root / 'hf'; directory.mkdir()
        (directory / 'config.json').write_text(json.dumps({'hidden_size': 2, 'max_position_embeddings': 8}))
        self.record = {'model_dir': 'hf', 'revision': 'a'*40,
                       'files_sha256': {'config.json': _sha(directory/'config.json')}}
        self.loads = []
        def load_tokenizer(path, **kwargs):
            self.loads.append(kwargs)
            return FakeTokenizer()
        def load_model(path, **kwargs):
            self.loads.append(kwargs)
            return FakeModel()
        self.fake = types.SimpleNamespace(
            AutoTokenizer=types.SimpleNamespace(from_pretrained=load_tokenizer),
            AutoModel=types.SimpleNamespace(from_pretrained=load_model))
        self.config = {'encoder_asset': self.record, 'device': 'cpu', 'failure_policy': 'nan', 'batch_size': 1}

    def tearDown(self):
        self.tmp.cleanup()

    def test_molformer_alignment_long_smiles_audited_no_truncation(self):
        with patch.dict(sys.modules, transformers=self.fake):
            X, names, audit = extract_features(self.frame, 'molformer', self.root, self.config)
        np.testing.assert_equal(X[:2], [[3,4], [2,3]])
        self.assertTrue(np.isnan(X[2]).all())
        self.assertEqual(audit['token_lengths'], [5,4,10])
        self.assertEqual(audit['failures'], [{'id':'c','reason':'token_limit_exceeded'}])
        self.assertEqual(names, ['molformer_0','molformer_1'])
        self.assertTrue(all(x['local_files_only'] for x in self.loads))

    def test_long_smiles_strict_failure_has_audit(self):
        with patch.dict(sys.modules, transformers=self.fake):
            with self.assertRaises(ExtractionFailure) as caught:
                extract_features(self.frame, 'molformer', self.root, {**self.config, 'failure_policy':'raise'})
        self.assertEqual(caught.exception.audit['failures'][0]['id'], 'c')
        self.assertEqual(len(self.loads), 1)  # No model load after a known bad structure.

    def test_unpinned_code_and_hash_mismatch_are_failures(self):
        (self.root/'hf'/'modeling.py').write_text('unverified = True')
        with self.assertRaises(ExtractionFailure) as caught:
            extract_features(self.frame, 'molformer', self.root, self.config)
        self.assertIn('Unpinned bundle', str(caught.exception))
        (self.root/'hf'/'modeling.py').unlink()
        (self.root/'hf'/'config.json').write_text('{}')
        with self.assertRaises(ExtractionFailure) as caught:
            extract_features(self.frame, 'molformer', self.root, self.config)
        self.assertIn('SHA-256 mismatch', str(caught.exception))

    def test_shared_manifest_and_precomputed_reorder(self):
        with patch.dict(sys.modules, transformers=self.fake):
            X, names, audit = extract_features(self.frame, 'molformer', self.root, self.config)
        publish_features(self.frame, X, names, audit, self.root, 'molformer')
        publish_features(self.frame, X, names, audit, self.root, 'other')
        manifest = json.loads((self.root/'feature_manifest.json').read_text())
        self.assertEqual(set(manifest['features']), {'molformer','other'})
        reordered, _, _ = build_features(self.frame.iloc[[1,0]], 'precomputed', self.root, {'asset_key':'molformer'})
        np.testing.assert_equal(reordered, X[[1,0]])
        with self.assertRaises(FileExistsError):
            publish_features(self.frame, X, names, audit, self.root, 'molformer')

    def test_cli_row_guard_writes_failure_audit(self):
        self.frame.to_csv(self.root/'molecules.csv', index=False)
        with self.assertRaises(ValueError):
            main(['--molecules',str(self.root/'molecules.csv'),'--encoder','molformer',
                  '--asset-root',str(self.root),'--asset-key','molformer','--audit-path',str(self.root/'audit.json')])
        self.assertIn('Expected 5655',json.loads((self.root/'audit.json').read_text())['error'])

    def test_monroe_missing_graph_id_alignment_and_strict_state(self):
        source = self.root/'monroe-source'; source.mkdir()
        (source/'__init__.py').write_text('')
        (self.root/'weights.pt').write_bytes(b'fake')
        (self.root/'monroe-config.json').write_text(json.dumps({'encoder':{'hidden_dim':2}}))
        record = {'source_dir':'monroe-source','revision':'b'*40,
                  'files_sha256':{'__init__.py':_sha(source/'__init__.py')},
                  'model_asset':{'path':'weights.pt','sha256':_sha(self.root/'weights.pt')},
                  'config_asset':{'path':'monroe-config.json','sha256':_sha(self.root/'monroe-config.json')}}
        graph = lambda smi: {'pos_rdkit':np.array([[0,0,1]],dtype=float),'smiles':smi}
        class FakeEncoder(FakeModel):
            def load_state_dict(inner, state, strict):
                self.assertTrue(strict)
                self.assertEqual(set(state), {'weight'})
            def __call__(inner, batch):
                return batch.float(), None
        modules = {
            'monroe':types.SimpleNamespace(__file__=str(source/'__init__.py')),
            'monroe.eval.embed':types.SimpleNamespace(
                featurize_smiles=lambda smiles,n_workers: [(s,graph(s)) for s in reversed(smiles) if len(s)<8],
                to_pyg=lambda g:[len(g['smiles']),len(g['smiles'])+1]),
            'monroe.model.ckpt':types.SimpleNamespace(_build_encoder=lambda hp:FakeEncoder(),
                _load_state_dict=lambda path,device:{'encoder.weight':torch.zeros(1),'head.weight':torch.ones(1)}),
            'torch_geometric.data':types.SimpleNamespace(Batch=types.SimpleNamespace(from_data_list=torch.tensor))}
        with patch.dict(sys.modules, modules):
            X, _, audit = extract_features(self.frame, 'monroe', self.root,
                {'encoder_asset':record,'device':'cpu','failure_policy':'nan'})
        np.testing.assert_equal(X[:2], [[3,4],[2,3]])
        self.assertTrue(np.isnan(X[2]).all())
        self.assertEqual(audit['ignored_nonencoder_state_keys'], ['head.weight'])
        self.assertEqual(audit['failures'][0]['id'], 'c')

    def test_foundation_rejects_any_cyp_adapted_weight_hash(self):
        with self.assertRaises(ExtractionFailure) as caught:
            extract_features(self.frame, 'chemeleon_foundation', self.root,
                             {'encoder_asset': {'model_asset': {'path':'anything.pt','sha256':'0'*64}}})
        self.assertIn('original published', str(caught.exception))

    def test_foundation_mean_pooling_uses_no_predictor(self):
        from night.encoders import _chemeleon_foundation
        expected = 'c376624d3407204e780a0ed13a9ac097cc9bb1c13ef89cdbc633c1715c183651'
        class FakeMP(FakeModel):
            output_dim = 2
            def __init__(self, **kwargs):
                pass
            def load_state_dict(inner, state, strict):
                self.assertTrue(strict)
            def __call__(self, batch):
                return batch.V
        class Aggregate(FakeModel):
            def __call__(self, values, batch):
                return torch.stack([values[batch==i].mean(0) for i in range(int(batch.max())+1)])
        class BMG:
            def __init__(self, graphs):
                self.V = torch.tensor(np.concatenate([g.V for g in graphs]), dtype=torch.float32)
                self.batch = torch.tensor(np.concatenate([[i]*len(g.V) for i,g in enumerate(graphs)]))
            def to(self, device):
                pass
        featurizer = lambda mol:types.SimpleNamespace(V=np.full((mol.GetNumAtoms(),2),mol.GetNumAtoms()), E=np.zeros((2,1)))
        fake_chemprop = types.SimpleNamespace(nn=types.SimpleNamespace(BondMessagePassing=FakeMP,
                MeanAggregation=Aggregate, SumAggregation=Aggregate, NormAggregation=Aggregate),
                featurizers=types.SimpleNamespace(SimpleMoleculeMolGraphFeaturizer=lambda:featurizer))
        audit = {'ids':self.frame.Molecule_Name.tolist(),'failures':[]}
        with patch.dict(sys.modules, {'chemprop':fake_chemprop,'chemprop.data.collate':types.SimpleNamespace(BatchMolGraph=BMG)}), \
             patch('night.encoders.verified_file', return_value=Path('fake.pt')), \
             patch.object(torch,'load',return_value={'hyper_parameters':{'d_v':2,'d_e':1},'state_dict':{}}):
            X = _chemeleon_foundation(self.frame, {'model_asset':{'path':'fake.pt','sha256':expected}},
                                      self.root, {'device':'cpu','batch_size':2}, audit)
        np.testing.assert_equal(X, [[3,3],[2,2],[8,8]])
        self.assertFalse(audit['cyp_finetuning'])
        self.assertTrue(audit['pooling_before_predictor'])


if __name__ == '__main__':
    unittest.main()
