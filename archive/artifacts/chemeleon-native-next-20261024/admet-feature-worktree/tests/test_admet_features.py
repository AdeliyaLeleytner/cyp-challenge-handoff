"""CPU-only feature contracts and forward parity; no fitted scientific model."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from night.admet_features import (AdmetFeatureCache, FoldImputer, build_with_zero_extended_fresh_head, copy_graph_model_weights,
                                 file_sha256, prepare_fold_descriptors)

COLS = ['ADMETLAB::physicochemical::MW', 'ADMETLAB::metabolism::CYP2D6-inh',
        'ADMETLAB::csv_extra::cl-int', 'ADMETLAB::csv_extra::Other_assay_interference']


def fixture():
    ids = ['a', 'b', 'c', 'd']; smiles = ['CCO', 'CCN', 'CCC', 'CO']
    req = [hashlib.sha256(x.encode()).hexdigest() for x in smiles]
    mapping = pd.DataFrame({'Molecule_Name': ids, 'SMILES': smiles, 'request_smiles': smiles,
                            'request_id': req, 'source': ['mock'] * 4})
    table = pd.DataFrame({'request_id': req, 'SMILES': smiles, 'priority': [0] * 4,
                          'service_smiles': smiles, 'taskid': ['mock-task'] * 4,
                          COLS[0]: [40., 50., 10000., np.nan], COLS[1]: [.1, np.nan, .9, .6],
                          COLS[2]: [np.nan, np.nan, 8., 7.], COLS[3]: [0., 1., .4, .8]})
    native = mapping[['Molecule_Name', 'SMILES']].rename(columns={'Molecule_Name': 'molecule_name', 'SMILES': 'smiles'})
    return mapping, table, native


class FeatureContracts(unittest.TestCase):
    def test_mapping_order_and_all_cyp_columns_are_retained(self):
        mapping, table, native = fixture()
        # Multiple source records may bind the same ID/SMILES/request triple.
        mapping = pd.concat([mapping, mapping.iloc[[0]]], ignore_index=True)
        cache = AdmetFeatureCache(mapping, table.iloc[[3, 1, 0, 2]], {'feature_columns': COLS})
        got = cache.align(native.iloc[[2, 0, 3]])
        self.assertEqual(got.molecule_ids, ('c', 'a', 'd'))
        self.assertEqual(got.columns, tuple(COLS))
        np.testing.assert_allclose(got.values[:, 1], [.9, .1, .6])
        self.assertEqual(got.values.shape, (3, 4))
        changed = native.copy(); changed['CYP2D6_pIC50_direct_inhibition'] = [999, -100, 1e6, np.nan]
        np.testing.assert_equal(cache.align(native).values, cache.align(changed).values)

    def test_no_id_only_fallback_and_incomplete_cache_fails(self):
        mapping, table, native = fixture()
        cache = AdmetFeatureCache(mapping, table.iloc[:3], {'feature_columns': COLS})
        with self.assertRaisesRegex(ValueError, 'cache is incomplete'): cache.align(native)
        changed = native.iloc[[0]].copy(); changed['smiles'] = 'CCN'
        with self.assertRaisesRegex(ValueError, 'exact ID/SMILES'): cache.align(changed)
        table2 = pd.concat([table, table.iloc[[0]]])
        with self.assertRaisesRegex(ValueError, 'one row per request_id'):
            AdmetFeatureCache(mapping, table2, {'feature_columns': COLS})
        duplicate = mapping.iloc[[0]].copy(); duplicate['request_smiles'] = 'CCCl'; duplicate['request_id'] = hashlib.sha256(b'CCCl').hexdigest()
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            AdmetFeatureCache(pd.concat([mapping, duplicate]), table, {'feature_columns': COLS})

    def test_schema_controls_features_not_numeric_dtype(self):
        mapping, table, _ = fixture()
        hidden = table.copy(); hidden['CYP2D6_pIC50_direct_inhibition'] = 5.
        with self.assertRaisesRegex(ValueError, 'absent from the frozen schema'):
            AdmetFeatureCache(mapping, hidden, {'feature_columns': COLS})
        extra = table.copy(); extra['ADMETLAB::new_endpoint'] = 1.
        with self.assertRaisesRegex(ValueError, 'absent from the frozen schema'):
            AdmetFeatureCache(mapping, extra, {'feature_columns': COLS})
        broken = table.copy(); broken.loc[0, COLS[0]] = np.inf
        with self.assertRaisesRegex(ValueError, 'Infinite'):
            AdmetFeatureCache(mapping, broken, {'feature_columns': COLS})
        broken = table.drop(columns=[COLS[-1]])
        with self.assertRaisesRegex(ValueError, 'endpoints absent'):
            AdmetFeatureCache(mapping, broken, {'feature_columns': COLS})

    def test_fit_only_imputation_missing_flags_and_roundtrip(self):
        mapping, table, native = fixture(); cache = AdmetFeatureCache(mapping, table, {'feature_columns': COLS})
        desc = prepare_fold_descriptors(cache, native.iloc[:2], native.iloc[[2]], native.iloc[[3]])
        np.testing.assert_allclose(desc.imputer.medians, [45., .1, 0., .5])
        np.testing.assert_allclose(desc.train[1], [50., .1, 0., 1., 0., 1., 1., 0.])
        np.testing.assert_allclose(desc.query[0], [45., .6, 0., .8, 1., 0., 1., 0.])
        self.assertEqual(desc.n_extra_descriptors, 8)
        self.assertTrue(desc.imputer.unsupported[2])
        state = json.loads(json.dumps(desc.imputer.to_dict(), allow_nan=False))
        recovered = FoldImputer.from_dict(state)
        np.testing.assert_array_equal(desc.query, recovered.transform(cache.align(native.iloc[[3]])))
        table2 = table.copy(); table2.loc[2:, COLS[0]] = -1e9
        desc2 = prepare_fold_descriptors(AdmetFeatureCache(mapping, table2, {'feature_columns': COLS}), native.iloc[:2], native.iloc[[2]], native.iloc[[3]])
        np.testing.assert_array_equal(desc.train, desc2.train)
        np.testing.assert_array_equal(desc.imputer.medians, desc2.imputer.medians)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            prepare_fold_descriptors(cache, native.iloc[:2], native.iloc[[2]], native.iloc[[0]])
        # Allowing a documented production query overlap never permits inner leakage.
        with self.assertRaisesRegex(ValueError, 'overlap'):
            prepare_fold_descriptors(cache, native.iloc[:2], native.iloc[[0]], native.iloc[[3]], require_disjoint_requests=False)

    def test_file_hash_binding_and_source_schema(self):
        mapping, table, native = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); mapping.to_csv(p/'map.csv', index=False); table.to_csv(p/'features.csv', index=False)
            (p/'schema.json').write_text(json.dumps({'feature_columns': COLS}))
            expected = {'id_map': file_sha256(p/'map.csv'), 'feature_table': file_sha256(p/'features.csv'), 'feature_schema': file_sha256(p/'schema.json')}
            got = AdmetFeatureCache.from_files(p/'map.csv', p/'features.csv', p/'schema.json', expected_sha256=expected)
            self.assertEqual(got.align(native).columns, tuple(COLS))
            with (p/'features.csv').open('a') as stream: stream.write('\n')
            with self.assertRaisesRegex(ValueError, 'Frozen feature inputs changed'):
                AdmetFeatureCache.from_files(p/'map.csv', p/'features.csv', p/'schema.json', expected_sha256=expected)

    def test_native_scaler_is_the_only_scaler(self):
        import torch
        from chemprop import data, nn
        from night.briford_native import runtime
        core = runtime(); mapping, table, native = fixture()
        desc = prepare_fold_descriptors(AdmetFeatureCache(mapping, table, {'feature_columns': COLS}), native.iloc[:2], native.iloc[[2]], native.iloc[[3]])
        kwargs = desc.native_training_kwargs()
        train_dps, _ = core.create_molecule_datapoints(native.iloc[:2].smiles.tolist(), np.zeros((2, 1)), kwargs['train_extra'])
        val_dps, _ = core.create_molecule_datapoints(native.iloc[[2]].smiles.tolist(), np.zeros((1, 1)), kwargs['val_extra'])
        train_ds, val_ds = data.MoleculeDataset(train_dps), data.MoleculeDataset(val_dps)
        scaler = train_ds.normalize_inputs('X_d'); val_ds.normalize_inputs('X_d', scaler)
        np.testing.assert_allclose(scaler.mean_, desc.train.mean(axis=0), rtol=0, atol=1e-7)
        np.testing.assert_array_equal(kwargs['val_extra_raw'], desc.validation)
        transform = nn.ScaleTransform.from_standard_scaler(scaler).eval()
        transformed = transform(torch.tensor(kwargs['val_extra_raw'])).detach().numpy()
        np.testing.assert_allclose(transformed, val_ds.X_d, rtol=1e-6, atol=1e-6)
        spec = core.FoldSpec(hyperparameters={}, n_targets=1)
        extended = desc.configure_spec(spec)
        self.assertTrue(extended.use_extra_features); self.assertEqual(extended.n_extra_descriptors, 8)
        self.assertFalse(spec.use_extra_features)


class WarmStartParity(unittest.TestCase):
    def test_700_and_2048_graph_columns_preserve_forward_and_accept_gradients(self):
        import torch
        from chemprop import data, models, nn
        from night.briford_native import defaults, runtime
        torch.set_num_threads(2); core = runtime(); hp = defaults()
        smiles = ['CCO', 'CCN', 'c1ccccc1']
        extra = np.asarray([[1., -1., .5, .1], [4., 2., .1, .2], [-2., .4, .7, .9]], dtype=np.float32)
        for width, depth, agg_cls in [(700, 5, nn.NormAggregation), (2048, 6, nn.MeanAggregation)]:
            with self.subTest(width=width):
                def build(n_extra):
                    mp = nn.BondMessagePassing(d_h=width, depth=depth, dropout=0. if width==2048 else .1)
                    out_transform = nn.UnscaleTransform([4., 5.], [1.5, .5])
                    pred = core.build_ffn('regression', width+n_extra, hp, None, 2, out_transform, np.ones(2))
                    transform = nn.ScaleTransform([1., .5, -.2, 0.], [2., 3., .5, 1.]) if n_extra else None
                    return models.MPNN(mp, agg_cls(), pred, batch_norm=True, X_d_transform=transform)
                torch.manual_seed(22); base = build(0).eval()
                with torch.no_grad():
                    base.bn.running_mean.copy_(torch.linspace(-.03, .03, width)); base.bn.running_var.fill_(.8)
                torch.manual_seed(103); extended = build(4).eval()
                before = {k: v.clone() for k, v in base.state_dict().items()}
                note = copy_graph_model_weights(base, extended)
                self.assertEqual(note['graph_width'], width)
                graph_dp, _ = core.create_molecule_datapoints(smiles)
                extra_dp, _ = core.create_molecule_datapoints(smiles, extra_descriptors=extra)
                graph_batch = next(iter(data.build_dataloader(data.MoleculeDataset(graph_dp), batch_size=3, shuffle=False, num_workers=0)))
                extra_batch = next(iter(data.build_dataloader(data.MoleculeDataset(extra_dp), batch_size=3, shuffle=False, num_workers=0)))
                with torch.no_grad():
                    p = base(*graph_batch[:3]); q = extended(*extra_batch[:3])
                torch.testing.assert_close(p, q, rtol=1e-6, atol=1e-6)
                for k, value in before.items(): torch.testing.assert_close(base.state_dict()[k], value, rtol=0, atol=0)
                weight = dict(extended.named_parameters())[note['expanded_weight']]
                self.assertTrue(torch.equal(weight[:, width:], torch.zeros_like(weight[:, width:])))
                extended(*extra_batch[:3]).sum().backward()
                self.assertTrue(torch.isfinite(weight.grad).all())
                self.assertGreater(float(weight.grad[:, width:].abs().sum()), 0.)
                self.assertEqual(extended.hparams['predictor']['input_dim'], width+4)
                self.assertTrue(all(p.requires_grad for p in extended.message_passing.parameters()))
                # Ordinary Chemprop reconstruction, not a state_dict-only reload.
                from chemprop.models.utils import save_model
                with tempfile.TemporaryDirectory() as tmp:
                    checkpoint = Path(tmp) / 'mock-feature-model.pt'
                    save_model(checkpoint, extended, output_columns=['mock_a', 'mock_b'])
                    restored = models.MPNN.load_from_file(checkpoint, map_location='cpu', strict=True).eval()
                    self.assertEqual(restored.predictor.input_dim, width+4)
                    self.assertEqual(restored.hparams['predictor']['input_dim'], width+4)
                    torch.testing.assert_close(restored.X_d_transform.mean, extended.X_d_transform.mean, rtol=0, atol=0)
                    with torch.no_grad():
                        restored_prediction = restored(*extra_batch[:3])
                    torch.testing.assert_close(restored_prediction, q, rtol=1e-6, atol=1e-6)

    def test_fresh_head_wrapper_preserves_graph_rng_and_initial_state(self):
        import torch
        from chemprop import nn
        from night.briford_native import defaults, runtime
        torch.set_num_threads(2); core = runtime(); hp = defaults()
        kwargs = {"n_targets": 4, "task_weights": np.ones(4),
                  "output_transform": nn.UnscaleTransform([4.] * 4, [1.] * 4)}
        torch.manual_seed(41); base = core.build_mpnn_model(hp, **kwargs)
        expected_rng = torch.random.get_rng_state().clone()
        torch.manual_seed(41)
        model, audit = build_with_zero_extended_fresh_head(core.build_mpnn_model, hp, **kwargs,
                          n_extra_descriptors=4, x_d_transform=nn.ScaleTransform([0.] * 4, [1.] * 4))
        self.assertTrue(torch.equal(torch.random.get_rng_state(), expected_rng))
        old = base.state_dict(); new = model.state_dict(); first = audit['expanded_weight']
        for k, value in old.items():
            if k == first: torch.testing.assert_close(value, new[k][:, :700], rtol=0, atol=0)
            else: torch.testing.assert_close(value, new[k], rtol=0, atol=0)
        self.assertEqual(audit['mode'], 'paired_fresh_head')


if __name__ == '__main__': unittest.main()
