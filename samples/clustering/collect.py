"""Collect complete public pages for structural clustering development only.

No production extractor, no expected answer generation, no validation inputs.
Existing snapshots are never overwritten. Each request has one bounded attempt.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import urllib.request

from lxml import html

ROOT = Path(__file__).resolve().parent
PAGES = [
    ('python-introduction', 'https://docs.python.org/zh-cn/3/tutorial/introduction.html', 'sphinx-tutorial'),
    ('python-controlflow', 'https://docs.python.org/zh-cn/3/tutorial/controlflow.html', 'sphinx-tutorial'),
    ('python-library-index', 'https://docs.python.org/zh-cn/3/library/index.html', 'sphinx-library-index'),
    ('iana-abuse', 'https://www.iana.org/help/abuse', 'iana-help'),
    ('iana-whois', 'https://www.iana.org/help/whois', 'iana-help'),
    ( "python-datastructures", "https://docs.python.org/zh-cn/3/tutorial/datastructures.html", "sphinx-documentation",),
]


def fetch(item):
    page_id, url, proposed_group = item
    target = ROOT / (page_id + '.html')
    source_path = ROOT / (page_id + '.html.source.json')
    if target.exists() and source_path.exists():
        source = json.loads(source_path.read_text(encoding='utf-8'))
        assert hashlib.sha256(target.read_bytes()).hexdigest() == source['sha256']
        return {'id': page_id, 'status': 'retained', 'source': source}
    if target.exists() or source_path.exists():
        raise RuntimeError('Incomplete prior artifacts require explicit review: ' + page_id)
    try:
        # 从环境变量读取代理；没有配置时明确直连。
        proxy_url = os.getenv("OFFLINE_EXTRACTOR_PROXY")

        if proxy_url:
            proxy_handler = urllib.request.ProxyHandler({
                "http": proxy_url,
                "https": proxy_url,
            })
        else:
            proxy_handler = urllib.request.ProxyHandler({})

        opener = urllib.request.build_opener(proxy_handler)

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 offline-extractor-learning/1.0"
            },
        )

        with opener.open(request, timeout=20) as response:
            payload = response.read()
            final_url = response.url
            status = response.status
            content_type = response.headers.get("Content-Type", "")
        if status != 200 or 'html' not in content_type.lower():
            raise ValueError(f'Unexpected response: {status} {content_type}')
        document = html.document_fromstring(payload)
        title = ' '.join(''.join(document.xpath('//title')[0].itertext()).split())
        headings = [' '.join(''.join(node.itertext()).split()) for node in document.xpath('//h1')]
        source = {
            'requested_url': url, 'final_url': final_url,
            'fetched_at': datetime.now(timezone.utc).isoformat(),
            'http_status': status, 'content_type': content_type,
            'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload),
            'source_kind': 'real', 'split': 'clustering-development',
            'proposed_manual_group': proposed_group,
            'page_title': title, 'h1_texts': headings,
            'note': 'Complete HTTP response, no truncation or production extraction. Group labels require source-structure review; not a gold extraction label.',
        }
        with target.open('xb') as stream:
            stream.write(payload)
        with source_path.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(source, ensure_ascii=False, indent=2) + '\n')
        return {'id': page_id, 'status': 'saved', 'source': source}
    except Exception as error:
        return {'id': page_id, 'status': 'failed', 'error': f'{type(error).__name__}: {error}'}


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(fetch, PAGES))
    outcome = ROOT / 'collection_results.json'
    if outcome.exists():
        raise SystemExit('Results exist; choose a new result filename rather than overwrite history')
    outcome.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for result in results:
        print(json.dumps({key: value for key, value in result.items() if key != 'source'}))
