# -*- coding: utf-8 -*-
"""P-H H2 tests: 32x4 banding recall fix, freeze discipline, CLI (zero calls)."""
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.webextractor.dom_lsh import minhash_signature, lsh_candidate_pairs
from tools import run_ph_cluster as phc


class BandingTests(unittest.TestCase):
    def test_params_product_matches_signature(self):
        self.assertEqual(phc.PARAMS['bands'] * phc.PARAMS['rows'], phc.PARAMS['num_perm'])
        self.assertEqual((phc.PARAMS['bands'], phc.PARAMS['rows']), (32, 4))

    def test_protocol_unchanged_except_banding(self):
        from tools import run_pg_cluster as pgc
        for key in ('feature_mode', 'threshold', 'num_perm', 'seed', 'drift_threshold'):
            self.assertEqual(phc.PARAMS[key], pgc.PARAMS[key])

    def test_near_threshold_recall_improved(self):
        rng = random.Random(20261124)
        sigs, exact_pos = {}, set()
        ids = ['p%02d' % i for i in range(24)]
        sets = {}
        universe = ['f%d' % i for i in range(2000)]
        for i, pid in enumerate(ids):
            if i % 2 == 1:
                partner = ids[i - 1]
                base = sets[partner]
                keep = rng.sample(sorted(base), 70)
                extra = rng.sample(universe[1000:], 30)
                sets[pid] = set(keep) | set(extra)
                exact_pos.add((partner, pid))
            else:
                sets[pid] = set(rng.sample(universe[:1000], 100))
        for pid in ids:
            sigs[pid] = minhash_signature(sets[pid], 128, 20261123)
        old = lsh_candidate_pairs(sigs, 16, 8)
        new = lsh_candidate_pairs(sigs, 32, 4)
        old_recall = len(old & exact_pos) / len(exact_pos)
        new_recall = len(new & exact_pos) / len(exact_pos)
        self.assertGreaterEqual(new_recall, 0.9)
        self.assertGreaterEqual(new_recall, old_recall)


class FreezeTests(unittest.TestCase):
    def test_freeze_requires_approval_quote(self):
        with self.assertRaises(ValueError):
            phc.make_freeze(None)
        with self.assertRaises(ValueError):
            phc.make_freeze('   ')

    def test_freeze_and_check(self):
        fz = phc.make_freeze('unit-test approval')
        self.assertEqual(fz['freeze_version'], 'ph-cluster-1')
        self.assertEqual(fz['params']['bands'], 32)
        self.assertEqual(phc.check_freeze(fz), [])
        bad = dict(fz)
        bad['plan_sha256'] = '0' * 64
        self.assertTrue(any('plan drift' in p for p in phc.check_freeze(bad)))

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'exists.json'
            out.write_text('{}', encoding='utf-8')
            self.assertEqual(phc.main(['--run', '--output', str(out)]), 3)
            fz = Path(td) / 'freeze.json'
            fz.write_text('{}', encoding='utf-8')
            self.assertEqual(phc.main(['--freeze', '--freeze-path', str(fz),
                                       '--approval-quote', 'x']), 3)


if __name__ == '__main__':
    unittest.main()
