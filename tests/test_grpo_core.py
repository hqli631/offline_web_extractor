# -*- coding: utf-8 -*-
"""P-H H4 tests: GRPO core math, tabular policy, offline dry-run (zero calls)."""
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.webextractor import grpo_core as gc
from tools import run_grpo_dryrun as dry


class AdvantageTests(unittest.TestCase):
    def test_zero_mean_unit_std(self):
        advs, stats = gc.group_advantages([1.0, 0.5, -0.5, -1.0])
        self.assertAlmostEqual(sum(advs) / 4, 0.0, places=12)
        self.assertAlmostEqual(math.sqrt(sum(a * a for a in advs) / 4), 1.0, places=12)
        self.assertFalse(stats['degenerate'])

    def test_degenerate_group(self):
        advs, stats = gc.group_advantages([0.5, 0.5, 0.5])
        self.assertEqual(advs, [0.0, 0.0, 0.0])
        self.assertTrue(stats['degenerate'])

    def test_invalid(self):
        for bad in ([], [True], [float('nan')], 'x'):
            with self.assertRaises(ValueError):
                gc.group_advantages(bad)


class ObjectiveTests(unittest.TestCase):
    def test_kl_nonnegative(self):
        for lp, rlp in ((0.0, 0.0), (-1.0, -0.5), (-2.0, -3.0)):
            self.assertGreaterEqual(gc.kl_k3(lp, rlp), 0.0)
        self.assertEqual(gc.kl_k3(-1.0, -1.0), 0.0)

    def test_clip_caps_positive_advantage(self):
        val = gc.clipped_surrogate(math.log(5.0), 0.0, 1.0, clip_eps=0.2)
        self.assertAlmostEqual(val, 1.2)

    def test_min_semantics_negative_advantage(self):
        # min(ratio*A, clip(ratio)*A): A<0, ratio=5 -> min(-5, -1.2) = -5
        val = gc.clipped_surrogate(math.log(5.0), 0.0, -1.0, clip_eps=0.2)
        self.assertAlmostEqual(val, -5.0)
        val2 = gc.clipped_surrogate(math.log(0.5), 0.0, -1.0, clip_eps=0.2)
        self.assertAlmostEqual(val2, -0.8)  # ratio below clip: min(-0.5, -0.8) = -0.8

    def test_objective_length_mismatch(self):
        with self.assertRaises(ValueError):
            gc.grpo_objective([0.0], [], [0.0], [1.0])
        with self.assertRaises(ValueError):
            gc.grpo_objective([], [], [], [])

    def test_softmax_sums_to_one(self):
        self.assertAlmostEqual(sum(gc.softmax([1.0, 2.0, 3.0])), 1.0, places=12)


class PolicyTests(unittest.TestCase):
    def test_deterministic_sampling(self):
        p1, p2 = gc.TabularPolicy(4, 7), gc.TabularPolicy(4, 7)
        g1 = p1.sample_group(8, random.Random(7))
        g2 = p2.sample_group(8, random.Random(7))
        self.assertEqual(g1, g2)

    def test_update_moves_logits(self):
        p = gc.TabularPolicy(3)
        p.update([0, 2], [1.0, -1.0], lr=0.5)
        self.assertEqual(p.logits, [0.5, 0.0, -0.5])
        self.assertGreater(p.probs()[0], p.probs()[2])

    def test_invalid_actions(self):
        with self.assertRaises(ValueError):
            gc.TabularPolicy(0)


class DryRunTests(unittest.TestCase):
    def test_ready_and_deterministic(self):
        a, b = dry.run_dry(), dry.run_dry()
        self.assertEqual(a['verdict'], 'GRPO_PLUMBING_READY')
        self.assertTrue(all(a['checks'].values()))
        self.assertEqual(a['step_rows'], b['step_rows'])
        self.assertEqual(a['action_rewards'], [1.0, 0.5, -1.0, -1.0])
        self.assertEqual(a['mapping_version'], '1.0.0')

    def test_policy_moves_to_best(self):
        r = dry.run_dry()
        self.assertGreater(r['probability_trajectory'][-1][0], r['probability_trajectory'][0][0])

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'x.json'
            out.write_text('{}', encoding='utf-8')
            self.assertEqual(dry.main(['--dry-out', str(out), '--audit-out', str(Path(td) / 'a.json')]), 3)


if __name__ == '__main__':
    unittest.main()
