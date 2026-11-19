"""P2 cross-family judge provider tests (mock opener, zero network)."""
import json
import unittest
from src.webextractor.judge_openai_provider import JudgeOpenAIProvider
from src.webextractor.rubrics_judge import run_judge, build_prompt
from src.webextractor.rubrics_v2 import DIMENSIONS

SOURCE = '<html><head><meta charset="utf-8"></head><body><main><h1>1. Title</h1><p>Hello article</p></main></body></html>'
DOC = {'title': '1. Title', 'blocks': [{'kind': 'paragraph', 'text': 'Hello article'}]}


def assessment():
    return {'schema_version': 1, 'dimensions': {n: {'score': 4, 'status': 'scored', 'severity': 'none',
            'reason': 'ok', 'evidence': [{'ref': 's:0', 'quote': '1. Title'}]} for n in DIMENSIONS}}


class MockOpener:
    def __init__(self, content):
        self.content = content
        self.body = None
    def open(self, request, timeout):
        self.body = json.loads(request.data)
        outer = self
        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def read(self, limit):
                return json.dumps({'model': 'gpt-5.6-sol', 'choices': [{'finish_reason': 'stop',
                       'message': {'content': json.dumps(outer.content)}}],
                       'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30}}).encode()
        return Resp()


class CrossJudgeTests(unittest.TestCase):
    def test_provider_uses_judge_system_message(self):
        op = MockOpener(assessment())
        prov = JudgeOpenAIProvider(api_key='fake', model='gpt-5.6-sol', opener=op)
        run_judge(SOURCE, DOC, prov, gold=DOC)
        self.assertIn('quality judge', op.body['messages'][0]['content'])
        self.assertNotIn('constrained XPath rule', op.body['messages'][0]['content'])

    def test_run_judge_accepts_judge_json_not_rule(self):
        op = MockOpener(assessment())
        prov = JudgeOpenAIProvider(api_key='fake', model='gpt-5.6-sol', opener=op)
        rep = run_judge(SOURCE, DOC, prov, gold=DOC)
        self.assertEqual(rep['status'], 'accepted')
        self.assertEqual(rep['assessment']['decision'], 'pass')
        self.assertEqual(rep['provider'], 'cc-switch-judge')

    def test_requires_api_key(self):
        with self.assertRaises(ValueError):
            JudgeOpenAIProvider(api_key='', model='x')

    def test_dry_run_no_key_needed(self):
        import tools.run_p2_cross_judge as R
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'x.json'
            rc = R.main([str(R.ROOT / 'samples/calibration_manifest.json'), '--output', str(out), '--dry-run'])
            self.assertEqual(rc, 0)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
