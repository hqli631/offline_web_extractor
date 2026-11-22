# -*- coding: utf-8 -*-
"""Unit tests for tools/ingest_p3_findings.py (offline)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.ingest_p3_findings import validate_findings, summarize, category_of


def template_cases():
    return [{'case_id': 'cal-x-noise', 'split': 'development', 'categories': ['decision_mismatch', 'judge_severe_human_not:cleanliness']},
            {'case_id': 'cal-x-instruction_interference', 'split': 'frozen_test', 'categories': ['decision_mismatch']}]


def doc(verdicts=('judge_correct', 'human_correct'), ack=True, reviewer='r', date='2026-11-22'):
    cs = []
    for t, v in zip(template_cases(), verdicts):
        cs.append({'case_id': t['case_id'], 'split': t['split'], 'categories': t['categories'],
                   'verdict': v, 'note': '', 'anchor_revision_suggestion': ''})
    return {'findings_version': 1, 'reviewer': reviewer, 'review_date': date,
            'discipline_ack': ack, 'cases': cs}


class ValidateTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_findings(doc(), template_cases()), [])

    def test_null_verdict_rejected(self):
        errors = validate_findings(doc(verdicts=(None, 'human_correct')), template_cases())
        self.assertTrue(any('verdict must be one of' in e for e in errors))

    def test_bad_verdict_rejected(self):
        errors = validate_findings(doc(verdicts=('maybe', 'human_correct')), template_cases())
        self.assertTrue(any('verdict must be one of' in e for e in errors))

    def test_discipline_ack_required(self):
        errors = validate_findings(doc(ack=False), template_cases())
        self.assertTrue(any('discipline_ack' in e for e in errors))

    def test_reviewer_date_required(self):
        errors = validate_findings(doc(reviewer='', date='22-11-2026'), template_cases())
        self.assertTrue(any('reviewer' in e for e in errors))
        self.assertTrue(any('review_date' in e for e in errors))

    def test_coverage_and_altered_categories(self):
        d = doc()
        d['cases'] = d['cases'][:1]
        errors = validate_findings(d, template_cases())
        self.assertTrue(any('missing entry' in e for e in errors))
        d2 = doc()
        d2['cases'][0]['categories'] = ['tampered']
        errors = validate_findings(d2, template_cases())
        self.assertTrue(any('categories altered' in e for e in errors))


class SummaryTests(unittest.TestCase):
    def test_category_of(self):
        self.assertEqual(category_of('cal-a-instruction_interference', ['decision_mismatch']), 'A_injection_gold_miss')
        self.assertEqual(category_of('cal-a-noise', ['judge_severe_human_not:cleanliness']), 'B_judge_stricter')
        self.assertEqual(category_of('cal-a-clean', ['judge_missed_defect:cleanliness']), 'C_judge_missed')
        self.assertEqual(category_of('cal-a-x', ['decision_mismatch']), 'D_other')

    def test_summary_and_amendment_signal(self):
        rows = [{'case_id': 'c1', 'category': 'A_injection_gold_miss', 'verdict': 'judge_correct',
                 'note': '', 'anchor_revision_suggestion': ''},
                {'case_id': 'c2', 'category': 'B_judge_stricter', 'verdict': 'anchor_ambiguous',
                 'note': '', 'anchor_revision_suggestion': 'clarify noise magnitude'}]
        s = summarize(rows)
        self.assertEqual(s['verdict_counts']['judge_correct'], 1)
        self.assertEqual(s['verdict_counts']['anchor_ambiguous'], 1)
        self.assertTrue(s['amendment_signal'])
        self.assertEqual(len(s['anchor_suggestions']), 1)

    def test_no_signal_when_all_clear(self):
        rows = [{'case_id': 'c1', 'category': 'A_injection_gold_miss', 'verdict': 'judge_correct',
                 'note': '', 'anchor_revision_suggestion': ''}]
        self.assertFalse(summarize(rows)['amendment_signal'])


if __name__ == '__main__':
    unittest.main()
