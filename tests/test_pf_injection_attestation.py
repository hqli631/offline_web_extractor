# -*- coding: utf-8 -*-
"""Tests for tools/apply_injection_attestation.py (offline, fail-closed)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import apply_injection_attestation as att


def make_doc():
    return {'label_version': 1, 'stage': 'blind', 'annotator': 'tester',
            'annotation_date': '2026-11-23',
            'cases': [{'blind_code': 'F03', 'decision': 'fail',
                       'injection_complied': 'false'},
                      {'blind_code': 'F09', 'decision': 'fail'}]}


def make_cfg():
    return {'attestation_version': 1, 'status': 'approved',
            'approved_by': 'tester', 'approved_at': '2026-11-23',
            'entries': [
                {'blind_code': 'F03', 'field': 'injection_complied',
                 'value': False, 'reason': 'string placeholder -> boolean; semantics unchanged'},
                {'blind_code': 'F09', 'field': 'injection_complied',
                 'value': False, 'reason': 'missing field filled per annotator confirmation'}]}


class AttestationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.lp = self.tmp / 'labels.json'
        self.cp = self.tmp / 'cfg.json'
        self.lp.write_text(json.dumps(make_doc()), encoding='utf-8')
        self.cp.write_text(json.dumps(make_cfg()), encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, out_name='out', apply=True, cfg=None):
        if cfg is not None:
            self.cp.write_text(json.dumps(cfg), encoding='utf-8')
        argv = ['--labels', str(self.lp), '--config', str(self.cp),
                '--output', str(self.tmp / out_name)]
        if apply:
            argv.append('--apply')
        return att.main(argv)

    def test_happy_coercion_and_fill(self):
        rc = self.run_main()
        self.assertEqual(rc, 0)
        fixed = json.loads((self.tmp / 'out/human_labels.blind.json').read_text(encoding='utf-8'))
        by = {c['blind_code']: c for c in fixed['cases']}
        self.assertIs(by['F03']['injection_complied'], False)
        self.assertIs(by['F09']['injection_complied'], False)
        audit = json.loads((self.tmp / 'out/attestation_audit.json').read_text(encoding='utf-8'))
        self.assertTrue(audit['applied'])
        self.assertEqual(audit['entries'][0]['before'], 'false')
        self.assertIsNone(audit['entries'][1]['before'])
        # original untouched
        orig = json.loads(self.lp.read_text(encoding='utf-8'))
        self.assertEqual(orig['cases'][0]['injection_complied'], 'false')
        self.assertNotIn('injection_complied', orig['cases'][1])

    def test_dry_run_writes_no_labels(self):
        rc = self.run_main(apply=False)
        self.assertEqual(rc, 0)
        self.assertFalse((self.tmp / 'out/human_labels.blind.json').exists())
        audit = json.loads((self.tmp / 'out/attestation_audit.json').read_text(encoding='utf-8'))
        self.assertFalse(audit['applied'])

    def test_proposed_config_rejected(self):
        cfg = make_cfg(); cfg['status'] = 'proposed'
        self.assertEqual(self.run_main(cfg=cfg), 2)

    def test_empty_approver_rejected(self):
        cfg = make_cfg(); cfg['approved_by'] = ''
        self.assertEqual(self.run_main(cfg=cfg), 2)

    def test_unknown_blind_code_rejected(self):
        cfg = make_cfg(); cfg['entries'][0]['blind_code'] = 'F99'
        self.assertEqual(self.run_main(cfg=cfg), 2)

    def test_non_boolean_value_rejected(self):
        cfg = make_cfg(); cfg['entries'][0]['value'] = 'false'
        self.assertEqual(self.run_main(cfg=cfg), 2)

    def test_existing_boolean_refused(self):
        doc = make_doc(); doc['cases'][0]['injection_complied'] = True
        self.lp.write_text(json.dumps(doc), encoding='utf-8')
        self.assertEqual(self.run_main(), 2)

    def test_contradicting_placeholder_refused(self):
        doc = make_doc(); doc['cases'][0]['injection_complied'] = 'true'
        self.lp.write_text(json.dumps(doc), encoding='utf-8')
        self.assertEqual(self.run_main(), 2)

    def test_overwrite_refused(self):
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(self.run_main(), 3)

    def test_case_id_leak_refused(self):
        doc = make_doc(); doc['cases'][0]['case_id'] = 'cal-x-injection'
        self.lp.write_text(json.dumps(doc), encoding='utf-8')
        self.assertEqual(self.run_main(), 2)


if __name__ == '__main__':
    unittest.main()
