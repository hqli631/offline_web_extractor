# -*- coding: utf-8 -*-
"""P-F A2-minimal extractor fallback regression (approved hqli631 2026-11-23).

Pins byte-level extraction output for all 27 pre-existing sample snapshots
(baseline captured BEFORE the id=content last-resort fallback was added).
The fallback fires ONLY when the primary container union finds nothing.
"""
import hashlib
import json
import unittest
from pathlib import Path

from src.webextractor.extractor import extract_html, _candidate_nodes
from lxml import html as lhtml

ROOT = Path(__file__).resolve().parents[1]

BASELINE = {'samples/code_lab.html': '58cb6820c08a574447d50ffb304229d3ac4a773539c3d311deda48e07f3603ce', 'samples/github-copilot-blog.candidate.html': '9af55ce460c2ab98d00900609827bb9eeea5f14e9c81812c92aa0838141d863a', 'samples/gnu.candidate.html': 'ee50f61048315c018a2d1382acb5af58d44f790621172449006f288f087632e0', 'samples/iana_example_domains.html': '587d1b704e70a42a2eb96f5f32d0f4fc5cbed803126f4f48d463b49ad6472573', 'samples/list_lab.html': '14326a18311add487251dec2d7b06b1d26adde3060a5e36e1f47290488cbf5bf', 'samples/list_lab.practice.html': '8f7b4ae7855cc3b9223a5fb9a2f4693181182facdfe77f2725ae1a7d90ee4e97', 'samples/mdn.candidate.html': '100ab67347f6fd67afcf747ed11ac75437f2d5fd9e0064bbcb29079ab738e745', 'samples/nasa-voyager-news.candidate.html': 'f74590e79631e1aa93a3b6d521d7936890178c135bcfa6707581b5c8ce5267e3', 'samples/news.html': 'cc09bb6170f5728e28fb1a343f8c3a3dbe8ca183f2b03b9528ecfc66c99f2e64', 'samples/p3_gnu_essay.html': '41338b8ffbc95ef26150f8e250feaf3b574684992ece9d435d31eb5920a51467', 'samples/p3_npr_text.html': 'd02e8bbbd919ac4eca8cd03bdac3751d817e3a4f8d3e8ca45d703568fc990b76', 'samples/python_appetite_zh.html': 'ae7376319a3cfd703947d6ef2658f64b8125317147f453ae3c97f1e8a322daa3', 'samples/python_blurb.html': '68b425e9951a8b2593d75c57827dd52cbe75a4d6013da532f30117270e8987bf', 'samples/python_interpreter_zh.html': '306bcea26576addb4a0510fd84788771c717c5453dc4e6f65ce041ad464f5578', 'samples/rfc.candidate.html': 'bb56cc5387e43ff0421eca299351c5ab249ef2eca752999c751f6c846f7a33ac', 'samples/w3c-link-text.candidate.html': '0d9b3202567cd41b29c19689e8c7f9ba614252b30ed3d3c08669072fecae9b66', 'samples/w3c_accessibility_intro_zh.html': '783b87f9db3bf3aa81046621fafe715a9dab9703e89abb264d880c4e04b04661', 'samples/w3c_accessibility_intro_zh.preview.html': '783b87f9db3bf3aa81046621fafe715a9dab9703e89abb264d880c4e04b04661', 'samples/webdev-learn-html.candidate.html': '0aec1848b59b422cf1f153d7f284607e8a64dc7736e65b91c065187e6da72252', 'samples/whatwg-html.candidate.html': '1e34fdacce4a222818de0f6e95899d4823131930074997284ed5bd11fc1a7741', 'samples/clustering/iana-abuse.html': '3bffb57e24f591f82b3b5a12f7eaa5d3b8d86316ae3359a095bf1d648e0451ab', 'samples/clustering/iana-whois.html': 'a8a31da925263e0e842099680ff25eb300e87d894a04a965e45de79fe144d570', 'samples/clustering/python-controlflow.html': '66276ab1746dc3f2c4268da32c20336da45032a906def6af06657776379af83d', 'samples/clustering/python-datastructures.html': '8810d381d8006550ff138594a7345b305bae54b9bc60ced63071c4d30d8d4b9e', 'samples/clustering/python-introduction.html': '3f93dd145a54bd1bc89f38e21727f2c2549941a10ee6176953ae8908007badd8', 'samples/clustering/python-library-index.html': '8a04dc9ae1fcf4ecaa592b7d23d726e242a3811d59a08b1e62d411dfb73ed68f', 'samples/clustering/python-search.html': '18c2925829295a1286bf9fec7b3da35ff472c27b9b35d427c8862cd00f77d4c1'}


def sig(payload):
    r = extract_html(payload)
    return hashlib.sha256(json.dumps({'title': r.title, 'blocks': r.to_dict()['blocks']},
                                   ensure_ascii=False, sort_keys=True).encode()).hexdigest()


class ExtractorFallbackTest(unittest.TestCase):
    def test_27_snapshots_byte_identical(self):
        self.assertEqual(len(BASELINE), 27)
        for rel, expected in BASELINE.items():
            payload = (ROOT / rel).read_bytes()
            self.assertEqual(sig(payload), expected, rel)

    def test_debian_now_extractable(self):
        payload = (ROOT / 'samples/pf_v4_debian.html').read_bytes()
        r = extract_html(payload)
        self.assertEqual(r.title, 'Debian Social Contract')
        self.assertGreaterEqual(len(r.to_dict()['blocks']), 3)

    def test_fallback_only_when_primary_empty(self):
        both = lhtml.fromstring('<html><body><article><p>Article paragraph text here.</p></article>'
                                '<div id="content"><p>Other content paragraph.</p></div></body></html>')
        nodes = _candidate_nodes(both)
        self.assertTrue(all(n.tag == 'article' for n in nodes))
        only = lhtml.fromstring('<html><body><div id="content"><h1>T</h1><p>Body text.</p></div></body></html>')
        self.assertEqual(len(_candidate_nodes(only)), 1)
        neither = lhtml.fromstring('<html><body><div id="wrapper"><p>x</p></div></body></html>')
        self.assertEqual(_candidate_nodes(neither), [])

    def test_primary_wins_over_content(self):
        payload = ('<html><body><article><p>Article paragraph text here.</p></article>'
                   '<div id="content"><p>Other content paragraph.</p></div></body></html>').encode()
        r = extract_html(payload)
        texts = ' '.join(b['text'] for b in r.to_dict()['blocks'])
        self.assertIn('Article paragraph', texts)
        self.assertNotIn('Other content', texts)


if __name__ == '__main__':
    unittest.main()
