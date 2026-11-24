# -*- coding: utf-8 -*-
"""P-H H3 tests: density fallback zero-drift, private-container coverage,
collector discipline with mock opener (zero network in tests)."""
import io
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.webextractor.extractor import extract_html
from src.webextractor.extractor_density import extract_with_density_fallback
from tools import collect_ph_coverage as cpc

PRIVATE = ('<html><body><table><tr><td id="nav"><a href="/">Home</a></td>'
           '<td><h1>OpenBSD goals</h1>'
           '<p>The project aims to produce a freely redistributable operating system.</p>'
           '<p>Security correctness is a primary design goal of the system.</p>'
           '<p>Documentation and code quality are emphasized over feature count.</p>'
           '</td></tr></table></body></html>')


class ZeroDriftTests(unittest.TestCase):
    def test_extractable_snapshots_identical(self):
        checked = 0
        for p in sorted((ROOT / 'samples').glob('*.html')):
            sb = p.read_bytes()
            base = extract_html(sb)
            if base.status == 'ok' and base.blocks:
                dens = extract_with_density_fallback(sb)
                self.assertEqual(dens.to_dict(), base.to_dict(), p.name)
                checked += 1
        self.assertGreaterEqual(checked, 20)

    def test_empty_input_unchanged(self):
        base = extract_html('')
        self.assertEqual(extract_with_density_fallback('').to_dict(), base.to_dict())


class CoverageTests(unittest.TestCase):
    def test_private_container_gap_and_fix(self):
        base = extract_html(PRIVATE)
        self.assertIn(base.status, ('no_candidate', 'empty_body'))
        dens = extract_with_density_fallback(PRIVATE)
        self.assertEqual(dens.status, 'ok')
        self.assertGreaterEqual(len(dens.blocks), 3)
        self.assertIn('OpenBSD goals', dens.title)

    def test_link_heavy_rejected(self):
        page = ('<html><body><div>' + '<a href="/x">link text number %d</a> ' * 40 +
                '<p>only short real text</p></div></body></html>') % tuple(range(40))
        base = extract_html(page)
        dens = extract_with_density_fallback(page)
        self.assertEqual(dens.to_dict(), base.to_dict())

    def test_short_text_rejected(self):
        page = '<html><body><div><p>tiny</p></div></body></html>'
        base = extract_html(page)
        self.assertEqual(extract_with_density_fallback(page).to_dict(), base.to_dict())


class BareBodyTests(unittest.TestCase):
    def test_bare_body_classic_layout(self):
        page = ('<html><body><h2>Site</h2><hr>'
                '<p>First real paragraph about the project goals and design philosophy.</p>'
                '<p>Second real paragraph describing security correctness aims in detail.</p>'
                '<p>Third real paragraph on documentation quality and code review practice.</p>'
                '<p>Fourth real paragraph explaining the release engineering process.</p>'
                '</body></html>')
        base = extract_html(page)
        self.assertIn(base.status, ('no_candidate', 'empty_body'))
        dens = extract_with_density_fallback(page)
        self.assertEqual(dens.status, 'ok')
        self.assertGreaterEqual(len(dens.blocks), 3)

    def test_retained_openbsd_probes_coverage(self):
        probes = sorted((ROOT / 'samples').glob('ph_openbsd_*.html'))
        if not probes:
            self.skipTest('coverage probes not collected')
        met = 0
        for hp in probes:
            sb = hp.read_bytes()
            base = extract_html(sb)
            dens = extract_with_density_fallback(sb)
            gap = base.status in ('no_candidate', 'empty_body') or not base.blocks
            if gap and len(dens.blocks) >= 3:
                met += 1
            if base.status == 'ok' and base.blocks:
                self.assertEqual(dens.to_dict(), base.to_dict())
        self.assertGreaterEqual(met, 2)


class _FakeResponse:
    def __init__(self, payload, url):
        self._payload = payload
        self.url = url
        self.status = 200

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class CollectorTests(unittest.TestCase):
    def test_deterministic_4xx_no_retry(self):
        calls = []

        class Opener:
            def open(self, req, timeout=None):
                calls.append(req.full_url)
                raise urllib.error.HTTPError(req.full_url, 404, 'nf', {}, None)

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'c.json'
            rep = cpc.collect(out, opener=Opener(), samples_dir=Path(td))
            self.assertEqual(len(calls), 4)  # one per slot, no retry
            self.assertEqual(rep['retained'], [])
            self.assertEqual(rep['verdict'], 'H3_COVERAGE_FIX_NOT_CONFIRMED')

    def test_transient_retry_bounded_and_cap(self):
        calls = []

        class Opener:
            def open(self, req, timeout=None):
                calls.append(req.full_url)
                raise OSError('transient')

        with tempfile.TemporaryDirectory() as td:
            rep = cpc.collect(Path(td) / 'c.json', opener=Opener(), samples_dir=Path(td))
            self.assertEqual(len(calls), 8)  # 4 slots x 2 attempts = cap
            self.assertEqual(rep['total_fetches'], 8)

    def test_retain_raw_and_provenance(self):
        payload = PRIVATE.encode('utf-8')

        class Opener:
            def open(self, req, timeout=None):
                return _FakeResponse(payload, req.full_url)

        with tempfile.TemporaryDirectory() as td:
            samples = Path(td) / 'samples'
            samples.mkdir()
            rep = cpc.collect(Path(td) / 'c.json', opener=Opener(), samples_dir=samples)
            self.assertEqual(len(rep['retained']), 4)
            self.assertEqual(rep['total_fetches'], 4)
            self.assertTrue(all(c['criterion_met'] for c in rep['coverage']))
            self.assertEqual(rep['verdict'], 'H3_COVERAGE_FIX_CONFIRMED')
            meta = samples / 'ph_openbsd_index.html.source.json'
            self.assertTrue(meta.exists())

    def test_reeval_zero_fetches(self):
        with tempfile.TemporaryDirectory() as td:
            samples = Path(td) / 'samples'
            samples.mkdir()
            (samples / 'ph_openbsd_innovations.html').write_text(PRIVATE, encoding='utf-8')
            rep = cpc.reeval(Path(td) / 'r.json', samples_dir=samples)
            self.assertEqual(rep['mode'], 'offline_reeval')
            self.assertEqual(rep['criterion_met_count'], 1)
            self.assertEqual(rep['verdict'], 'H3_COVERAGE_FIX_NOT_CONFIRMED')

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'c.json'
            out.write_text('{}', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                cpc.collect(out)


if __name__ == '__main__':
    unittest.main()
