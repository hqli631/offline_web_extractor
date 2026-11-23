# -*- coding: utf-8 -*-
import unittest
from pathlib import Path
from src.webextractor import rule_cache as R
from src.webextractor.dom_similarity import structural_features

ROOT = Path(__file__).resolve().parents[1]


def src(name):
    return (ROOT / 'samples/drift_lab' / (name + '.html')).read_bytes()


def feats(name):
    return structural_features(src(name), 'full-counts')


class RuleCacheTest(unittest.TestCase):
    def setUp(self):
        self.rule = R.derive_shared_rule(src('reference'))

    def test_derive_reference_rule(self):
        self.assertIsNotNone(self.rule)
        self.assertEqual(self.rule['container_xpath'], "//*[@role='main']")
        self.assertEqual(self.rule['version'], 1)

    def test_derive_sphinx_rule(self):
        s = (ROOT / 'samples/python_appetite_zh.html').read_bytes()
        self.assertIsNotNone(R.derive_shared_rule(s))

    def test_derive_no_container_returns_none(self):
        self.assertIsNone(R.derive_shared_rule(b'<html><body><p>tiny</p></body></html>'))

    def test_apply_reference_ok(self):
        res = R.apply_rule(src('reference'), self.rule)
        self.assertEqual(res['status'], 'ok')
        self.assertGreater(res['block_count'], 0)
        self.assertEqual(res['match_count'], 1)

    def test_apply_role_drift_no_match(self):
        res = R.apply_rule(src('role-drift'), self.rule)
        self.assertEqual(res['status'], 'rule_no_match')

    def test_apply_duplicate_main_ambiguous(self):
        res = R.apply_rule(src('duplicate-main'), self.rule)
        self.assertEqual(res['status'], 'rule_ambiguous')

    def test_cache_class_drift_reuse(self):
        cache = R.ClusterRuleCache(0.7)
        cache.derive_and_cache('c0', 'reference', src('reference'), feats('reference'))
        out = cache.reuse_member('c0', 'class-drift', src('class-drift'), feats('class-drift'))
        self.assertTrue(out['reuse'])
        self.assertFalse(out['drift'])
        self.assertEqual(out['fingerprint_similarity'], 1.0)

    def test_cache_role_drift_fallback_via_rule_failure(self):
        cache = R.ClusterRuleCache(0.7)
        cache.derive_and_cache('c0', 'reference', src('reference'), feats('reference'))
        out = cache.reuse_member('c0', 'role-drift', src('role-drift'), feats('role-drift'))
        self.assertFalse(out['reuse'])
        self.assertTrue(out['fallback'])
        self.assertTrue(out['drift'])
        self.assertIn('rule_failure', out['drift_reasons'])
        # tag-path fingerprint cannot see attribute drift: similarity stays high
        self.assertGreaterEqual(out['fingerprint_similarity'], 0.7)
        self.assertNotIn('fingerprint_drift', out['drift_reasons'])

    def test_cache_duplicate_main_fallback(self):
        cache = R.ClusterRuleCache(0.7)
        cache.derive_and_cache('c0', 'reference', src('reference'), feats('reference'))
        out = cache.reuse_member('c0', 'duplicate-main', src('duplicate-main'), feats('duplicate-main'))
        self.assertTrue(out['fallback'])
        self.assertTrue(out['drift'])

    def test_fallback_extract(self):
        out = R.fallback_extract(src('role-drift'))
        self.assertIsNotNone(out['extraction'])

    def test_fingerprint_determinism(self):
        f = feats('reference')
        self.assertEqual(R.cluster_fingerprint(f), R.cluster_fingerprint(f))

    def test_invalid_drift_threshold(self):
        with self.assertRaises(ValueError):
            R.ClusterRuleCache(1.5)

    def test_no_shared_rule_fallback(self):
        cache = R.ClusterRuleCache(0.7)
        cache.derive_and_cache('c0', 'reference', b'<html><body><p>x</p></body></html>', feats('reference'))
        out = cache.reuse_member('c0', 'reference', src('reference'), feats('reference'))
        self.assertTrue(out['fallback'])
        self.assertIn('no_shared_rule', out['drift_reasons'])


if __name__ == '__main__':
    unittest.main()
