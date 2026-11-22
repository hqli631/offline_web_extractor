# -*- coding: utf-8 -*-
"""Unit tests for tools/check_p3_dev_guard.py pure logic (offline)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.check_p3_dev_guard import guard_checks

CFG_DEV = {'reject_rate_lt': 0.10, 'severe_miss_count_le': 1, 'false_alarm_rate_le': 0.15}


def rec(cid, status='accepted', match=True, severe=False, alarm=False,
        human='uncertain', judge='uncertain'):
    return {'case_id': cid, 'split': 'development', 'judge_status': status,
            'decision_match': match, 'severe_miss': severe, 'false_alarm': alarm,
            'human_decision': human, 'judge_decision': judge,
            'dimensions': {}}


class GuardTests(unittest.TestCase):
    def test_pass_clean(self):
        pooled = [rec('c%d' % i) for i in range(18)]
        g = guard_checks(pooled, pooled[:12], CFG_DEV)
        self.assertEqual(g['verdict'], 'GUARD_PASS')

    def test_fail_reject(self):
        pooled = [rec('c%d' % i, status='error' if i < 2 else 'accepted') for i in range(18)]
        g = guard_checks(pooled, pooled[:12], CFG_DEV)
        self.assertEqual(g['verdict'], 'GUARD_FAIL')

    def test_fail_severe_miss(self):
        pooled = [rec('c%d' % i, severe=i < 2) for i in range(18)]
        g = guard_checks(pooled, pooled[:12], CFG_DEV)
        self.assertEqual(g['verdict'], 'GUARD_FAIL')

    def test_fail_false_alarm_boundary(self):
        pooled = [rec('c%d' % i, alarm=i < 3) for i in range(18)]  # 3/18 = 0.1667 > 0.15
        g = guard_checks(pooled, pooled[:12], CFG_DEV)
        self.assertEqual(g['verdict'], 'GUARD_FAIL')
        pooled2 = [rec('c%d' % i, alarm=i < 2) for i in range(18)]  # 2/18 = 0.111 <= 0.15
        self.assertEqual(guard_checks(pooled2, pooled2[:12], CFG_DEV)['verdict'], 'GUARD_PASS')

    def test_empty_pool_fails(self):
        g = guard_checks([], [], CFG_DEV)
        self.assertEqual(g['verdict'], 'GUARD_FAIL')


if __name__ == '__main__':
    unittest.main()
