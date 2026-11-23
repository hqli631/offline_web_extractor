# -*- coding: utf-8 -*-
"""P-F runner --judge-version opt-in tests (zero model calls, mock provider)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import run_rubrics_judge as r
from src.webextractor import rubrics_judge as v12
from src.webextractor import rubrics_judge_v14 as v14

SOURCE = ('<html><head><meta charset="utf-8"></head><body><main><h1>1.  Title</h1>'
          '<p>Hello article body text.</p><p>Second paragraph here.</p>'
          '<pre>code  here</pre></main><nav><p>Menu advertisement</p></nav></body></html>')


class MenuProvider:
    name = 'mock-judge'
    model = 'qwen3.8-27b'

    def __init__(self):
        self.calls = 0
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.calls += 1
        self.prompts.append(prompt)
        dims = {}
        for n, items in prompt['evidence_menus'].items():
            sg = [it for it in items if it['ref'].startswith(('s:', 'g:'))]
            ev = [sg[0]] if sg else [{'ref': 's:html', 'quote': '<main>'}]
            dims[n] = {'score': 4, 'status': 'scored', 'severity': 'none',
                       'reason': 'ok', 'evidence': ev}
        return {'content': {'schema_version': 1, 'dimensions': dims}, 'model': self.model,
                'finish_reason': 'stop',
                'usage': {'input_tokens': 10, 'output_tokens': 20, 'total_tokens': 30}}


class RunnerV14Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'page.html').write_text(SOURCE, encoding='utf-8')
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps({'judge_manifest_version': 1, 'cases': [
            {'case_id': 't1', 'template': 'tmpl', 'split': 'development', 'source': 'page.html'}]}),
            encoding='utf-8')

    def run_batch(self, provider, **kw):
        kw.setdefault('cache_path', self.root / 'cache.json')
        kw.setdefault('max_calls', 5)
        return r.run_batch(self.manifest, provider, **kw)

    def test_default_signature_unchanged(self):
        sig = r.config_signature('qwen3.8-27b', 2200, 20000, 90.0)
        self.assertEqual(sig['judge_version'], '1.2.0')
        self.assertEqual(sig, {'model': 'qwen3.8-27b', 'max_output_tokens': 2200,
                               'max_source_chars': 20000, 'timeout_seconds': 90.0,
                               'judge_version': v12.JUDGE_VERSION, 'rubrics_version': r.RUBRICS_VERSION})

    def test_judge_module_selector(self):
        self.assertIs(r._judge_module('1.2'), v12)
        self.assertEqual(r._judge_module('1.4').JUDGE_VERSION, '1.4.0')
        with self.assertRaises(ValueError):
            r._judge_module('9.9')

    def test_run_batch_v14_provenance_and_anchors(self):
        p = MenuProvider()
        rep = self.run_batch(p, judge_version='1.4')
        self.assertEqual(rep['signature']['judge_version'], '1.4.0')
        row = rep['cases'][0]
        self.assertEqual(row['status'], 'accepted')
        jr = row['report']
        self.assertEqual(jr['judge_version'], '1.4.0')
        self.assertEqual(jr['base_judge_version'], '1.2.0')
        self.assertEqual(jr['protocol_anchors'], 'v1.4')
        constraints = p.prompts[0]['protocol']['constraints']
        self.assertEqual(tuple(constraints[-len(v14.PROTOCOL_ANCHORS_V14):]), v14.PROTOCOL_ANCHORS_V14)
        self.assertEqual(p.prompts[0]['protocol']['protocol_anchors'], 'v1.4')

    def test_run_batch_default_stays_v12(self):
        p = MenuProvider()
        rep = self.run_batch(p)
        self.assertEqual(rep['signature']['judge_version'], '1.2.0')
        jr = rep['cases'][0]['report']
        self.assertEqual(jr['judge_version'], '1.2.0')
        self.assertNotIn('protocol_anchors', jr)
        self.assertNotIn('protocol_anchors', p.prompts[0]['protocol'])
        self.assertNotIn('PROTOCOL ANCHOR', ' '.join(p.prompts[0]['protocol']['constraints']))

    def test_cache_keys_disjoint_across_versions(self):
        cache = self.root / 'shared_cache.json'
        p12 = MenuProvider()
        self.run_batch(p12, cache_path=cache)
        p14 = MenuProvider()
        rep14 = self.run_batch(p14, cache_path=cache, judge_version='1.4')
        self.assertEqual(p12.calls, 1)
        self.assertEqual(p14.calls, 1)  # v1.2 cache entry must NOT satisfy v1.4
        self.assertEqual(rep14['cases'][0]['status'], 'accepted')
        self.assertEqual(len(json.loads(cache.read_text(encoding='utf-8'))), 2)
        p14b = MenuProvider()
        rep14b = self.run_batch(p14b, cache_path=cache, judge_version='1.4')
        self.assertEqual(p14b.calls, 0)  # same-version cache hit works
        self.assertTrue(rep14b['cases'][0]['cache_hit'])

    def test_cli_exposes_flag(self):
        out = subprocess.run([sys.executable, '-m', 'tools.run_rubrics_judge', '--help'],
                             capture_output=True, text=True, cwd=str(r.ROOT))
        self.assertEqual(out.returncode, 0)
        self.assertIn('--judge-version', out.stdout)
        self.assertIn('1.4', out.stdout)


if __name__ == '__main__':
    unittest.main()
