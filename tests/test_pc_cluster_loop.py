# -*- coding: utf-8 -*-
"""P-C closed-loop harness tests: determinism, anti-chaining invariant, honest
drift/fallback behavior on drift_lab, feature-mode ablation, output discipline.
Zero model calls, zero network (local frozen snapshots only)."""
import json
import tempfile
import unittest
from itertools import combinations
from pathlib import Path

from tools import run_pc_cluster_loop as H
from src.webextractor.dom_cluster import pairwise_similarity

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / 'samples/dom_similarity.expanded_development.json'
CONTROLLED = ROOT / 'samples/dom_similarity.controlled.json'
DRIFT_LAB = ROOT / 'samples/drift_lab'


class PcClusterLoopTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real_pages = H.load_pages(REAL)
        cls.ctrl_pages = H.load_pages(CONTROLLED)
        cls.real = H.run_corpus(cls.real_pages, REAL)
        cls.ctrl = H.run_corpus(cls.ctrl_pages, CONTROLLED, expected_dir=DRIFT_LAB)
        cls.ctrl_members = {m['member_id']: m for m in cls.ctrl['members']}

    def test_real_determinism(self):
        again = H.run_corpus(H.load_pages(REAL), REAL)
        self.assertEqual(self.real, again)

    def test_real_anti_chaining_invariant(self):
        cl = self.real['complete_linkage']
        self.assertEqual(cl['anti_chaining_violations'], [])
        sim = pairwise_similarity({p['id']: p['features'] for p in self.real_pages})
        for cluster in cl['clusters']:
            for a, b in combinations(sorted(cluster), 2):
                self.assertGreaterEqual(sim[(a, b)], H.PARAMS['threshold'])

    def test_real_primary_purity_regression(self):
        # Pre-registered primary (full-counts/0.7/CL): honest weak recall, perfect precision.
        pu = self.real['cluster_purity']
        self.assertEqual(pu['pair_precision'], 1.0)
        self.assertEqual(pu['pair_recall'], 0.076923)
        self.assertEqual(pu['tp'], 1)
        self.assertEqual(pu['true_same_pairs'], 13)

    def test_real_lsh_candidate_filter(self):
        lsh = self.real['lsh']
        self.assertEqual(lsh['candidate_recall_of_exact_positives'], 1.0)
        self.assertLess(lsh['candidate_pairs'], lsh['full_pairs'])

    def test_controlled_role_drift_rule_failure_fallback(self):
        m = self.ctrl_members['role-drift']
        # Fingerprint cannot see attribute drift (tags identical) ...
        self.assertGreaterEqual(m['fingerprint_similarity'], 0.7)
        # ... but rule execution failure triggers drift + fallback.
        self.assertTrue(m['drift'])
        self.assertEqual(m['drift_reasons'], ['rule_failure'])
        self.assertTrue(m['fallback'])
        self.assertFalse(m['reuse'])
        # Honest negative: fallback triggered != fallback recovered. The heuristic
        # candidate selectors do not cover role="article"/article-shell.
        self.assertEqual(m['final_status'], 'no_candidate')
        self.assertEqual(m['block_count'], 0)

    def test_controlled_duplicate_main_fallback_recovers(self):
        m = self.ctrl_members['duplicate-main']
        self.assertEqual(m['drift_reasons'], ['no_shared_rule'])
        self.assertTrue(m['fallback'])
        self.assertTrue(m['quality']['blocks_exact'])
        self.assertEqual(m['quality']['block_text_recall'], 1.0)

    def test_controlled_content_moved_unique_not_complete(self):
        m = self.ctrl_members['content-moved']
        # Unique rule match + status ok is NOT content completeness.
        self.assertTrue(m['reuse'])
        self.assertEqual(m['rule_status'], 'ok')
        self.assertFalse(m['quality']['blocks_exact'])
        self.assertLess(m['quality']['block_text_recall'], 1.0)

    def test_controlled_class_drift_reuse(self):
        m = self.ctrl_members['class-drift']
        self.assertTrue(m['reuse'])
        self.assertFalse(m['drift'])
        self.assertTrue(m['quality']['blocks_exact'])

    def test_feature_mode_override_changes_features(self):
        presence = H.load_pages(REAL, feature_mode='full-presence')
        diffs = [a['id'] for a, b in zip(self.real_pages, presence)
                 if a['features'] != b['features']]
        self.assertTrue(diffs)

    def test_ablation_suffix_presence_recovers_families(self):
        pages = H.load_pages(REAL, feature_mode='suffix-presence')
        r = H.run_corpus(pages, REAL, params={**H.PARAMS, 'feature_mode': 'suffix-presence'})
        clusters = r['complete_linkage']['clusters']
        iana = {'iana', 'iana-abuse', 'iana-whois'}
        self.assertTrue(any(iana <= set(c) for c in clusters))
        # Same-site negative stays out of the documentation clusters.
        for c in clusters:
            if 'python-search' in c:
                self.assertEqual(c, ['python-search'])
        self.assertEqual(r['complete_linkage']['anti_chaining_violations'], [])
        self.assertEqual(r['rule_reuse']['reuse_rate'], 1.0)
        self.assertGreater(r['cluster_purity']['pair_recall'],
                           self.real['cluster_purity']['pair_recall'])

    def test_output_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'exists'
            out.mkdir()
            self.assertEqual(H.main(['--output', str(out)]), 3)

    def test_main_writes_primary_and_ablation_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'primary'
            self.assertEqual(H.main(['--output', str(out)]), 0)
            data = json.loads((out / 'pc_cluster_loop.json').read_text(encoding='utf-8'))
            self.assertEqual(data['params']['feature_mode'], 'full-counts')
            self.assertTrue((out / 'PC_CLUSTER_REPORT.md').exists())
            out2 = Path(td) / 'ablation'
            self.assertEqual(H.main(['--output', str(out2), '--ablation']), 0)
            ab = json.loads((out2 / 'pc_cluster_ablation.json').read_text(encoding='utf-8'))
            self.assertEqual(len(ab['modes']), 6)
            self.assertIn('NOT threshold tuning', ab['kind'])
            self.assertTrue((out2 / 'PC_CLUSTER_ABLATION_REPORT.md').exists())


if __name__ == '__main__':
    unittest.main()
