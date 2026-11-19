# -*- coding: utf-8 -*-
import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools.build_human_review_kit import build_kit
from tests.human_review_fixtures import make_fixture


def kit_args(fixture, output):
    p = fixture['paths']
    return argparse.Namespace(batch=p['batch'], stability=p['stability'],
                              freeze=p['freeze'], manifest=p['manifest'],
                              output=Path(output))


class BuildHumanReviewKitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fixture = make_fixture(self.root / 'fx')

    def tearDown(self):
        self.tmp.cleanup()

    def test_deterministic_bytes(self):
        out1, out2 = self.root / 'o1', self.root / 'o2'
        self.assertEqual(build_kit(kit_args(self.fixture, out1)), 0)
        self.assertEqual(build_kit(kit_args(self.fixture, out2)), 0)
        files1 = sorted(p.relative_to(out1) for p in out1.rglob('*') if p.is_file())
        files2 = sorted(p.relative_to(out2) for p in out2.rglob('*') if p.is_file())
        self.assertEqual(files1, files2)
        for rel in files1:
            b1 = (out1 / rel).read_bytes()
            b2 = (out2 / rel).read_bytes()
            if rel.name == 'INDEX.md':
                # INDEX embeds the absolute kit path for user convenience;
                # normalize it before comparing deterministic content.
                b1 = b1.replace(str(out1).encode('utf-8'), b'<OUT>')
                b2 = b2.replace(str(out2).encode('utf-8'), b'<OUT>')
            if rel.name == 'kit_manifest.json':
                # The manifest hashes INDEX.md, whose embedded path differs by
                # design; drop that derived entry before comparing.
                m1, m2 = json.loads(b1), json.loads(b2)
                m1['files'].pop('INDEX.md', None)
                m2['files'].pop('INDEX.md', None)
                b1 = json.dumps(m1, sort_keys=True).encode('utf-8')
                b2 = json.dumps(m2, sort_keys=True).encode('utf-8')
            self.assertEqual(b1, b2, rel)

    def test_blind_packets_do_not_leak(self):
        out = self.root / 'o'
        self.assertEqual(build_kit(kit_args(self.fixture, out)), 0)
        packet = (out / 'packets' / 'B01.md').read_text(encoding='utf-8')
        for sentinel in ('c1', 'reorder', 'assistant_silver', 'JUDGE_REASON_SENTINEL',
                         '"expected"', 'mutation'):
            self.assertNotIn(sentinel, packet)
        self.assertIn('candidate text', packet)
        self.assertIn('source text', packet)
        self.assertIn('g:0', packet)

    def test_freeze_tamper_rejected(self):
        freeze = json.loads(self.fixture['paths']['freeze'].read_text(encoding='utf-8'))
        freeze['cases'][0]['candidate_sha256'] = 'tampered'
        self.fixture['paths']['freeze'].write_text(
            json.dumps(freeze), encoding='utf-8', newline='')
        out = self.root / 'o'
        self.assertEqual(build_kit(kit_args(self.fixture, out)), 2)
        self.assertFalse(out.exists())

    def test_overwrite_refused(self):
        out = self.root / 'o'
        self.assertEqual(build_kit(kit_args(self.fixture, out)), 0)
        self.assertEqual(build_kit(kit_args(self.fixture, out)), 3)

    def test_template_coverage(self):
        out = self.root / 'o'
        self.assertEqual(build_kit(kit_args(self.fixture, out)), 0)
        doc = json.loads((out / 'human_labels.blind.json').read_text(encoding='utf-8'))
        self.assertEqual(doc['stage'], 'blind')
        self.assertEqual({e['blind_code'] for e in doc['cases']}, {'B01', 'B02'})
        mapping = json.loads((out / 'sealed_mapping.json').read_text(encoding='utf-8'))
        self.assertEqual(mapping, {'B01': 'c1', 'B02': 'c2'})
        for e in doc['cases']:
            self.assertNotIn('case_id', e)
            self.assertIsNone(e['decision'])
            for v in e['dimensions'].values():
                self.assertIsNone(v['score'])
                self.assertIsNone(v['status'])
                self.assertIsNone(v['severity'])


if __name__ == '__main__':
    unittest.main()
