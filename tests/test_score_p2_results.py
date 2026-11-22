# -*- coding: utf-8 -*-
"""Unit tests for tools/score_p2_results.py pure logic (offline)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.score_p2_results import (generalization_acceptance, unpaired_diff_ci,
                                    status_artifact, all_split_records, THRESHOLDS)
from tools.bootstrap_stats import m_decision_match


def rec(cid, split, match, judge_status='accepted', severe_miss=False, false_alarm=False,
        human_status='scored', judge_status_dim='scored'):
    return {'case_id': cid, 'split': split, 'judge_status': judge_status,
            'decision_match': match, 'judge_decision': 'uncertain', 'human_decision': 'uncertain',
            'severe_miss': severe_miss, 'false_alarm': false_alarm,
            'dimensions': {'completeness': {'human_status': human_status, 'judge_status': judge_status_dim,
                                            'comparable': True, 'exact': True, 'within1': True,
                                            'severity_sign_match': True}}}


class AcceptanceTests(unittest.TestCase):
    def test_accept_clean(self):
        dev = [rec('d%d' % i, 'development', True) for i in range(6)]
        test = [rec('t%d' % i, 'frozen_test', True) for i in range(12)]
        acc = generalization_acceptance(dev, test, B=500, seed=7)
        self.assertEqual(acc['verdict'], 'ACCEPT')
        self.assertFalse(acc['overfit_flag'])
        self.assertEqual(acc['reject_rate'], 0.0)

    def test_reject_high_reject_rate(self):
        dev = [rec('d%d' % i, 'development', True) for i in range(6)]
        test = [rec('t%d' % i, 'frozen_test', True, judge_status='error') for i in range(2)] + \
               [rec('t%d' % i, 'frozen_test', True) for i in range(2, 12)]
        acc = generalization_acceptance(dev, test, B=200, seed=7)
        self.assertEqual(acc['verdict'], 'REJECT')
        self.assertFalse(acc['checks']['reject_rate_lt_0.10'])

    def test_reject_severe_miss(self):
        dev = [rec('d%d' % i, 'development', True) for i in range(6)]
        test = [rec('t0', 'frozen_test', True, severe_miss=True), rec('t1', 'frozen_test', True, severe_miss=True)] + \
               [rec('t%d' % i, 'frozen_test', True) for i in range(2, 12)]
        acc = generalization_acceptance(dev, test, B=200, seed=7)
        self.assertEqual(acc['verdict'], 'REJECT')
        self.assertEqual(acc['severe_miss_count'], 2)

    def test_overfit_flag_large_drop(self):
        dev = [rec('d%d' % i, 'development', True) for i in range(6)]
        test = [rec('t%d' % i, 'frozen_test', i < 3) for i in range(12)]  # match 0.25 vs 1.0
        acc = generalization_acceptance(dev, test, B=2000, seed=7)
        self.assertTrue(acc['overfit_flag'])
        self.assertTrue(acc['dev_minus_test_match']['excludes_zero'])
        self.assertGreater(acc['dev_minus_test_match']['diff_A_minus_B'], THRESHOLDS['overfit_drop_gt'])

    def test_small_drop_no_flag(self):
        dev = [rec('d%d' % i, 'development', i < 5) for i in range(6)]
        test = [rec('t%d' % i, 'frozen_test', i < 10) for i in range(12)]
        acc = generalization_acceptance(dev, test, B=2000, seed=7)
        self.assertFalse(acc['overfit_flag'])

    def test_unpaired_ci_deterministic(self):
        a = [rec('d%d' % i, 'development', i < 4) for i in range(6)]
        b = [rec('t%d' % i, 'frozen_test', i < 8) for i in range(12)]
        c1 = unpaired_diff_ci(a, b, m_decision_match, 500, 42)
        c2 = unpaired_diff_ci(a, b, m_decision_match, 500, 42)
        self.assertEqual(c1, c2)
        self.assertAlmostEqual(c1['diff_A_minus_B'], round(4/6 - 8/12, 4))

    def test_status_artifact_counts(self):
        rows = [rec('x', 'development', True, human_status='scored', judge_status_dim='partial'),
                rec('y', 'development', True, human_status='partial', judge_status_dim='partial')]
        self.assertEqual(status_artifact(rows)['human_scored_judge_partial_dims'], 1)

    def test_all_split_records_keeps_test(self):
        batch = {'cases': [
            {'case_id': 'c1', 'split': 'development', 'report': {'status': 'accepted', 'assessment': {
                'decision': 'uncertain', 'dimensions': {n: {'score': 4, 'status': 'partial', 'severity': 'none'} for n in
                ('completeness', 'cleanliness', 'structure', 'title', 'format')}}}},
            {'case_id': 'c2', 'split': 'frozen_test', 'report': {'status': 'accepted', 'assessment': {
                'decision': 'uncertain', 'dimensions': {n: {'score': 4, 'status': 'partial', 'severity': 'none'} for n in
                ('completeness', 'cleanliness', 'structure', 'title', 'format')}}}}]}
        gm = {cid: {'decision': 'uncertain', 'dimensions': {n: {'score': 4, 'status': 'partial', 'severity': 'none', 'note': ''} for n in
              ('completeness', 'cleanliness', 'structure', 'title', 'format')}} for cid in ('c1', 'c2')}
        recs = all_split_records(batch, gm, Path('nonexistent_silver_dir'))
        self.assertEqual(len(recs), 2)
        self.assertEqual({r['split'] for r in recs}, {'development', 'frozen_test'})


if __name__ == '__main__':
    unittest.main()
