"""Checks label masking, policy fitting boundaries, and native numerical parity."""
import inspect
import json
import unittest
import numpy as np
from tdi.evaluation import (TARGETS, THRESHOLDS, score, optimize_threshold,
                            fit_policy, apply_policy, fit_native_policy)


class EvaluationTests(unittest.TestCase):
    def test_masked_confusion_and_macro(self):
        y = np.array([[1, 0], [0, 1], [1, np.nan], [np.nan, 0.]])
        p = np.array([[1, 0], [0, 0], [0, np.nan], [np.nan, 1.]])
        got = score(y, p)
        self.assertAlmostEqual(got['per_target'][TARGETS[0]]['mcc'], .5)
        self.assertAlmostEqual(got['per_target'][TARGETS[1]]['mcc'], -.5)
        self.assertEqual(got['macro_mcc'], 0)
        self.assertEqual(got['per_target'][TARGETS[0]]['fn'], 1)
        self.assertEqual(got['per_target'][TARGETS[0]]['n'], 3)

    def test_constant_and_absent_task(self):
        y = np.array([[0, 1], [1, 0.]])
        self.assertEqual(score(y, np.zeros_like(y))['macro_mcc'], 0)
        y[:, 1] = np.nan
        self.assertIsNone(score(y, np.zeros_like(y))['macro_mcc'])
        with self.assertRaises(ValueError):
            score([[0, 2]], [[0, 1]])
        with self.assertRaises(ValueError):
            score([[0, 1]], [[.3, 1]])

    def test_threshold_native_ties_and_missing(self):
        result = optimize_threshold([0, 1, np.nan], [.5, .5, np.nan])
        self.assertEqual(result['threshold'], THRESHOLDS[0])
        self.assertEqual(result['mcc'], 0)
        result = optimize_threshold([0, 1], [.101, .102], exact=True)
        self.assertEqual(result['mcc'], 1)
        with self.assertRaises(ValueError):
            optimize_threshold([0, 1], [.1, np.nan])

    @staticmethod
    def example():
        y = np.tile([[0., 1.], [1., 0.]], (6, 1))
        folds = np.repeat([0, 1, 2], 4)
        return y, folds, {'good': .15 + .7 * y, 'bad': .85 - .7 * y}

    def test_crossfit_policy_json_ids_and_query_isolation(self):
        y, folds, oof = self.example(); ids = [f'mol{i}' for i in range(len(y))]
        before = {k: v.copy() for k, v in oof.items()}
        policy = fit_policy(oof, y, folds, ids=ids)
        self.assertEqual(policy['selection_input']['ids'], ids)
        self.assertEqual(policy['selection_metrics']['macro_mcc'], 1)
        self.assertFalse(policy['outer_labels_used'])
        restored = json.loads(json.dumps(policy, allow_nan=False))
        expected = apply_policy(oof, restored)
        np.testing.assert_array_equal(expected, y.astype(bool))
        self.assertNotIn('y', inspect.signature(apply_policy).parameters)
        self.assertNotIn('querydict', inspect.signature(fit_policy).parameters)
        with self.assertRaises(TypeError):
            apply_policy(oof, policy, y=y)
        with self.assertRaises(ValueError):
            fit_policy(oof, y, folds, ids=['duplicate'] * len(y))
        with self.assertRaises(ValueError):
            apply_policy({'good': oof['good']}, policy)
        for name in oof:
            np.testing.assert_array_equal(oof[name], before[name])

    def test_masked_oof_and_fold_safety(self):
        y, folds, oof = self.example(); y[0, 0] = np.nan
        for v in oof.values(): v[0, 0] = np.nan
        policy = fit_policy(oof, y, folds)
        self.assertEqual(policy['selection_metrics']['per_target'][TARGETS[0]]['n'], 11)
        with self.assertRaises(ValueError):
            fit_policy(oof, y, np.zeros(len(y)))
        broken = {k: v.copy() for k, v in oof.items()}; broken['good'][1, 0] = np.nan
        with self.assertRaises(ValueError):
            fit_policy(broken, y, folds)

    def test_native_function_injection(self):
        y, _, oof = self.example(); calls = []
        def native(x, yy, score_fn, *, minimize, seed):
            calls.append((minimize, seed, yy.dtype))
            self.assertEqual(score_fn(yy, x[:, 0]), 1)
            return np.array([1., 0.])
        policy = fit_native_policy(oof, y, caruana_fn=native)
        self.assertEqual(policy['selection_metrics']['macro_mcc'], 1)
        self.assertEqual(len(calls), 2)
        self.assertFalse(calls[0][0])
        self.assertEqual(calls[0][1], 42)

    def test_mcc_matches_sklearn_if_available(self):
        try:
            from sklearn.metrics import matthews_corrcoef
        except ImportError:
            self.skipTest('sklearn unavailable')
        rng = np.random.default_rng(123)
        for n in (2, 7, 100):
            for _ in range(10):
                y = rng.integers(0, 2, (n, 2)); p = rng.integers(0, 2, (n, 2))
                result = score(y, p)
                for j, t in enumerate(TARGETS):
                    self.assertAlmostEqual(result['per_target'][t]['mcc'], matthews_corrcoef(y[:, j], p[:, j]))


if __name__ == '__main__':
    unittest.main()
