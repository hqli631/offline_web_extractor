# -*- coding: utf-8 -*-
"""Unit tests for tools/ingest_p2_human_labels.py (offline, no model calls)."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.ingest_p2_human_labels import validate_labels, DECISIONS


def dim(score, status, severity, note=''):
    return {'score': score, 'status': status, 'severity': severity, 'note': note}


def make_case(code='P01', decision='uncertain', truncated=True):
    dims = {'completeness': dim(4, 'partial' if truncated else 'scored', 'none'),
            'cleanliness': dim(4, 'partial' if truncated else 'scored', 'none'),
            'structure': dim(4, 'partial' if truncated else 'scored', 'none'),
            'title': dim(4, 'partial' if truncated else 'scored', 'none'),
            'format': dim(None, 'not_applicable', 'none')}
    return {'blind_code': code, 'split': 'development', 'mode': 'with_gold',
            'decision': decision, 'dimensions': dims, 'overall_note': ''}


def make_doc(cases):
    return {'label_version': 1, 'stage': 'blind', 'annotator': 'tester',
            'annotation_date': '2026-11-22', 'cases': cases}


MAPPING = {'P01': 'cal-x-clean'}
METAS = {'cal-x-clean': {'mode': 'with_gold', 'source_truncated': True}}
MUT = {}


class ValidateLabelsTests(unittest.TestCase):
    def test_valid_truncated_uncertain(self):
        errors, _ = validate_labels(make_doc([make_case()]), MAPPING, METAS, MUT)
        self.assertEqual(errors, [])

    def test_valid_untruncated_pass(self):
        metas = {'cal-x-clean': {'mode': 'with_gold', 'source_truncated': False}}
        errors, _ = validate_labels(make_doc([make_case(decision='pass', truncated=False)]), MAPPING, metas, MUT)
        self.assertEqual(errors, [])

    def test_format_na_severity_critical_rejected(self):
        c = make_case()
        c['dimensions']['format']['severity'] = 'critical'
        errors, _ = validate_labels(make_doc([c]), MAPPING, METAS, MUT)
        self.assertTrue(any('not_applicable' in e for e in errors))

    def test_null_severity_rejected(self):
        c = make_case()
        c['dimensions']['completeness'] = dim(3, 'scored', None)
        errors, _ = validate_labels(make_doc([c]), MAPPING, METAS, MUT)
        self.assertTrue(any('invalid severity' in e for e in errors))
        self.assertTrue(any('score<4 requires severity' in e for e in errors))

    def test_score3_severity_none_rejected(self):
        c = make_case()
        c['dimensions']['cleanliness'] = dim(3, 'scored', 'none')
        errors, _ = validate_labels(make_doc([c]), MAPPING, METAS, MUT)
        self.assertTrue(any('score<4 requires severity' in e for e in errors))

    def test_score4_severity_minor_rejected(self):
        c = make_case()
        c['dimensions']['title'] = dim(4, 'scored', 'minor')
        errors, _ = validate_labels(make_doc([c]), MAPPING, METAS, MUT)
        self.assertTrue(any('score 4 requires severity none' in e for e in errors))

    def test_decision_inconsistent_with_severe(self):
        c = make_case(decision='uncertain')
        c['dimensions']['structure'] = dim(2, 'scored', 'major')
        errors, _ = validate_labels(make_doc([c]), MAPPING, METAS, MUT)
        self.assertTrue(any('expected fail' in e for e in errors))

    def test_truncated_pass_rejected(self):
        c = make_case(decision='pass')
        errors, _ = validate_labels(make_doc([c]), MAPPING, METAS, MUT)
        self.assertTrue(any('truncated source evidence cannot support pass' in e for e in errors))

    def test_truncated_all_scored_none_expects_uncertain(self):
        c = make_case(decision='uncertain')
        for n in ('completeness', 'cleanliness', 'structure', 'title'):
            c['dimensions'][n] = dim(4, 'scored', 'none')
        errors, _ = validate_labels(make_doc([c]), MAPPING, METAS, MUT)
        self.assertEqual(errors, [])

    def test_injection_complied_required(self):
        mut = {'cal-x-clean': 'instruction_interference'}
        c = make_case()
        errors, _ = validate_labels(make_doc([c]), MAPPING, METAS, mut)
        self.assertTrue(any('injection_complied' in e for e in errors))
        c['injection_complied'] = False
        errors, _ = validate_labels(make_doc([c]), MAPPING, METAS, mut)
        self.assertEqual(errors, [])

    def test_missing_and_unknown_entries(self):
        errors, _ = validate_labels(make_doc([]), MAPPING, METAS, MUT)
        self.assertTrue(any('missing entry' in e for e in errors))
        errors, _ = validate_labels(make_doc([make_case('P99')]), MAPPING, METAS, MUT)
        self.assertTrue(any('unknown blind code' in e for e in errors))
        self.assertTrue(any('missing entry' in e for e in errors))

    def test_bad_annotator_and_date(self):
        doc = make_doc([make_case()])
        doc['annotator'] = ''
        doc['annotation_date'] = '22-11-2026'
        errors, _ = validate_labels(doc, MAPPING, METAS, MUT)
        self.assertTrue(any('annotator' in e for e in errors))
        self.assertTrue(any('annotation_date' in e for e in errors))

    def test_source_only_pass_rejected(self):
        metas = {'cal-x-clean': {'mode': 'source_only', 'source_truncated': True}}
        c = make_case(decision='pass')
        errors, _ = validate_labels(make_doc([c]), MAPPING, metas, MUT)
        self.assertTrue(any('source_only' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
