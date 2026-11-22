"""P1.5 judge v1.2.0 anti-anchoring decoupling targeted tests (zero model calls)."""
import json
import unittest

from src.webextractor.rubrics_judge import (build_prompt, validate_assessment, run_judge,
                                            JUDGE_VERSION, _ws_fold, MENU_QUOTE_CHARS)
from src.webextractor.rubrics_v2 import DIMENSIONS

SOURCE = ('<html><head><meta charset="utf-8"></head><body><main><h1>1.  Title</h1><p>Hello article</p>'
          '<ul><li>Item one</li></ul><pre>code  here</pre></main>'
          '<nav><p>Menu advertisement</p></nav></body></html>')
DOC = {'title': '1. Title', 'blocks': [{'kind': 'paragraph', 'text': 'Hello article'}]}


def assessment(ref='s:0', quote='1. Title'):
    return {'schema_version': 1, 'dimensions': {n: {'score': 4, 'status': 'scored', 'severity': 'none',
            'reason': 'ok', 'evidence': [{'ref': ref, 'quote': quote}]} for n in DIMENSIONS}}


class Provider:
    name = 'mock-judge'
    model = 'qwen3.8-27b'
    def __init__(self, value=None):
        self.value = value or assessment(); self.calls = 0
    def generate(self, prompt, **kwargs):
        self.calls += 1; self.prompt = prompt
        return {'content': json.loads(json.dumps(self.value)), 'model': self.model, 'finish_reason': 'stop',
                'usage': {'input_tokens': 10, 'output_tokens': 20, 'total_tokens': 30}}


class JudgeV12Tests(unittest.TestCase):
    def test_version_1_2_0(self):
        self.assertEqual(JUDGE_VERSION, '1.3.0')

    def test_menus_are_appendix_last_key(self):
        p, _, _ = build_prompt(SOURCE, DOC, DOC)
        self.assertEqual(list(p.keys())[-1], 'evidence_menus')
        self.assertIn('source', p); self.assertIn('candidate', p); self.assertIn('gold', p)

    def test_scoring_independence_constraint(self):
        p, _, _ = build_prompt(SOURCE, DOC, DOC)
        joined = ' '.join(p['protocol']['constraints'])
        self.assertIn('SCORING INDEPENDENCE', joined)
        self.assertIn('MUST NOT raise or lower any score or severity', joined)
        self.assertIn('SOLELY from the actual defect magnitude', joined)

    def test_citation_appendix_constraint(self):
        p, _, _ = build_prompt(SOURCE, DOC, DOC)
        joined = ' '.join(p['protocol']['constraints'])
        self.assertIn('CITATION APPENDIX', joined)
        self.assertIn('must not influence scoring', joined)

    def test_severity_anchor_reinforcement(self):
        p, _, _ = build_prompt(SOURCE, DOC, DOC)
        joined = ' '.join(p['protocol']['constraints'])
        for token in ('critical=empty', 'major=clear moderate', 'minor=small local', 'none=no material'):
            self.assertIn(token, joined)

    def test_generality_no_case_specific_content(self):
        p, _, _ = build_prompt(SOURCE, DOC, DOC)
        blob = json.dumps(p, ensure_ascii=False)
        self.assertNotIn('cal-', blob)
        for code in ('B01', 'B13', 'B18', 'B19'):
            self.assertNotIn(code, blob)

    def test_menus_preserved_and_validate(self):
        p, reg, _ = build_prompt(SOURCE, DOC, DOC)
        self.assertEqual(set(p['evidence_menus']), set(DIMENSIONS))
        for items in p['evidence_menus'].values():
            for it in items:
                self.assertIn(it['ref'], reg)
                self.assertTrue(_ws_fold(it['quote']) in _ws_fold(reg[it['ref']]))
                self.assertLessEqual(len(it['quote']), MENU_QUOTE_CHARS)

    def test_validation_rules_unchanged(self):
        _, reg, _ = build_prompt(SOURCE, DOC)
        validate_assessment(assessment(ref='s:0', quote='1. Title'), reg)  # ws-fold still works
        with self.assertRaises(ValueError):  # hallucination still rejected
            validate_assessment(assessment(ref='s:0', quote='invented text'), reg)
        val = assessment(ref='p:0', quote='Hello article')  # candidate-only still rejected
        with self.assertRaises(ValueError):
            validate_assessment(val, reg)

    def test_default_prompt_deterministic(self):
        a, _, _ = build_prompt(SOURCE, DOC, DOC)
        b, _, _ = build_prompt(SOURCE, DOC, DOC)
        self.assertEqual(a, b)

    def test_run_judge_accepted_v12(self):
        rep = run_judge(SOURCE, DOC, Provider(), gold=DOC)
        self.assertEqual(rep['status'], 'accepted')
        self.assertEqual(rep['judge_version'], '1.3.0')
        self.assertEqual(list(rep['prompt'].keys())[-1], 'evidence_menus')


if __name__ == '__main__':
    unittest.main()
