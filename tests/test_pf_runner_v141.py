# -*- coding: utf-8 -*-
"""P-F runner 1.4.1 opt-in tests (mock provider, zero calls)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import run_rubrics_judge as r
from tests.test_pf_runner_v14 import MenuProvider, SOURCE


class RunnerV141Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'page.html').write_text(SOURCE, encoding='utf-8')
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps({'judge_manifest_version': 1, 'cases': [
            {'case_id': 't1', 'template': 'tmpl', 'split': 'development', 'source': 'page.html'}]}),
            encoding='utf-8')

    def test_selector_and_provenance(self):
        self.assertEqual(r._judge_module('1.4.1').JUDGE_VERSION, '1.4.1')
        p = MenuProvider()
        rep = r.run_batch(self.manifest, p, judge_version='1.4.1',
                          cache_path=self.root / 'c.json', max_calls=5)
        self.assertEqual(rep['signature']['judge_version'], '1.4.1')
        jr = rep['cases'][0]['report']
        self.assertEqual(rep['cases'][0]['status'], 'accepted')
        self.assertEqual(jr['judge_version'], '1.4.1')
        self.assertEqual(jr['protocol_anchors'], 'v1.4.1')
        joined = ' '.join(p.prompts[0]['protocol']['constraints'])
        self.assertIn('ZERO DISCRETION', joined)

    def test_cache_disjoint_three_versions(self):
        cache = self.root / 'shared.json'
        for ver in ('1.2', '1.4', '1.4.1'):
            p = MenuProvider()
            r.run_batch(self.manifest, p, judge_version=ver, cache_path=cache, max_calls=5)
            self.assertEqual(p.calls, 1)
        self.assertEqual(len(json.loads(cache.read_text(encoding='utf-8'))), 3)
        p = MenuProvider()
        rep = r.run_batch(self.manifest, p, judge_version='1.4.1', cache_path=cache, max_calls=5)
        self.assertEqual(p.calls, 0)
        self.assertTrue(rep['cases'][0]['cache_hit'])

    def test_cli_lists_141(self):
        out = subprocess.run([sys.executable, '-m', 'tools.run_rubrics_judge', '--help'],
                             capture_output=True, text=True, cwd=str(r.ROOT))
        self.assertEqual(out.returncode, 0)
        self.assertIn('1.4.1', out.stdout)


if __name__ == '__main__':
    unittest.main()
