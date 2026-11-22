# -*- coding: utf-8 -*-
"""P3 rollback verification: judge v1.3 amendment failed the pre-registered
dev regression guard; v1.2.0 restored byte-exact (freeze v8 == v4 hashes)."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.webextractor.rubrics_judge import JUDGE_VERSION, build_prompt
from src.webextractor.rubrics_v2 import VERSION as RUBRICS_VERSION

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '<html><body><nav>Menu Home</nav><article><h1>Title</h1><p>First paragraph text.</p><p>Second paragraph text.</p></article><footer>Copyright</footer></body></html>'
CAND = {'title': 'Title', 'blocks': [{'kind': 'heading', 'text': 'Title'},
                   {'kind': 'paragraph', 'text': 'First paragraph text.'},
                   {'kind': 'paragraph', 'text': 'Second paragraph text.'}]}


def _prompt():
    return build_prompt(SOURCE, CAND, max_source_chars=20000)[0]


class RollbackTests(unittest.TestCase):
    def test_judge_version_restored(self):
        self.assertEqual(JUDGE_VERSION, '1.2.0')

    def test_rubrics_version_unchanged(self):
        self.assertEqual(RUBRICS_VERSION, '2.0.0')

    def test_judge_sha_matches_freeze_v4(self):
        sha = hashlib.sha256((ROOT / 'src/webextractor/rubrics_judge.py').read_bytes()).hexdigest()
        v4 = json.loads((ROOT / 'outputs/rubrics_judge.node3.freeze.v4.json').read_text(encoding='utf-8'))
        self.assertEqual(sha, v4['files']['src/webextractor/rubrics_judge.py'])

    def test_v13_anchors_removed(self):
        a = _prompt()['protocol']['anchors']
        self.assertEqual(a['3'], 'Small local defect (e.g. missing title number)')
        self.assertEqual(a['2'], 'Clear moderate loss or contamination')

    def test_v13_constraints_removed(self):
        cs = _prompt()['protocol']['constraints']
        for prefix in ('Severity granularity:', 'Source presence is not justification:', 'Order check:'):
            self.assertFalse(any(c.startswith(prefix) for c in cs))

    def test_v12_scoring_independence_preserved(self):
        cs = _prompt()['protocol']['constraints']
        self.assertTrue(any('SCORING INDEPENDENCE' in c for c in cs))

    def test_freeze_v8_rollback_record(self):
        v8 = json.loads((ROOT / 'outputs/rubrics_judge.node3.freeze.v8.json').read_text(encoding='utf-8'))
        v4 = json.loads((ROOT / 'outputs/rubrics_judge.node3.freeze.v4.json').read_text(encoding='utf-8'))
        self.assertEqual(v8['freeze_version'], 8)
        self.assertEqual(v8['amendment']['type'], 'rollback')
        self.assertEqual(v8['amendment']['judge_version'], {'failed': '1.3.0', 'restored': '1.2.0'})
        self.assertEqual(v8['files'], v4['files'])
        self.assertEqual(v8['batch_config'], v4['batch_config'])


if __name__ == '__main__':
    unittest.main()
