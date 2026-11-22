# -*- coding: utf-8 -*-
"""P3 judge v1.3.0 calibration amendment targeted tests (zero model calls)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.webextractor.rubrics_judge import JUDGE_VERSION, build_prompt
from src.webextractor.rubrics_v2 import VERSION as RUBRICS_VERSION

SOURCE = '<html><body><nav>Menu Home</nav><article><h1>Title</h1><p>First paragraph text.</p><p>Second paragraph text.</p></article><footer>Copyright</footer></body></html>'
CAND = {'title': 'Title', 'blocks': [{'kind': 'heading', 'text': 'Title'},
                   {'kind': 'paragraph', 'text': 'First paragraph text.'},
                   {'kind': 'paragraph', 'text': 'Second paragraph text.'}]}


def _prompt():
    return build_prompt(SOURCE, CAND, max_source_chars=20000)[0]


class VersionTests(unittest.TestCase):
    def test_judge_version(self):
        self.assertEqual(JUDGE_VERSION, '1.3.0')

    def test_rubrics_version_unchanged(self):
        self.assertEqual(RUBRICS_VERSION, '2.0.0')


class AnchorTests(unittest.TestCase):
    def test_anchor3_granularity_examples(self):
        a = _prompt()['protocol']['anchors']
        self.assertIn('single short noise block in a long article', a['3'])
        self.assertIn('one non-lead body paragraph missing', a['3'])
        self.assertIn('single adjacent paragraph swap', a['3'])

    def test_anchor2_granularity_examples(self):
        a = _prompt()['protocol']['anchors']
        self.assertIn('noise spanning multiple blocks', a['2'])
        self.assertIn('missing lead/abstract or multiple paragraphs', a['2'])
        self.assertIn('multi-block order disruption', a['2'])

    def test_anchor4_1_0_unchanged(self):
        a = _prompt()['protocol']['anchors']
        self.assertEqual(a['4'], 'No material defect observed in supplied scope')
        self.assertEqual(a['1'], 'Large defect')
        self.assertEqual(a['0'], 'Empty or fundamentally incorrect')


class ConstraintTests(unittest.TestCase):
    def test_severity_granularity_constraint(self):
        cs = _prompt()['protocol']['constraints']
        self.assertTrue(any(c.startswith('Severity granularity:') for c in cs))

    def test_source_presence_constraint(self):
        cs = _prompt()['protocol']['constraints']
        self.assertTrue(any(c.startswith('Source presence is not justification:') for c in cs))

    def test_order_check_constraint(self):
        cs = _prompt()['protocol']['constraints']
        self.assertTrue(any(c.startswith('Order check:') for c in cs))

    def test_scoring_independence_preserved(self):
        cs = _prompt()['protocol']['constraints']
        self.assertTrue(any('SCORING INDEPENDENCE' in c for c in cs))

    def test_no_case_specific_rules(self):
        cs = _prompt()['protocol']['constraints']
        for token in ('nasa', 'w3ca11y', 'interpreter', 'C01', 'C03', 'C09'):
            self.assertFalse(any(token in c for c in cs))


if __name__ == '__main__':
    unittest.main()
