# -*- coding: utf-8 -*-
"""Tests for tools/score_pf_dev.py (zero calls; sealed v1.2 dev batches as fixtures)."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.score_pf_dev import main, ROOT

INP = ROOT / 'outputs/pb.gate.inputs.v1'
GOLD = ROOT / 'outputs/pf.dev.gold.v2'


def base_args(out, cfg):
    return ['--gate-config', str(cfg),
            '--dev-batch', 'orig=' + str(INP / 'dev.orig.batch.json'),
            '--dev-gold', 'orig=' + str(GOLD / 'dev.orig.gold.json'),
            '--dev-freeze', 'orig=' + str(ROOT / 'outputs/rubrics_judge.node3.freeze.v4.json'),
            '--dev-manifest', 'orig=' + str(ROOT / 'samples/calibration_manifest.json'),
            '--dev-batch', 'p2=' + str(INP / 'dev.p2.batch.json'),
            '--dev-gold', 'p2=' + str(GOLD / 'dev.p2.gold.json'),
            '--dev-freeze', 'p2=' + str(ROOT / 'outputs/p2.freeze.v5.json'),
            '--dev-manifest', 'p2=' + str(ROOT / 'samples/p2_manifest.json'),
            '--output', str(out)]


class PfDevScoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / 'cal'
        cfg = json.loads((ROOT / 'outputs/pf.gate.config.v1.json').read_text(encoding='utf-8'))
        # fixture: sealed v1.2 batches require judge pin 1.2.0 (test-only copy)
        cfg['batch_config']['judge_version'] = '1.2.0'
        self.cfg = self.root / 'cfg.fixture.json'
        self.cfg.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')

    def test_happy_dual_track(self):
        args = base_args(self.out, self.cfg) + [
            '--mechanical-gold', 'orig=' + str(ROOT / 'outputs/human_review/final.v1/human_gold.final.json'),
            '--mechanical-gold', 'p2=' + str(ROOT / 'outputs/human_review/p2.gold.v1/human_gold.p2.blind.json')]
        self.assertEqual(main(args), 0)
        res = json.loads((self.out / 'pf.dev.json').read_text(encoding='utf-8'))
        self.assertEqual(res['dev_pooled']['aggregate']['n_cases'], 18)
        self.assertIn('6/18', res['circularity']['note'])
        self.assertEqual(len(res['circularity']['readjudicated_case_ids']), 3)
        self.assertIsNotNone(res['mechanical_track'])
        self.assertEqual(res['mechanical_track']['pooled']['aggregate']['n_cases'], 18)
        self.assertTrue((self.out / 'PF_DEV_SUMMARY.md').exists())

    def test_protocol_drift_rejected(self):
        # real pf config pins 1.4.0; sealed fixture batches are 1.2.0 -> fail closed
        args = base_args(self.out, ROOT / 'outputs/pf.gate.config.v1.json')
        self.assertEqual(main(args), 1)
        self.assertFalse(self.out.exists())

    def test_overwrite_refused(self):
        self.out.mkdir()
        self.assertEqual(main(base_args(self.out, self.cfg)), 3)

    def test_label_mismatch_rejected(self):
        args = base_args(self.out, self.cfg)
        args[args.index('--dev-gold') + 1] = 'wrong=' + str(GOLD / 'dev.orig.gold.json')
        self.assertEqual(main(args), 1)


if __name__ == '__main__':
    unittest.main()
