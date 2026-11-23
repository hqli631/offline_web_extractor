# -*- coding: utf-8 -*-
"""Tests for tools/apply_pf_dev_overrides.py (P-F dev gold re-adjudication)."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.apply_pf_dev_overrides import main, ROOT

SPEC = ROOT / 'configs/pf_dev_gold_overrides.v1.json'
INPUTS = ROOT / 'outputs/pb.gate.inputs.v1'
GOLDS = ('dev.orig.gold.json', 'dev.p2.gold.json')
CHANGED = {'cal-appetite-missing_paragraph', 'cal-interpreter-missing_paragraph',
           'cal-interpreter-reorder'}


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


class PfDevOverridesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / 'view'

    def run_tool(self, spec=SPEC, out=None):
        return main(['--spec', str(spec), '--inputs-dir', str(INPUTS),
                     '--output', str(out or self.out)])

    def tmp_spec(self, mutate):
        spec = load(SPEC)
        mutate(spec)
        p = Path(self.tmp.name) / 'spec.json'
        p.write_text(json.dumps(spec, ensure_ascii=False), encoding='utf-8')
        return p

    def test_happy_path_changes_exactly_three(self):
        self.assertEqual(self.run_tool(), 0)
        n_same = 0
        for n in GOLDS:
            a = {c['case_id']: c for c in load(INPUTS / n)['cases']}
            b = {c['case_id']: c for c in load(self.out / n)['cases']}
            self.assertEqual(set(a), set(b))
            for cid in a:
                if cid in CHANGED:
                    self.assertEqual(b[cid]['decision'], 'fail')
                    dim = 'structure' if cid.endswith('reorder') else 'completeness'
                    self.assertEqual(b[cid]['dimensions'][dim]['score'], 2)
                    self.assertEqual(b[cid]['dimensions'][dim]['severity'], 'major')
                    for k in a[cid]:
                        if k not in ('decision', 'dimensions'):
                            self.assertEqual(a[cid][k], b[cid][k])
                else:
                    self.assertEqual(a[cid], b[cid])
                    n_same += 1
        self.assertEqual(n_same, 15)
        aud = load(self.out / 'override_audit.json')
        self.assertEqual(len(aud['entries']), 3)
        self.assertTrue(aud['inputs_unchanged_verified'])
        self.assertTrue((self.out / 'OVERRIDE_DIFF.md').exists())

    def test_inputs_never_modified(self):
        before = {n: (INPUTS / n).read_bytes() for n in GOLDS}
        self.assertEqual(self.run_tool(), 0)
        for n in GOLDS:
            self.assertEqual((INPUTS / n).read_bytes(), before[n])

    def test_before_drift_rejected(self):
        def mut(s):
            s['entries'][0]['before']['dimensions']['completeness']['score'] = 4
        self.assertEqual(self.run_tool(spec=self.tmp_spec(mut)), 2)
        self.assertFalse(self.out.exists())

    def test_unknown_case_rejected(self):
        def mut(s):
            s['entries'][0]['case_id'] = 'cal-nonexistent-case'
        self.assertEqual(self.run_tool(spec=self.tmp_spec(mut)), 2)

    def test_wrong_source_file_rejected(self):
        def mut(s):
            s['entries'][0]['source_file'] = 'dev.p2.gold.json'
        self.assertEqual(self.run_tool(spec=self.tmp_spec(mut)), 2)

    def test_overwrite_refused(self):
        self.out.mkdir(parents=True)
        self.assertEqual(self.run_tool(), 3)

    def test_deterministic_bytes(self):
        out2 = Path(self.tmp.name) / 'view2'
        self.assertEqual(self.run_tool(), 0)
        self.assertEqual(self.run_tool(out=out2), 0)
        for n in GOLDS + ('override_audit.json', 'OVERRIDE_DIFF.md'):
            self.assertEqual((self.out / n).read_bytes(), (out2 / n).read_bytes())

    def test_empty_entries_rejected(self):
        def mut(s):
            s['entries'] = []
        self.assertEqual(self.run_tool(spec=self.tmp_spec(mut)), 2)

    def test_after_extra_dimension_rejected(self):
        def mut(s):
            s['entries'][0]['after']['dimensions']['cleanliness'] = {'score': 2, 'severity': 'major'}
        self.assertEqual(self.run_tool(spec=self.tmp_spec(mut)), 2)


if __name__ == '__main__':
    unittest.main()
