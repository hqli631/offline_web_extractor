# -*- coding: utf-8 -*-
"""P-G G1/G2 tests: collector acceptance/caps (offline mock), variant builder
prose preservation + rule breaking + silver provenance, clustering freeze/strata/
hard checks/determinism, CLI discipline. Zero network, zero model calls.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import collect_pg_sources as col
from tools import build_pg_corpus as bld
from tools import run_pg_cluster as pgc

REP_HTML = ('<!doctype html><html><head><title>Real-ish template</title></head><body>'
            '<nav><p>Navigation noise.</p></nav>'
            '<div role="main" class="content"><h1>Article title</h1>'
            '<p>First paragraph of the article body.</p>'
            '<p>Second paragraph of the article body.</p>'
            '<p>Third paragraph of the article body.</p></div>'
            '<footer><p>Footer noise.</p></footer></body></html>')


class FakeResponse:
    def __init__(self, payload, url):
        self._payload = payload
        self.url = url

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeOpener:
    def __init__(self, mapping, fail_urls=()):
        self.mapping = mapping
        self.fail_urls = set(fail_urls)
        self.calls = []

    def open(self, req, timeout=None):
        url = req.full_url
        self.calls.append(url)
        if url in self.fail_urls:
            raise OSError('mock network failure')
        if url not in self.mapping:
            raise OSError('mock 404')
        return FakeResponse(self.mapping[url], url)


def _big_html(body_paragraphs=3):
    ps = ''.join('<p>Paragraph number %d with enough prose to count.</p>' % i for i in range(body_paragraphs))
    padding = '<!--' + (' pad' * 900) + '-->'
    return ('<!doctype html><html><head><title>Template page</title></head><body>'
            '<nav><p>nav</p></nav><div role="main" class="content"><h1>Title</h1>'
            + ps + '</div><footer><p>footer</p></footer>' + padding + '</body></html>').encode('utf-8')


class CollectorTests(unittest.TestCase):
    def test_acceptance_checks(self):
        payload = _big_html(3)
        checks = col.acceptance_checks(payload, payload.decode('utf-8'))
        self.assertIsNone(checks['reject_reason'])
        self.assertGreaterEqual(checks['block_count'], 3)
        self.assertTrue(checks['title_ok'])
        short = b'<html><head><title>t</title></head><body><div role="main"><p>one</p><p>two</p><p>three</p></div></body></html>'
        self.assertIsNotNone(col.acceptance_checks(short, short.decode())['reject_reason'])
        few = _big_html(1)
        self.assertEqual(col.acceptance_checks(few, few.decode())['reject_reason'], 'fewer than 3 blocks')

    def test_excluded_host_no_network(self):
        opener = FakeOpener({})
        log = []
        payload, entry = col.fetch(opener, 'https://www.sqlite.org/whentouse.html', log)
        self.assertIsNone(payload)
        self.assertEqual(entry['reject_reason'], 'excluded host')
        self.assertEqual(opener.calls, [])

    def test_collection_writes_accepted_and_caps(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'collect.json'
            sdir = Path(td) / 'pg_v1'
            mapping = {}
            for fam in col.FAMILIES:
                for slot in fam['pages']:
                    mapping[slot['urls'][0]] = _big_html(3)
            opener = FakeOpener(mapping)
            report, ok = col.run_collection(out, opener=opener, samples_dir=sdir)
            self.assertTrue(ok)
            self.assertEqual(len(report['accepted_pages']), 12)
            self.assertLessEqual(report['total_fetches'], col.TOTAL_FETCH_CAP)
            self.assertTrue(all(not f['degraded'] for f in report['families']))
            self.assertTrue((sdir / 'pg_apache_howitworks.html').exists())
            self.assertEqual(report['status'], 'ok')

    def test_collection_degraded_and_insufficient(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'collect.json'
            mapping = {'https://www.apache.org/foundation/how-it-works.html': _big_html(3),
                       'https://www.apache.org/foundation/faq.html': _big_html(3)}
            opener = FakeOpener(mapping)
            report, ok = col.run_collection(out, opener=opener, samples_dir=Path(td) / 'pg_v1')
            self.assertFalse(ok)
            self.assertEqual(report['status'], 'insufficient_families')
            apache = next(f for f in report['families'] if f['family'] == 'apache-org')
            self.assertEqual(apache['accepted'], 2)
            self.assertTrue(apache['degraded'])
            self.assertLessEqual(report['total_fetches'], col.TOTAL_FETCH_CAP)

    def test_collection_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'collect.json'
            out.write_text('{}', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                col.run_collection(out, opener=FakeOpener({}))


class BuilderTests(unittest.TestCase):
    def test_variant_prose_preserved_and_rule_broken(self):
        from src.webextractor.extractor import extract_html
        v = bld.build_variant(REP_HTML.encode('utf-8'), 'rep-var')
        self.assertIsNotNone(v)
        self.assertEqual(v['mutation']['old_tag'], 'div')
        self.assertEqual(v['mutation']['new_tag'], 'section')
        self.assertTrue(v['mutation']['prose_preserved'])
        self.assertEqual(v['rule_before']['container_xpath'], "//*[@role='main']")
        self.assertEqual(v['rule_status_after'], 'rule_no_match')
        self.assertTrue(v['rule_broken'])
        rep_blocks = extract_html(REP_HTML).to_dict()['blocks']
        self.assertEqual(v['silver']['blocks'], rep_blocks)
        self.assertIn('NOT human gold', v['silver']['annotation_note'])
        self.assertNotIn('role=', v['html'].split('<section')[1].split('>')[0])

    def test_variant_infeasible_without_container(self):
        src = b'<html><head><title>t</title></head><body><p>lonely paragraph</p></body></html>'
        self.assertIsNone(bld.build_variant(src, 'x-var'))

    def test_build_corpus_temp_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'pg_v1').mkdir()
            rep_bytes = REP_HTML.encode('utf-8')
            (root / 'pg_v1' / 'rep.html').write_bytes(rep_bytes)
            collect = {'generated_at': '2026-11-23T00:00:00+00:00',
                       'accepted_pages': [{'page_id': 'rep', 'family': 'fam-a', 'exposed': False,
                                           'html': 'pg_v1/rep.html', 'sha256': bld.sha(rep_bytes),
                                           'url': 'https://example.org/'}]}
            cp = root / 'collect.json'
            cp.write_text(json.dumps(collect), encoding='utf-8')
            mp = root / 'manifest.json'
            manifest = bld.build_corpus(cp, mp, samples_root=root, include_existing=False)
            self.assertEqual(len(manifest['pages']), 2)
            self.assertEqual(len(manifest['strata']['new']), 2)
            self.assertEqual(manifest['strata']['existing'], [])
            self.assertTrue(manifest['families']['fam-a']['variant_feasible'])
            self.assertTrue((root / 'pg_v1' / 'rep-var.html').exists())
            self.assertTrue((root / 'pg_v1' / 'rep-var.expected.json').exists())
            prov = json.loads((root / 'pg_v1' / 'rep-var.html.source.json').read_text(encoding='utf-8'))
            self.assertIn('NOT human gold', prov['silver_method'])
            with self.assertRaises(FileExistsError):
                bld.build_corpus(cp, mp, samples_root=root, include_existing=False)


def _tiny_corpus(td):
    """Tiny manifest referencing existing drift_lab fixtures, under ROOT/outputs."""
    pages = []
    groups = {'reference': 'fam-ref', 'role-drift': 'fam-ref', 'class-drift': 'fam-ref',
              'content-moved': 'fam-other'}
    for pid, g in groups.items():
        sb = (ROOT / 'samples' / 'drift_lab' / (pid + '.html')).read_bytes()
        pages.append({'id': pid, 'html': str(ROOT / 'samples' / 'drift_lab' / (pid + '.html')), 'sha256': bld.sha(sb),
                      'manual_group': g, 'source_kind': 'real_new' if g == 'fam-ref' else 'real_existing',
                      'split': 'development', 'layout': 'natural'})
    manifest = {'protocol': 'test', 'strata': {'all': sorted(groups), 'new': ['class-drift', 'reference', 'role-drift'],
                                              'existing': ['content-moved']}, 'pages': pages}
    mp = Path(td) / 'pg_corpus.test.json'
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return mp, str(mp.relative_to(ROOT))


class ClusterHarnessTests(unittest.TestCase):
    def test_freeze_requires_quote(self):
        with self.assertRaises(ValueError):
            pgc.make_freeze(None)

    def test_freeze_roundtrip_run_and_determinism(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'outputs') as td:
            mp, rel = _tiny_corpus(td)
            fz = pgc.make_freeze('test approval', rel)
            self.assertEqual(pgc.check_freeze(fz, rel), [])
            fz['_freeze_sha256'] = 'test'
            r1 = pgc.run_strata(mp, fz)
            r2 = pgc.run_strata(mp, fz)
            self.assertEqual(r1['verdict'], 'G2_HARD_CHECKS_PASS')
            self.assertEqual(set(r1['strata']), {'all', 'new', 'existing'})
            for r in (r1, r2):
                r.pop('generated_at')
            self.assertEqual(r1, r2)
            self.assertTrue(all(h['cl_violations_zero'] for h in r1['hard_checks'].values()))

    def test_freeze_detects_drift(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'outputs') as td:
            mp, rel = _tiny_corpus(td)
            fz = pgc.make_freeze('test approval', rel)
            fz['corpus_sha256'] = '0' * 64
            self.assertIn('corpus drift', pgc.check_freeze(fz, rel))
            fz2 = pgc.make_freeze('test approval', rel)
            fz2['cases'][0]['source_sha256'] = '0' * 64
            self.assertTrue(any(p.startswith('source drift') for p in pgc.check_freeze(fz2, rel)))
            fz3 = pgc.make_freeze('test approval', rel)
            fz3['protocol']['dom_lsh_sha256'] = '0' * 64
            self.assertTrue(any('dom_lsh' in p for p in pgc.check_freeze(fz3, rel)))

    def test_cli_discipline(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'outputs') as td:
            mp, rel = _tiny_corpus(td)
            fp = Path(td) / 'freeze.json'
            rc = pgc.main(['--freeze', '--freeze-path', str(fp), '--corpus', str(mp), '--approval-quote', 'test'])
            self.assertEqual(rc, 0)
            self.assertEqual(pgc.main(['--freeze', '--freeze-path', str(fp), '--corpus', str(mp), '--approval-quote', 'test']), 3)
            out = Path(td) / 'run.json'
            self.assertEqual(pgc.main(['--run', '--output', str(out), '--freeze-path', str(Path(td) / 'missing.json')]), 1)
            rc2 = pgc.main(['--run', '--output', str(out), '--freeze-path', str(fp), '--corpus', str(mp)])
            self.assertEqual(rc2, 0)
            self.assertEqual(pgc.main(['--run', '--output', str(out), '--freeze-path', str(fp), '--corpus', str(mp)]), 3)


if __name__ == '__main__':
    unittest.main()
