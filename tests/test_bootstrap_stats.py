"""P2 bootstrap_stats targeted tests (zero model calls)."""
import unittest
import tools.bootstrap_stats as BS


def rec(cid, accepted=True, match=True, jd='fail', hd='fail', sev_miss=False, fa=False, exact=5, comp=5, sign=5):
    r = {'case_id': cid, 'split': 'development', 'judge_status': 'accepted' if accepted else 'error',
         'judge_decision': jd, 'human_decision': hd, 'decision_match': match,
         'severe_miss': sev_miss, 'false_alarm': fa,
         'dimensions': {d: {'comparable': comp > 0, 'exact': exact > 0, 'severity_sign_match': sign > 0}
                        for d in BS.DIMS}}
    return r


class BootstrapTests(unittest.TestCase):
    def test_mcnemar_known(self):
        self.assertEqual(BS._mcnemar_exact(0, 0), 1.0)
        self.assertAlmostEqual(BS._mcnemar_exact(5, 0), 2 * (0.5 ** 5), places=6)
        self.assertEqual(BS._mcnemar_exact(3, 3), 1.0)

    def test_decision_match_rate(self):
        recs = [rec('a', match=True), rec('b', match=False), rec('c', accepted=False)]
        self.assertAlmostEqual(BS.m_decision_match(recs), 0.5)

    def test_reject_rate(self):
        recs = [rec('a'), rec('b', accepted=False)]
        self.assertAlmostEqual(BS.m_reject(recs), 0.5)

    def test_kappa_perfect(self):
        recs = [rec('a', jd='fail', hd='fail'), rec('b', jd='pass', hd='pass'), rec('c', jd='uncertain', hd='uncertain')]
        self.assertAlmostEqual(BS.m_kappa(recs), 1.0)

    def test_bootstrap_deterministic(self):
        recs = [rec('a', match=True), rec('b', match=False), rec('c', match=True), rec('d', match=False)]
        c1 = BS.bootstrap_ci(recs, BS.m_decision_match, 500, 42)
        c2 = BS.bootstrap_ci(recs, BS.m_decision_match, 500, 42)
        self.assertEqual(c1, c2)
        self.assertEqual(c1['point'], 0.5)
        lo, hi = c1['ci95']
        self.assertLessEqual(lo, 0.5); self.assertGreaterEqual(hi, 0.5)
        self.assertLessEqual(lo, hi)

    def test_bootstrap_all_match_boundary(self):
        recs = [rec('a'), rec('b'), rec('c')]
        c = BS.bootstrap_ci(recs, BS.m_decision_match, 200, 1)
        self.assertEqual(c['point'], 1.0)
        self.assertEqual(c['ci95'], [1.0, 1.0])  # boundary: all successes

    def test_paired_mcnemar(self):
        A = [rec('a', match=True), rec('b', match=True), rec('c', match=False)]
        B = [rec('a', match=True), rec('b', match=False), rec('c', match=False)]
        p = BS.paired(A, B, 300, 7)
        self.assertEqual(p['common_accepted'], 3)
        self.assertEqual(p['A_correct_B_wrong'], 1)
        self.assertEqual(p['A_wrong_B_correct'], 0)
        self.assertAlmostEqual(p['match_diff_A_minus_B'], 1 / 3, places=3)

    def test_dev_only_filter(self):
        batch = {'cases': [
            {'case_id': 'a', 'split': 'development', 'report': {'status': 'accepted', 'assessment': {'decision': 'fail', 'dimensions': {d: {'score': 2, 'status': 'scored', 'severity': 'major'} for d in BS.DIMS}}}},
            {'case_id': 'z', 'split': 'frozen_test', 'report': {'status': 'accepted', 'assessment': {'decision': 'fail', 'dimensions': {d: {'score': 2, 'status': 'scored', 'severity': 'major'} for d in BS.DIMS}}}}]}
        gold = {'cases': [{'case_id': 'a', 'decision': 'fail', 'dimensions': {d: {'score': 2, 'severity': 'major'} for d in BS.DIMS}}]}
        recs = BS._records(batch, BS._gold_map(gold), 'nonexistent_dir')
        self.assertEqual([r['case_id'] for r in recs], ['a'])


if __name__ == '__main__':
    unittest.main()
