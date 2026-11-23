# -*- coding: utf-8 -*-
import unittest
from collections import Counter
from src.webextractor import dom_cluster as C


class DomClusterTest(unittest.TestCase):
    def test_jaccard_identical(self):
        a = Counter({'x': 3, 'y': 1})
        self.assertEqual(C.multiset_jaccard(a, a), 1.0)

    def test_jaccard_disjoint(self):
        self.assertEqual(C.multiset_jaccard(Counter({'x': 1}), Counter({'y': 1})), 0.0)

    def test_jaccard_partial(self):
        a = Counter({'x': 2, 'y': 1})
        b = Counter({'x': 1, 'z': 1})
        # inter min(x)=1 ; union max(x)=2 + y1 + z1 = 4 -> 0.25
        self.assertEqual(C.multiset_jaccard(a, b), 0.25)

    def test_jaccard_empty(self):
        self.assertEqual(C.multiset_jaccard(Counter(), Counter()), 1.0)

    def test_chaining_counterexample(self):
        feats = {'A': Counter(), 'B': Counter(), 'C': Counter()}
        sim = {('A', 'B'): 0.8, ('A', 'C'): 0.5, ('B', 'C'): 0.8}
        res = C.complete_linkage(feats, 0.7, sim=sim)
        # complete-linkage must NOT chain {A,B,C}
        self.assertFalse(any(len(c) == 3 for c in res['clusters']))
        self.assertEqual(res['anti_chaining_violations'], [])
        sizes = sorted(len(c) for c in res['clusters'])
        self.assertEqual(sizes, [1, 2])

    def test_invariant_no_violations(self):
        feats = {'p%d' % i: Counter({'t%d' % j: 1 for j in range(i, i + 8)})
                 for i in range(6)}
        res = C.complete_linkage(feats, 0.5)
        self.assertEqual(res['anti_chaining_violations'], [])
        for d in res['cluster_diagnostics']:
            if d['size'] > 1:
                self.assertGreaterEqual(d['min_intra_similarity'], 0.5)

    def test_threshold_one_only_identical(self):
        feats = {'a': Counter({'x': 1}), 'b': Counter({'x': 1}), 'c': Counter({'y': 1})}
        res = C.complete_linkage(feats, 1.0)
        self.assertIn(['a', 'b'], res['clusters'])
        self.assertIn(['c'], res['clusters'])

    def test_threshold_zero_merges_all(self):
        feats = {'a': Counter({'x': 1}), 'b': Counter({'y': 1})}
        res = C.complete_linkage(feats, 0.0)
        self.assertEqual(len(res['clusters']), 1)

    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):
            C.complete_linkage({'a': Counter()}, 1.5)

    def test_merge_log(self):
        feats = {'a': Counter({'x': 1}), 'b': Counter({'x': 1})}
        res = C.complete_linkage(feats, 0.7)
        self.assertEqual(len(res['merges']), 1)
        self.assertEqual(res['merges'][0]['min_cross_similarity'], 1.0)


if __name__ == '__main__':
    unittest.main()
