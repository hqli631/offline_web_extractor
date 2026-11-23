# -*- coding: utf-8 -*-
import unittest
from src.webextractor import dom_lsh as L


class DomLshTest(unittest.TestCase):
    def test_determinism(self):
        f = ['a', 'b', 'c']
        self.assertEqual(L.minhash_signature(f, seed=1), L.minhash_signature(f, seed=1))

    def test_seed_changes_signature(self):
        f = ['a', 'b', 'c']
        self.assertNotEqual(L.minhash_signature(f, seed=1), L.minhash_signature(f, seed=2))

    def test_identical_sets_identical_signature(self):
        self.assertEqual(L.minhash_signature(['a', 'b']), L.minhash_signature(['b', 'a', 'a']))

    def test_empty_sentinel(self):
        s = L.minhash_signature([], num_perm=16)
        self.assertEqual(len(s), 16)
        self.assertTrue(all(x == L.MAX_HASH for x in s))

    def test_invalid_num_perm(self):
        with self.assertRaises(ValueError):
            L.minhash_signature(['a'], num_perm=0)

    def test_bands_rows_validation(self):
        sigs = {'a': L.minhash_signature(['x'], num_perm=16)}
        with self.assertRaises(ValueError):
            L.lsh_candidate_pairs(sigs, bands=3, rows=8)

    def test_length_mismatch(self):
        sigs = {'a': (1, 2), 'b': (1, 2, 3)}
        with self.assertRaises(ValueError):
            L.lsh_candidate_pairs(sigs, bands=1, rows=2)

    def test_high_similarity_recall_and_separation(self):
        A = {'f%d' % i for i in range(20)}
        B = {'f%d' % i for i in range(19)} | {'f20'}
        C = {'g%d' % i for i in range(20)}
        sigs = {k: L.minhash_signature(v, num_perm=128, seed=20261123)
                for k, v in (('A', A), ('B', B), ('C', C))}
        pairs = L.lsh_candidate_pairs(sigs, bands=16, rows=8)
        self.assertIn(('A', 'B'), pairs)
        self.assertNotIn(('A', 'C'), pairs)
        self.assertNotIn(('B', 'C'), pairs)
        self.assertLessEqual(len(pairs), 3)

    def test_empty_signatures(self):
        self.assertEqual(L.lsh_candidate_pairs({}, 16, 8), set())

    def test_estimated_jaccard_identical(self):
        s = L.minhash_signature(['a', 'b', 'c'])
        self.assertEqual(L.estimated_jaccard(s, s), 1.0)


if __name__ == '__main__':
    unittest.main()
