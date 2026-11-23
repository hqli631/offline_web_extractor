# -*- coding: utf-8 -*-
"""P-A adjudication kit builder tests (zero calls; relies on committed artifacts)."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import tools.build_pa_adjudication_kit as pa


class BuildPaKitTests(unittest.TestCase):
    def build(self, td):
        out = Path(td) / 'kit'
        rc = pa.main(['--output', str(out)])
        return rc, out

    def test_build_structure(self):
        with TemporaryDirectory() as td:
            rc, out = self.build(td)
            self.assertEqual(rc, 0)
            for code in ('A01', 'A02', 'A03', 'A04', 'A05'):
                self.assertTrue((out / 'packets' / (code + '.md')).exists())
            self.assertTrue((out / 'INDEX.md').exists())
            self.assertTrue((out / 'kit_manifest.json').exists())
            findings = json.loads((out / 'pa_findings.json').read_text(encoding='utf-8'))
            self.assertEqual(len(findings['cases']), 5)
            self.assertEqual(findings['verdicts'], list(pa.VERDICTS))
            self.assertFalse(findings['discipline_ack'])
            self.assertTrue(all(c['verdict'] is None for c in findings['cases']))

    def test_overwrite_refused(self):
        with TemporaryDirectory() as td:
            rc, out = self.build(td)
            self.assertEqual(rc, 0)
            self.assertEqual(pa.main(['--output', str(out)]), 3)

    def test_case_ids_and_codes(self):
        with TemporaryDirectory() as td:
            _, out = self.build(td)
            findings = json.loads((out / 'pa_findings.json').read_text(encoding='utf-8'))
            pairs = [(c['code'], c['case_id']) for c in findings['cases']]
            self.assertEqual(pairs, [('A01', 'cal-appetite-reorder'), ('A02', 'n5-blurb-title'),
                                     ('A03', 'cal-appetite-noise'), ('A04', 'cal-blurb-noise'),
                                     ('A05', 'cal-blurb-reorder')])

    def test_manifest_source_hashes(self):
        with TemporaryDirectory() as td:
            _, out = self.build(td)
            man = json.loads((out / 'kit_manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(man['kit_version'], pa.KIT_VERSION)
            for rel, sha in man['source_artifacts_sha256'].items():
                self.assertEqual(sha, pa.sha256_bytes((pa.ROOT / rel).read_bytes()))

    def test_a02_title_evidence(self):
        with TemporaryDirectory() as td:
            _, out = self.build(td)
            txt = (out / 'packets' / 'A02.md').read_text(encoding='utf-8')
            self.assertIn('What is Python?  Executive Summary', txt)
            self.assertIn('exact=True', txt)
            self.assertIn('double space', txt)

    def test_a05_severity_conflict(self):
        with TemporaryDirectory() as td:
            _, out = self.build(td)
            txt = (out / 'packets' / 'A05.md').read_text(encoding='utf-8')
            self.assertIn('critical', txt)
            self.assertIn('indices=[0, 1]', txt)


if __name__ == '__main__':
    unittest.main()
