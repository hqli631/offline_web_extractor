# -*- coding: utf-8 -*-
"""One-shot P3 v3 source collection (route b, approved 2026-11-22 hqli631).

Collects TWO real short article pages (raw 5,000-18,000 chars so the frozen
max_source_chars=20000 does not truncate -> pass reachable), from two
templates never used in calibration/P2. Minimal-fetch discipline: one index
fetch per source for navigation + bounded article attempts; EVERY fetch is
recorded in the provenance file. No model calls. Refuses overwrite.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import urllib.request

from lxml import html as lhtml

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / 'samples'
# Hard constraint (pre-registered, docs/P3_GATE_PLAN.md section 3): raw <= 20000
# chars so frozen max_source_chars=20000 never truncates. 5k-18k was the target
# window; 18k-20k accepted with honest recording (GNU essay 19,271 chars).
MIN_CHARS, MAX_CHARS = 5000, 20000
MAX_ARTICLE_ATTEMPTS = 4
SOURCES = [
    {'page_id': 'p3_npr_text', 'index_url': 'https://text.npr.org/', 'template': 'npr-text'},
    # cnn-lite rejected 2026-11-22: 4 article attempts all ~650k chars (inline JS),
    # outside 5k-18k window; attempts logged in outputs/p3.collection.v1.log.
    {'page_id': 'p3_gnu_essay', 'index_url': None, 'template': 'gnu-philosophy',
     'direct_urls': ['https://www.gnu.org/philosophy/your-freedom-needs-free-software.html',
                     'https://www.gnu.org/philosophy/why-gnu-linux.html',
                     'https://www.gnu.org/philosophy/free-doc.html',
                     'https://www.gnu.org/philosophy/pragmatic.html']},
]


def _opener():
    proxy = os.getenv('OFFLINE_EXTRACTOR_PROXY')
    handler = urllib.request.ProxyHandler({'http': proxy, 'https': proxy} if proxy else {})
    return urllib.request.build_opener(handler)


def fetch(opener, url, log):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 offline-extractor-learning/1.0'})
    with opener.open(req, timeout=25) as resp:
        payload = resp.read()
        final = resp.url
    text = payload.decode('utf-8', errors='replace')
    log.append({'url': url, 'final_url': final, 'sha256': hashlib.sha256(payload).hexdigest(),
                'raw_chars': len(text), 'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds')})
    return text, final


def article_links(index_text, base, host):
    doc = lhtml.fromstring(index_text)
    seen, out = set(), []
    for a in doc.xpath('//a[@href]'):
        u = urljoin(base, a.get('href'))
        p = urlparse(u)
        if p.netloc != host or u in seen:
            continue
        path = p.path.rstrip('/')
        if path and path != '' and len(path.split('/')) >= 2 and not path.endswith(('.css', '.js', '.png', '.jpg')):
            seen.add(u)
            out.append(u)
    return out


def collect_one(src):
    page_id, index_url, template = src['page_id'], src['index_url'], src['template']
    target = SAMPLES / (page_id + '.html')
    prov = SAMPLES / (page_id + '.html.source.json')
    if target.exists() and prov.exists():
        meta = json.loads(prov.read_text(encoding='utf-8'))
        assert hashlib.sha256(target.read_bytes()).hexdigest() == meta['sha256']
        return {'page_id': page_id, 'status': 'retained', 'raw_chars': meta['raw_chars'],
                'fetches': len(meta['fetch_log'])}
    if target.exists() or prov.exists():
        raise RuntimeError('Incomplete prior artifacts require review: ' + page_id)
    opener = _opener()
    log = []
    if src.get('direct_urls'):
        links = src['direct_urls']
        final_index = None
    else:
        index_text, final_index = fetch(opener, index_url, log)
        host = urlparse(final_index).netloc
        links = article_links(index_text, final_index, host)
    attempts = []
    for url in links[:MAX_ARTICLE_ATTEMPTS]:
        try:
            text, final = fetch(opener, url, log)
        except Exception as e:
            attempts.append({'url': url, 'error': str(e)})
            continue
        n = len(text)
        doc = lhtml.fromstring(text)
        paras = [p for p in doc.xpath('//p') if (p.text_content() or '').strip()]
        if MIN_CHARS <= n <= MAX_CHARS and len(paras) >= 3:
            target.write_text(text, encoding='utf-8', newline='')
            prov.write_text(json.dumps({
                'page_id': page_id, 'template': template, 'index_url': index_url or '(direct urls)',
                'article_url': url, 'final_url': final,
                'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                'raw_chars': n, 'paragraph_count': len(paras),
                'size_window': [MIN_CHARS, MAX_CHARS], 'fetch_log': log,
                'rejected_attempts': attempts,
                'approval': 'hqli631 2026-11-22 route b (2 short real pages; zero model calls)',
            }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
            return {'page_id': page_id, 'status': 'collected', 'article_url': final, 'raw_chars': n,
                    'paragraphs': len(paras), 'fetches': len(log)}
        attempts.append({'url': url, 'raw_chars': n, 'paragraphs': len(paras),
                         'reason': 'outside size window or too few paragraphs'})
    raise RuntimeError('No suitable article for %s; attempts=%s' % (page_id, json.dumps(attempts)))


def main():
    results = []
    for src in SOURCES:
        results.append(collect_one(src))
    print(json.dumps({'collected': results, 'total_fetches': sum(r['fetches'] for r in results)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
