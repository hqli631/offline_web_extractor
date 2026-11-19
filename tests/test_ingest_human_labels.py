# -*- coding: utf-8 -*-
import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools.ingest_human_labels import (cohen_kappa, run_blind, run_final,
                                       validate_labels)
from tests.human_review_fixtures import human_doc, make_fixture


def ingest_args(fixture, output, labels=None, round1=None, stage='blind'):
    p = fixture['paths']
    return argparse.Namespace(stage=stage, labels=labels, output=Path(output),
                              round1=round1, kit=p['kit'],
                              batch=p['batch'], stability=p['stability'],
                              freeze=p['freeze'], manifest=p['manifest'],
                              silver_labels=p['labels'])


class CohenKappaTest(unittest.TestCase):
    def test_perfect(self):
        self.assertEqual(cohen_kappa([('pass', 'pass'), ('fail', 'fail'),
                                      ('uncertain', 'uncertain')]), 1.0)

    def test_known_value(self):
        pairs = [('pass', 'pass'), ('pass', 'uncertain'),
                 ('fail', 'fail'), ('uncertain', 'uncertain')]
        self.assertEqual(cohen_kappa(pairs), 0.6364)

    def test_empty(self):
        self.assertIsNone(cohen_kappa([]))

    def test_single_category(self):
        self.assertEqual(cohen_kappa([('pass', 'pass'), ('pass', 'pass')]), 1.0)


class ValidationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = make_fixture(Path(self.tmp.name) / 'fx')
        self.batch = self.fixture['batch']

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_blind_doc(self):
        self.assertEqual(validate_labels(human_doc(self.batch), self.batch, 'blind'), [])

    def test_missing_case(self):
        doc = human_doc(self.batch)
        doc['cases'] = doc['cases'][:1]
        errors = validate_labels(doc, self.batch, 'blind')
        self.assertTrue(any('c2: missing' in e for e in errors))

    def test_bad_decision(self):
        doc = human_doc(self.batch)
        doc['cases'][0]['decision'] = 'bogus'
        self.assertTrue(any('decision must be' in e
                            for e in validate_labels(doc, self.batch, 'blind')))

    def test_source_only_pass_forbidden(self):
        doc = human_doc(self.batch)
        for e in doc['cases']:
            if e['case_id'] == 'c2':
                e['decision'] = 'pass'
        self.assertTrue(any('source_only' in e
                            for e in validate_labels(doc, self.batch, 'blind')))

    def test_score_range_and_type(self):
        doc = human_doc(self.batch)
        doc['cases'][0]['dimensions']['title']['score'] = 5
        doc['cases'][0]['dimensions']['cleanliness']['score'] = True
        errors = validate_labels(doc, self.batch, 'blind')
        self.assertTrue(any('title: score' in e for e in errors))
        self.assertTrue(any('cleanliness: score' in e for e in errors))

    def test_score_status_consistency(self):
        doc = human_doc(self.batch)
        doc['cases'][0]['dimensions']['title'] = {
            'score': None, 'status': 'scored', 'severity': 'none', 'note': ''}
        self.assertTrue(any('null score requires' in e
                            for e in validate_labels(doc, self.batch, 'blind')))

    def test_final_requires_confirmed(self):
        doc = human_doc(self.batch, stage='final', confirmed=False)
        self.assertTrue(any('confirmed must be true' in e
                            for e in validate_labels(doc, self.batch, 'final')))

    def test_injection_field_required(self):
        doc = human_doc(self.batch, stage='final', confirmed=True)
        silver = {'c1': {'mutation': {'type': 'instruction_interference'}}}
        self.assertTrue(any('injection_complied' in e
                            for e in validate_labels(doc, self.batch, 'final', silver)))


class BlindFinalFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fixture = make_fixture(self.root / 'fx')
        self.batch = self.fixture['batch']

    def tearDown(self):
        self.tmp.cleanup()

    def _run_blind(self, doc=None):
        doc = doc or human_doc(self.batch)
        rev = {'c1': 'B01', 'c2': 'B02'}
        for e in doc['cases']:
            e['blind_code'] = rev[e.pop('case_id')]
        labels = self.root / 'blind_labels.json'
        labels.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8',
                          newline='')
        out = self.root / 'round1'
        code = run_blind(ingest_args(self.fixture, out, labels=labels))
        return code, out, labels

    def test_blind_flow(self):
        code, out, _ = self._run_blind()
        self.assertEqual(code, 0)
        snap = json.loads((out / 'human_gold.blind.json').read_text(encoding='utf-8'))
        self.assertEqual(snap['label_origin'], 'human')
        self.assertTrue(snap['human_reviewed'])
        report = json.loads((out / 'blind_agreement.json').read_text(encoding='utf-8'))
        self.assertEqual(report['overall']['decision_match_rate'], 0.0)
        self.assertEqual(report['overall']['severe_miss_cases'], ['c1'])
        self.assertTrue((out / 'adjudicate' / 'c1.md').exists())
        self.assertTrue((out / 'adjudicate' / 'c2.md').exists())
        packet = (out / 'adjudicate' / 'c1.md').read_text(encoding='utf-8')
        self.assertIn('reorder', packet)
        self.assertIn('JUDGE_REASON_SENTINEL', packet)
        final = json.loads((out / 'human_labels.final.json').read_text(encoding='utf-8'))
        self.assertEqual(final['stage'], 'final')
        self.assertTrue(all(e['confirmed'] is False for e in final['cases']))
        self.assertTrue((out / 'ROUND1_SUMMARY.md').exists())

    def test_blind_validation_failure_creates_nothing(self):
        doc = human_doc(self.batch)
        doc['cases'][0]['decision'] = 'bogus'
        code, out, _ = self._run_blind(doc)
        self.assertEqual(code, 2)
        self.assertFalse(out.exists())

    def test_final_flow(self):
        code, out, _ = self._run_blind()
        self.assertEqual(code, 0)
        final = json.loads((out / 'human_labels.final.json').read_text(encoding='utf-8'))
        for e in final['cases']:
            e['confirmed'] = True
            e['adjudication_note'] = '维持盲评判断'
        labels2 = self.root / 'final_labels.json'
        labels2.write_text(json.dumps(final, ensure_ascii=False), encoding='utf-8',
                           newline='')
        out2 = self.root / 'final'
        code = run_final(ingest_args(self.fixture, out2, labels=labels2, round1=out,
                                     stage='final'))
        self.assertEqual(code, 0)
        report = json.loads((out2 / 'agreement_report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['overall']['decision_match_rate'], 0.0)
        self.assertEqual(report['blind_to_final_changed_cases'], [])
        ids = {f['case_id'] for f in report['persistent_disagreements']}
        self.assertEqual(ids, {'c1', 'c2'})
        snap = json.loads((out2 / 'human_gold.final.json').read_text(encoding='utf-8'))
        self.assertEqual(snap['label_origin'], 'human')
        self.assertTrue((out2 / 'AGREEMENT_REPORT.md').exists())
        self.assertTrue((out2 / 'calibration_findings.json').exists())

    def test_final_unconfirmed_rejected(self):
        code, out, _ = self._run_blind()
        self.assertEqual(code, 0)
        labels2 = self.root / 'final_labels.json'
        labels2.write_text((out / 'human_labels.final.json').read_text(encoding='utf-8'),
                           encoding='utf-8', newline='')
        out2 = self.root / 'final'
        code = run_final(ingest_args(self.fixture, out2, labels=labels2, round1=out,
                                     stage='final'))
        self.assertEqual(code, 2)
        self.assertFalse(out2.exists())


if __name__ == '__main__':
    unittest.main()
