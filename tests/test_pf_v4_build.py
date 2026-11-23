# -*- coding: utf-8 -*-
"""Offline tests for P-F v4 FORMAL builder + kit (synthetic pages, zero network/calls)."""
import json
import tempfile
import unittest
from pathlib import Path

import tools.build_pf_v4_calibration as b
import tools.build_pf_v4_kit as k


def good_html(tag):
    para = ('This is a sufficiently long paragraph about databases and software. ' * 12)
    body = ''.join('<p>%s %s %d</p>' % (para, tag, i) for i in range(6))
    return ('<html><head><meta charset="utf-8"><title>%s</title></head>'
            '<body><main><h1>%s</h1>' % (tag, tag) + body + '</main></body></html>')


def make_samples(root):
    for pid, fam, tag in (('pf_v4_sqlite', 'sqlite-org', 'alpha'), ('pf_v4_debian', 'debian-org', 'beta')):
        text = good_html(tag)
        (root / (pid + '.html')).write_text(text, encoding='utf-8')
        side = {'page_id': pid, 'template': fam, 'url': 'https://example.invalid/' + pid,
                'final_url': 'https://example.invalid/' + pid, 'sha256': 'x' * 64,
                'raw_chars': len(text), 'fetched_at': '2026-11-23T00:00:00+00:00',
                'acceptance': {'n_blocks': 7, 'has_paragraph_pair': True, 'has_para_ge40': True, 'title_ok': True}}
        (root / (pid + '.html.source.json')).write_text(json.dumps(side), encoding='utf-8')


class V4FormalBuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.samples = self.root / 'samples'
        self.samples.mkdir()
        make_samples(self.samples)

    def test_discover_two_different_families(self):
        bases = b.discover_bases(self.samples)
        self.assertEqual(len(bases), 2)
        self.assertEqual({x['template_family'] for x in bases}, {'sqlite-org', 'debian-org'})

    def test_discover_requires_two(self):
        (self.samples / 'pf_v4_debian.html').unlink()
        with self.assertRaises(ValueError):
            b.discover_bases(self.samples)

    def test_discover_rejects_same_family(self):
        side = json.loads((self.samples / 'pf_v4_debian.html.source.json').read_text(encoding='utf-8'))
        side['template'] = 'sqlite-org'
        (self.samples / 'pf_v4_debian.html.source.json').write_text(json.dumps(side), encoding='utf-8')
        with self.assertRaises(ValueError):
            b.discover_bases(self.samples)

    def test_build_v4_twelve_cases_all_feasible(self):
        bases, built, feasible = b.build_v4(samples_root=self.samples)
        self.assertEqual(len(built), 12)
        self.assertTrue(all(f[2] == 'ok' for f in feasible), feasible)
        self.assertEqual({x['manifest_case']['split'] for x in built}, {'frozen_test'})
        self.assertEqual({x['manifest_case']['template'] for x in built}, {'pf_v4_sqlite', 'pf_v4_debian'})
        for x in built:
            self.assertIn('never-exposed', x['exposure'])
            self.assertFalse(x['label']['source_truncated'])

    def test_main_refuses_overwrite(self):
        m = self.root / 'manifest.json'
        m.write_text('{}', encoding='utf-8')
        rc = b.main(['--manifest', str(m), '--freeze', str(self.root / 'f.json'),
                     '--slate', str(self.root / 's.json'), '--samples-root', str(self.samples)])
        self.assertEqual(rc, 3)

    def test_main_requires_collected_pages(self):
        empty = self.root / 'empty'
        empty.mkdir()
        rc = b.main(['--manifest', str(self.root / 'm2.json'), '--freeze', str(self.root / 'f2.json'),
                     '--slate', str(self.root / 's2.json'), '--samples-root', str(empty)])
        self.assertEqual(rc, 2)

    def test_formal_kit_blind_and_anchored(self):
        _, built, _ = b.build_v4(samples_root=self.samples)
        slate = {'slate_version': 'test', 'status': 'FORMAL_ROUTE_A_APPROVED', 'route': 'A',
                 'cases': [{'case_id': x['case_id'], 'manifest_case': x['manifest_case'],
                            'candidate': x['candidate'], 'label': x['label'],
                            'prompt_chars': x['prompt_chars'], 'exposure': x['exposure']} for x in built]}
        sp = self.root / 'slate.json'
        sp.write_text(json.dumps(slate, ensure_ascii=False), encoding='utf-8')
        out = self.root / 'kit'
        rc = k.main(['--slate', str(sp), '--output', str(out), '--samples-root', str(self.samples)])
        self.assertEqual(rc, 0)
        packets = sorted((out / 'packets').glob('F*.md'))
        self.assertEqual(len(packets), 12)
        for pp in packets:
            text = pp.read_text(encoding='utf-8')
            self.assertNotIn('cal-', text)
            self.assertNotIn('pf_v4', text)
            for mut in ('missing_paragraph', 'instruction_interference', 'reorder', 'duplicate'):
                self.assertNotIn(mut, text)
        mapping = json.loads((out / 'sealed_mapping.json').read_text(encoding='utf-8'))
        self.assertEqual(len(mapping), 12)
        self.assertEqual(sorted(mapping), ['F%02d' % i for i in range(1, 13)])
        labels = json.loads((out / 'human_labels.blind.json').read_text(encoding='utf-8'))
        self.assertEqual(len(labels['cases']), 12)
        self.assertIn('R1', labels['instructions'])
        self.assertIn('R2', labels['instructions'])
        km = json.loads((out / 'kit_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(km['status'], 'FORMAL_ROUTE_A_OPEN_FOR_ANNOTATION')


if __name__ == '__main__':
    unittest.main()
