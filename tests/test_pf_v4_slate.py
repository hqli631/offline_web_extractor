# -*- coding: utf-8 -*-
"""P-F v4 slate draft builder tests (zero calls, zero network)."""
import json
import tempfile
import unittest
from pathlib import Path

from tools import build_pf_v4_slate as S


class PfV4SlateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = S.build_slate()

    def test_twelve_cases_v3_shape(self):
        self.assertEqual(len(self.cases), 12)
        templates = {c['manifest_case']['template'] for c in self.cases}
        self.assertEqual(templates, {'iana-abuse', 'iana-whois'})
        for t in templates:
            variants = [c['label']['mutation']['type'] for c in self.cases
                        if c['manifest_case']['template'] == t]
            self.assertEqual(sorted(variants), sorted(
                ['clean', 'missing_paragraph', 'noise', 'duplicate', 'reorder', 'instruction_interference']))

    def test_no_truncation_pass_reachable(self):
        for c in self.cases:
            self.assertFalse(c['label']['source_truncated'])
            self.assertLessEqual(c['source_bytes'], 20000)

    def test_draft_status_and_exposure_disclosed(self):
        for c in self.cases:
            self.assertIn('same-family transfer', c['exposure'])
            self.assertEqual(c['label']['split'], 'frozen_test_v4_draft')
            self.assertFalse(c['label']['human_reviewed'])

    def test_determinism(self):
        self.assertEqual(S.build_slate(), self.cases)

    def test_reorder_mutation_real(self):
        for c in self.cases:
            if c['label']['mutation']['type'] == 'reorder':
                self.assertIn('indices', c['label']['mutation'])

    def test_overwrite_refusal_and_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'exists'
            out.mkdir()
            self.assertEqual(S.main(['--output', str(out)]), 3)
            self.assertEqual(S.main(['--output', str(Path(td) / 'dry'), '--dry-run']), 0)
            self.assertFalse((Path(td) / 'dry').exists())

    def test_main_writes_draft(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'slate'
            self.assertEqual(S.main(['--output', str(out)]), 0)
            d = json.loads((out / 'pf_v4_slate.draft.json').read_text(encoding='utf-8'))
            self.assertEqual(d['status'], 'DRAFT_UNSEALED_PENDING_APPROVAL')
            self.assertEqual(d['n_cases'], 12)
            self.assertTrue((out / 'PF_V4_SLATE.md').exists())


if __name__ == '__main__':
    unittest.main()
