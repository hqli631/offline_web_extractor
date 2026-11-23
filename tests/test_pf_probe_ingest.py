# -*- coding: utf-8 -*-
"""Offline tests for tools/ingest_pf_v4_probes.py (synthetic probes, zero network)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import tools.ingest_pf_v4_probes as ing


def good_html(tag):
    para = ('This is a sufficiently long paragraph about databases and software. ' * 12)
    body = ''.join('<p>%s %s %d</p>' % (para, tag, i) for i in range(6))
    return ('<html><head><meta charset="utf-8"><title>%s</title></head>'
            '<body><main><h1>%s</h1>' % (tag, tag) + body + '</main></body></html>')


class ProbeIngestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.samples = self.root / 'samples'
        self.samples.mkdir()
        self.logp = self.root / 'log.json'

    def make_log(self, families=('debian-org', 'freebsd-org'), tamper_sha=False, short_payload=False):
        fetches = []
        for pid, fam, tag in (('pf_v4_debian', families[0], 'alpha'), ('pf_v4_freebsd', families[1], 'beta')):
            text = '<html><body><p>short</p></body></html>' if short_payload else good_html(tag)
            payload = text.encode('utf-8')
            pf = self.root / (pid + '.html')
            pf.write_bytes(payload)
            sha = '0' * 64 if tamper_sha else hashlib.sha256(payload).hexdigest()
            fetches.append({'url': 'https://example.invalid/' + pid, 'probe': True, 'accepted': True,
                            'page_id': pid, 'template': fam, 'probe_file': str(pf),
                            'sha256': sha, 'raw_chars': len(text),
                            'fetched_at': '2026-11-23T00:00:00+00:00', 'final_url': 'https://example.invalid/' + pid})
        doc = {'status': 'incomplete', 'total_fetches': len(fetches), 'fetches': fetches}
        self.logp.write_text(json.dumps(doc), encoding='utf-8')
        return doc

    def run_tool(self):
        return ing.main(['--log', str(self.logp), '--samples-dir', str(self.samples)])

    def test_happy_two_families(self):
        doc = self.make_log()
        self.assertEqual(self.run_tool(), 0)
        after = json.loads(self.logp.read_text(encoding='utf-8'))
        self.assertEqual(after['status'], 'complete')
        self.assertEqual(after['accepted_page_ids'], ['pf_v4_debian', 'pf_v4_freebsd'])
        self.assertEqual(after['fetches'], doc['fetches'])  # fetch records immutable
        for pid in ('pf_v4_debian', 'pf_v4_freebsd'):
            self.assertTrue((self.samples / (pid + '.html')).exists())
            side = json.loads((self.samples / (pid + '.html.source.json')).read_text(encoding='utf-8'))
            self.assertTrue(side['probe_ingest'])

    def test_sha_drift_rejected(self):
        self.make_log(tamper_sha=True)
        self.assertEqual(self.run_tool(), 2)
        self.assertEqual(list(self.samples.glob('*.html')), [])

    def test_reacceptance_failure_rejected(self):
        self.make_log(short_payload=True)  # sha matches but acceptance re-run fails
        self.assertEqual(self.run_tool(), 2)

    def test_same_family_rejected(self):
        self.make_log(families=('debian-org', 'debian-org'))
        self.assertEqual(self.run_tool(), 2)

    def test_overwrite_refused(self):
        self.make_log()
        (self.samples / 'pf_v4_debian.html').write_text('x', encoding='utf-8')
        self.assertEqual(self.run_tool(), 3)


if __name__ == '__main__':
    unittest.main()
