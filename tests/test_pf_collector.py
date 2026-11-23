# -*- coding: utf-8 -*-
"""Offline tests for tools/collect_pf_v4_sources.py (mocked fetch, zero network)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import tools.collect_pf_v4_sources as c


def good_html():
    para = ('This is a sufficiently long paragraph about databases and software. ' * 12)
    body = ''.join('<p>%s %d</p>' % (para, i) for i in range(6))
    return ('<html><head><meta charset="utf-8"><title>SQLite Usage</title></head>'
            '<body><main><h1>When To Use SQLite</h1>' + body + '</main></body></html>')


def entry_for(url, text, accepted=True, reason=None):
    return {'url': url, 'final_url': url, 'sha256': hashlib.sha256(text.encode()).hexdigest(),
            'raw_chars': len(text), 'fetched_at': '2026-11-23T00:00:00+00:00',
            'n_blocks': 7, 'has_paragraph_pair': True, 'has_para_ge40': True, 'title_ok': True,
            'accepted': accepted, 'reject_reason': reason}


class CollectorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.samples = self.root / 'samples'
        self.samples.mkdir()
        self.log = self.root / 'log.json'

    def test_acceptance_good_page(self):
        text = good_html()
        checks = c.acceptance_checks(text.encode('utf-8'), text)
        self.assertIsNone(checks['reject_reason'])
        self.assertGreaterEqual(checks['n_blocks'], 3)
        self.assertTrue(checks['has_paragraph_pair'])

    def test_acceptance_too_short(self):
        text = '<html><body><main><h1>T</h1><p>short</p></main></body></html>'
        checks = c.acceptance_checks(text.encode(), text)
        self.assertIn('outside', checks['reject_reason'])

    def test_acceptance_no_paragraph_pair(self):
        pad = 'x ' * 3000
        text = ('<html><head><title>T</title></head><body><main><h1>H</h1>'
                '<p>only one paragraph %s</p><pre>code</pre></main></body></html>' % pad)
        checks = c.acceptance_checks(text.encode(), text)
        self.assertIn('reorder infeasible', checks['reject_reason'] or '')

    def test_main_complete_writes_both(self):
        text = good_html()
        payload = text.encode('utf-8')

        def fake_fetch(opener, url, log):
            e = entry_for(url, text)
            log.append(e)
            return (payload, text), e

        with mock.patch.object(c, '_opener', return_value=object()), \
             mock.patch.object(c, 'fetch', side_effect=fake_fetch):
            rc = c.main(['--log', str(self.log), '--samples-dir', str(self.samples)])
        self.assertEqual(rc, 0)
        doc = json.loads(self.log.read_text(encoding='utf-8'))
        self.assertEqual(doc['status'], 'complete')
        self.assertEqual(doc['total_fetches'], 2)
        for pid in ('pf_v4_sqlite', 'pf_v4_debian'):
            self.assertTrue((self.samples / (pid + '.html')).exists())
            side = json.loads((self.samples / (pid + '.html.source.json')).read_text(encoding='utf-8'))
            self.assertEqual(side['sha256'], hashlib.sha256(payload).hexdigest())

    def test_main_incomplete_no_samples(self):
        def fake_fetch(opener, url, log):
            e = entry_for(url, 'x', accepted=False, reason='raw_chars 1 outside [5000, 20000]')
            log.append(e)
            return None, e

        with mock.patch.object(c, '_opener', return_value=object()), \
             mock.patch.object(c, 'fetch', side_effect=fake_fetch):
            rc = c.main(['--log', str(self.log), '--samples-dir', str(self.samples)])
        self.assertEqual(rc, 2)
        doc = json.loads(self.log.read_text(encoding='utf-8'))
        self.assertEqual(doc['status'], 'incomplete')
        self.assertLessEqual(doc['total_fetches'], c.TOTAL_FETCH_CAP)
        self.assertEqual(list(self.samples.glob('*.html')), [])

    def test_log_overwrite_refused(self):
        self.log.write_text('{}', encoding='utf-8')
        self.assertEqual(c.main(['--log', str(self.log), '--samples-dir', str(self.samples)]), 3)

    def test_sample_overwrite_refused(self):
        (self.samples / 'pf_v4_sqlite.html').write_text('x', encoding='utf-8')
        self.assertEqual(c.main(['--log', str(self.log), '--samples-dir', str(self.samples)]), 3)

    def test_excluded_host_never_fetched(self):
        slot = {'page_id': 'x', 'template': 'gnu-philosophy',
                'urls': ['https://www.gnu.org/philosophy/free-doc.html']}
        log, budget = [], [0]
        with mock.patch.object(c, 'fetch') as f:
            got = c.collect_slot(object(), slot, log, budget)
        self.assertIsNone(got)
        f.assert_not_called()
        self.assertIn('exposed template family', log[0]['reject_reason'])


if __name__ == '__main__':
    unittest.main()
