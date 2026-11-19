"""P2 compute_iaa targeted tests (zero model calls)."""
import unittest
import tools.compute_iaa as I


def lab(cid, decision, score=2, sev='major', blind=None):
    c = {'case_id': cid, 'decision': decision,
         'dimensions': {d: {'score': score, 'severity': sev} for d in I.DIMS}}
    if blind:
        c['blind_code'] = blind
    return c


class IaaTests(unittest.TestCase):
    def test_pairs_align_by_case_id(self):
        a = {'cases': [lab('a', 'fail'), lab('b', 'pass')]}
        b = {'cases': [lab('b', 'pass'), lab('a', 'fail')]}
        p = I._pairs(a, b)
        self.assertEqual([k for _, _, k in p], ['a', 'b'])

    def test_pairs_align_by_blind_code(self):
        a = {'cases': [lab('a', 'fail', blind='P01')]}
        b = {'cases': [lab('x', 'fail', blind='P01')]}
        a['cases'][0].pop('case_id'); b['cases'][0].pop('case_id')
        p = I._pairs(a, b)
        self.assertEqual(len(p), 1)

    def test_perfect_agreement(self):
        a = {'cases': [lab('a', 'fail'), lab('b', 'pass', 4, 'none'), lab('c', 'uncertain', 3, 'minor')]}
        b = {'cases': [lab('a', 'fail'), lab('b', 'pass', 4, 'none'), lab('c', 'uncertain', 3, 'minor')]}
        p = I._pairs(a, b)
        self.assertAlmostEqual(I.m_match(p), 1.0)
        self.assertAlmostEqual(I.m_kappa(p), 1.0)
        self.assertAlmostEqual(I.m_dim_exact(p), 1.0)

    def test_disagreement(self):
        a = {'cases': [lab('a', 'fail'), lab('b', 'pass')]}
        b = {'cases': [lab('a', 'uncertain'), lab('b', 'pass')]}
        p = I._pairs(a, b)
        self.assertAlmostEqual(I.m_match(p), 0.5)

    def test_bootstrap_deterministic(self):
        a = {'cases': [lab('a', 'fail'), lab('b', 'pass'), lab('c', 'fail'), lab('d', 'uncertain')]}
        b = {'cases': [lab('a', 'fail'), lab('b', 'uncertain'), lab('c', 'fail'), lab('d', 'uncertain')]}
        p = I._pairs(a, b)
        c1 = I.bootstrap_ci(p, I.m_match, 400, 9)
        c2 = I.bootstrap_ci(p, I.m_match, 400, 9)
        self.assertEqual(c1, c2)
        lo, hi = c1['ci95']
        self.assertLessEqual(lo, c1['point']); self.assertGreaterEqual(hi, c1['point'])


if __name__ == '__main__':
    unittest.main()
