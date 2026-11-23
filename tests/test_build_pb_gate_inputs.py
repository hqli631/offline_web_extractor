# -*- coding: utf-8 -*-
"""Tests for tools/build_pb_gate_inputs.py (P-B zero-call gate input builder)."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import build_pb_gate_inputs as b
from tools import score_p3_gate as g

ROOT = Path(__file__).resolve().parents[1]


def _inputs(root):
    return {k: root / v for k, v in b.DEFAULT_INPUTS.items()}


def _copy_inputs(dest):
    for k, rel in b.DEFAULT_INPUTS.items():
        src = ROOT / rel
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return _inputs(dest)


def _load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


class BuildPBGateInputsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real = _inputs(ROOT)
        cls.data = {k: _load(p) for k, p in cls.real.items()}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.out = self.tmp / 'out'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _build(self):
        return b.build(self.real, self.out)

    def test_happy_path_corrections(self):
        m = self._build()
        self.assertEqual(m['corrections'], ['C01', 'C02', 'A01'])
        g1 = _load(self.out / 'dev.orig.gold.json')
        g2 = _load(self.out / 'dev.p2.gold.json')
        a = {c['case_id']: c for c in g1['cases']}['cal-appetite-reorder']
        self.assertEqual(a['decision'], 'fail')
        self.assertEqual(a['dimensions']['structure']['score'], 2)
        self.assertEqual(a['dimensions']['structure']['severity'], 'major')
        n = {c['case_id']: c for c in g2['cases']}['cal-interpreter-noise']
        self.assertEqual(n['decision'], 'fail')
        self.assertEqual(n['dimensions']['cleanliness']['severity'], 'major')
        i = {c['case_id']: c for c in g2['cases']}['cal-interpreter-instruction_interference']
        self.assertEqual(i['decision'], 'fail')
        self.assertEqual(i['dimensions']['cleanliness']['severity'], 'critical')
        self.assertEqual(i['dimensions']['completeness']['severity'], 'major')
        self.assertEqual(i['dimensions']['structure']['severity'], 'major')

    def test_human_correct_cases_unchanged(self):
        self._build()
        g1 = {c['case_id']: c for c in _load(self.out / 'dev.orig.gold.json')['cases']}
        sealed = {c['case_id']: c for c in self.data['gold_orig']['cases']}
        for cid in ('cal-appetite-noise', 'cal-blurb-noise', 'cal-blurb-reorder'):
            self.assertEqual(g1[cid], sealed[cid])

    def test_non_dev_excluded(self):
        m = self._build()
        self.assertEqual(len(m['dev_cases']['orig']), 12)
        self.assertEqual(len(m['dev_cases']['p2']), 6)
        self.assertEqual(len(m['excluded_frozen_v2']), 12)
        v2 = _load(self.out / 'dev.p2.batch.json')
        self.assertEqual(len(v2['cases']), 6)
        self.assertTrue(all(c['split'] == 'development' for c in v2['cases']))
        self.assertEqual(len(_load(self.out / 'dev.orig.gold.json')['cases']), 12)
        self.assertEqual(len(_load(self.out / 'dev.p2.gold.json')['cases']), 6)

    def test_overwrite_refusal(self):
        self._build()
        with self.assertRaises(FileExistsError):
            self._build()
        rc = b.main(['--output', str(self.out)])
        self.assertEqual(rc, 3)

    def test_findings_byte_drift_fails_closed(self):
        inputs = _copy_inputs(self.tmp)
        p = inputs['findings_p3']
        p.write_bytes(p.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            b.build(inputs, self.out)

    def test_verdict_drift_fails_closed(self):
        inputs = _copy_inputs(self.tmp)
        d = _load(inputs['findings_pa'])
        for c in d['cases']:
            if c['code'] == 'A01':
                c['verdict'] = 'human_correct'
        inputs['findings_pa'].write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        pins = dict(b.FINDINGS_SHA)
        pins['findings_pa'] = b.sha256_bytes(inputs['findings_pa'].read_bytes())
        with mock.patch.dict(b.FINDINGS_SHA, pins, clear=True):
            with self.assertRaises(ValueError):
                b.build(inputs, self.out)

    def test_unexpected_judge_correct_fails_closed(self):
        inputs = _copy_inputs(self.tmp)
        d = _load(inputs['findings_p3'])
        d['cases'].append({'case_id': 'cal-blurb-clean', 'split': 'development',
                           'categories': ['decision_mismatch'], 'verdict': 'judge_correct'})
        inputs['findings_p3'].write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        pins = dict(b.FINDINGS_SHA)
        pins['findings_p3'] = b.sha256_bytes(inputs['findings_p3'].read_bytes())
        with mock.patch.dict(b.FINDINGS_SHA, pins, clear=True):
            with self.assertRaises(ValueError):
                b.build(inputs, self.out)

    def test_determinism(self):
        self._build()
        first = {p.name: p.read_bytes() for p in self.out.iterdir()}
        out2 = self.tmp / 'out2'
        b.build(self.real, out2)
        second = {p.name: p.read_bytes() for p in out2.iterdir()}
        self.assertEqual(first, second)

    def test_signature_and_meta_preserved(self):
        self._build()
        v2 = _load(self.out / 'dev.p2.batch.json')
        self.assertEqual(v2['signature'], self.data['dev_p2_batch']['signature'])
        self.assertEqual(v2['manifest_sha256'], self.data['dev_p2_batch']['manifest_sha256'])
        orig_meta = {c['case_id']: c['case_meta'] for c in self.data['dev_p2_batch']['cases']}
        for c in v2['cases']:
            self.assertEqual(c['case_meta'], orig_meta[c['case_id']])

    def test_gate_integrity_compat(self):
        self._build()
        cfg = _load(ROOT / 'outputs/pb.gate.config.v2.draft.json')
        for bf, ff in (('dev.orig.batch.json', 'outputs/rubrics_judge.node3.freeze.v4.json'),
                       ('dev.p2.batch.json', 'outputs/p2.freeze.v5.json')):
            batch = _load(self.out / bf)
            self.assertEqual(g.check_protocol(batch, cfg), [])
            self.assertEqual(g.check_data_freeze(batch, _load(ROOT / ff)), [])

    def test_human_status_note_preserved(self):
        self._build()
        g2 = {c['case_id']: c for c in _load(self.out / 'dev.p2.gold.json')['cases']}
        sealed = {c['case_id']: c for c in self.data['gold_p2']['cases']}
        n = g2['cal-interpreter-noise']
        self.assertEqual(n['dimensions']['cleanliness']['status'],
                         sealed['cal-interpreter-noise']['dimensions']['cleanliness']['status'])
        self.assertIn('overlay_note', n)
        self.assertEqual(n['blind_code'], sealed['cal-interpreter-noise']['blind_code'])

    def test_a02_not_in_dev_pool(self):
        self._build()
        for f in ('dev.orig.gold.json', 'dev.p2.gold.json'):
            ids = {c['case_id'] for c in _load(self.out / f)['cases']}
            self.assertNotIn('n5-blurb-title', ids)

    def test_upstream_chain_verified(self):
        m = self._build()
        kit = ROOT / 'outputs/human_review/p3.calibration.v1/p3_findings.json'
        self.assertEqual(b.sha256_bytes(kit.read_bytes()),
                         self.data['findings_p3']['provenance']['findings_sha256'])
        self.assertIn('findings_p3', m['inputs'])

    def test_main_cli_success(self):
        rc = b.main(['--output', str(self.out)])
        self.assertEqual(rc, 0)
        self.assertTrue((self.out / 'manifest.json').exists())
        self.assertTrue((self.out / 'INPUTS_SUMMARY.md').exists())

    def test_missing_gold_case_fails_closed(self):
        inputs = _copy_inputs(self.tmp)
        d = _load(inputs['gold_orig'])
        d['cases'] = [c for c in d['cases'] if c.get('case_id') != 'cal-iana-clean']
        inputs['gold_orig'].write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        with self.assertRaises(ValueError):
            b.build(inputs, self.out)


if __name__ == '__main__':
    unittest.main()
