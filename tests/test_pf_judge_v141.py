# -*- coding: utf-8 -*-
"""P-F judge v1.4.1 tests: single-anchor revision, freeze chains intact."""
import hashlib
import json
import unittest
from pathlib import Path

from src.webextractor import rubrics_judge as v12
from src.webextractor import rubrics_judge_v14 as v14
from src.webextractor import rubrics_judge_v141 as v141
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

    def __init__(self):
        self.calls = 0

    def generate(self, prompt, **kwargs):
        self.calls += 1
        return {'content': assessment(), 'model': self.model, 'finish_reason': 'stop',
                'usage': {'input_tokens': 10, 'output_tokens': 20, 'total_tokens': 30}}


class JudgeV141Tests(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(v141.JUDGE_VERSION, '1.4.1')
        self.assertEqual(v141.BASE_JUDGE_VERSION, '1.2.0')
        self.assertEqual(v141.PROTOCOL_ANCHORS_VERSION, 'v1.4.1')

    def test_freeze_chains(self):
        self.assertEqual(hashlib.sha256(Path(v12.__file__).read_bytes()).hexdigest(),
                         'edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891')
        pin = json.loads(Path('outputs/pf.protocol.v1.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(Path(v14.__file__).read_bytes()).hexdigest(),
                         pin['judge_module_sha256'])

    def test_exactly_one_anchor_revised(self):
        self.assertEqual(len(v141.PROTOCOL_ANCHORS_V141), 6)
        self.assertEqual(v141.PROTOCOL_ANCHORS_V141[:3], v14.PROTOCOL_ANCHORS_V14[:3])
        self.assertEqual(v141.PROTOCOL_ANCHORS_V141[4:], v14.PROTOCOL_ANCHORS_V14[4:])
        self.assertNotEqual(v141.PROTOCOL_ANCHORS_V141[3], v14.PROTOCOL_ANCHORS_V14[3])

    def test_missing_anchor_zero_discretion(self):
        a = v141.MISSING_BODY_ANCHOR_V141
        for token in ('ZERO DISCRETION', 'regardless of its position, length or perceived importance',
                      'FIRST paragraph', 'NEVER classify a missing body paragraph as minor',
                      'OVERRIDES the generic 3=small-local-defect scale', 'completeness <= 2'):
            self.assertIn(token, a)

    def test_prompt_anchors_marked(self):
        p, _, _ = v141.build_prompt(SOURCE, DOC, DOC)
        self.assertEqual(tuple(p['protocol']['constraints'][-6:]), v141.PROTOCOL_ANCHORS_V141)
        self.assertEqual(p['protocol']['protocol_anchors'], 'v1.4.1')

    def test_v14_prompt_not_mutated(self):
        p14, _, _ = v14.build_prompt(SOURCE, DOC, DOC)
        v141.build_prompt(SOURCE, DOC, DOC)
        p14b, _, _ = v14.build_prompt(SOURCE, DOC, DOC)
        self.assertEqual(p14, p14b)
        self.assertEqual(p14['protocol']['protocol_anchors'], 'v1.4')

    def test_budget_and_determinism(self):
        p, _, meta = v141.build_prompt(SOURCE, DOC, DOC, max_prompt_chars=20000)
        self.assertLessEqual(len(json.dumps(p, ensure_ascii=False)), 20000)
        with self.assertRaises(ValueError):
            v141.build_prompt(SOURCE, DOC, DOC, max_prompt_chars=500)
        a, _, _ = v141.build_prompt(SOURCE, DOC, DOC)
        b, _, _ = v141.build_prompt(SOURCE, DOC, DOC)
        self.assertEqual(a, b)

    def test_execution_equivalence_with_v12(self):
        r12 = v12.run_judge(SOURCE, DOC, Provider(), gold=DOC)
        r141 = v141.run_judge(SOURCE, DOC, Provider(), gold=DOC)
        self.assertEqual(r12['status'], r141['status'])
        self.assertEqual(r12['assessment'], r141['assessment'])
        self.assertEqual(r141['judge_version'], '1.4.1')
        self.assertEqual(r141['base_judge_version'], '1.2.0')
        self.assertEqual(r141['protocol_anchors'], 'v1.4.1')


if __name__ == '__main__':
    unittest.main()
