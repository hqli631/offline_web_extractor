# -*- coding: utf-8 -*-
"""P-F v4 draft blind kit tests (zero calls): blindness, structure, discipline."""
import json
import tempfile
import unittest
from pathlib import Path

from tools import build_pf_v4_kit as K


class PfV4KitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._td = tempfile.TemporaryDirectory()
        cls.out = Path(cls._td.name) / 'kit'
        assert K.main(['--output', str(cls.out)]) == 0
        cls.slate = json.loads((K.ROOT / 'outputs/pf.v4.slate.v1/pf_v4_slate.draft.json').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls._td.cleanup()

    def test_twelve_packets_and_codes(self):
        packets = sorted(p.name for p in (self.out / 'packets').glob('*.md'))
        self.assertEqual(packets, ['F%02d.md' % i for i in range(1, 13)])
        tpl = json.loads((self.out / 'human_labels.blind.json').read_text(encoding='utf-8'))
        self.assertEqual(len(tpl['cases']), 12)
        mapping = json.loads((self.out / 'sealed_mapping.json').read_text(encoding='utf-8'))
        self.assertEqual(set(mapping.values()), {c['case_id'] for c in self.slate['cases']})

    def test_packet_blindness(self):
        for p in (self.out / 'packets').glob('*.md'):
            t = p.read_text(encoding='utf-8')
            for bad in ('cal-', 'iana-abuse', 'iana-whois', 'missing_paragraph',
                        'instruction_interference', 'judge_version', 'mutation'):
                self.assertNotIn(bad, t)

    def test_draft_status_and_hashes(self):
        km = json.loads((self.out / 'kit_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(km['status'], 'DRAFT_UNSEALED_PENDING_APPROVAL')
        self.assertEqual(km['n_cases'], 12)
        import hashlib
        for rel, h in km['files'].items():
            self.assertEqual(hashlib.sha256((self.out / rel).read_bytes()).hexdigest(), h)

    def test_instructions_carry_anchors(self):
        tpl = json.loads((self.out / 'human_labels.blind.json').read_text(encoding='utf-8'))
        for token in ('R1', 'R2', 'R3', '绝不 minor', '按量级'):
            self.assertIn(token, tpl['instructions'])

    def test_overwrite_refusal(self):
        self.assertEqual(K.main(['--output', str(self.out)]), 3)

    def test_determinism(self):
        with tempfile.TemporaryDirectory() as td:
            out2 = Path(td) / 'kit2'
            self.assertEqual(K.main(['--output', str(out2)]), 0)
            for p in (self.out / 'packets').glob('*.md'):
                self.assertEqual(p.read_bytes(), (out2 / 'packets' / p.name).read_bytes())

    def test_non_draft_slate_refused(self):
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / 'slate.json'
            fake.write_text(json.dumps({'status': 'SEALED', 'cases': []}), encoding='utf-8')
            self.assertEqual(K.main(['--slate', str(fake), '--output', str(Path(td) / 'o')]), 2)


if __name__ == '__main__':
    unittest.main()
