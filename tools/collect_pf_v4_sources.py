# -*- coding: utf-8 -*-
"""One-shot P-F v4 source collection (route A, approved 2026-11-23 hqli631).

Collects TWO real short article pages from two NEVER-EXPOSED template families
(raw 5,000-20,000 chars so frozen max_source_chars=20000 never truncates ->
pass reachable). Pre-registered candidates (docs/P_F_V14_PLAN.md + P-F execution
plan F3): sqlite.org (whentouse -> famous), debian.org (social_contract ->
intro/about), fallback apache.org (how-it-works). Excluded families: python/
sphinx, iana, rfc, whatwg, web.dev, mdn, w3c, gnu, npr-text, github-blog, nasa.

Acceptance per page: raw chars in [5000, 20000]; extract_html yields >=3 blocks,
a consecutive paragraph pair (reorder feasible), a paragraph with >=40 stripped
chars (missing_paragraph feasible), nonempty title. Minimal-fetch discipline:
direct URLs only, <=4 attempts per slot, <=10 total fetches; EVERY fetch is
recorded (url/final_url/sha256/raw_chars/acceptance checks/reject reason). No
model calls. Samples are written ONLY when BOTH slots are accepted; otherwise
exit 2 with an honest log (no partial slate). Refuses overwrite.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.webextractor.extractor import extract_html

TOOL_VERSION = '1.0.0'
MIN_CHARS, MAX_CHARS = 5000, 20000
MAX_ARTICLE_ATTEMPTS = 4
TOTAL_FETCH_CAP = 10
EXCLUDED_HOSTS = {
    'docs.python.org', 'www.python.org', 'python.org', 'www.iana.org', 'iana.org',
    'www.rfc-editor.org', 'rfc-editor.org', 'html.spec.whatwg.org', 'web.dev',
    'developer.mozilla.org', 'www.w3.org', 'w3.org', 'www.gnu.org', 'gnu.org',
    'text.npr.org', 'github.blog', 'www.nasa.gov', 'nasa.gov',
}
SLOTS = [
    {'page_id': 'pf_v4_sqlite', 'template': 'sqlite-org',
     'urls': ['https://www.sqlite.org/whentouse.html', 'https://www.sqlite.org/famous.html']},
    {'page_id': 'pf_v4_debian', 'template': 'debian-org',
     'urls': ['https://www.debian.org/social_contract', 'https://www.debian.org/intro/about']},
]
FALLBACK = {'page_id': 'pf_v4_apache', 'template': 'apache-org',
            'urls': ['https://www.apache.org/foundation/how-it-works.html']}


def _opener():
    proxy = os.getenv('OFFLINE_EXTRACTOR_PROXY')
    handler = urllib.request.ProxyHandler({'http': proxy, 'https': proxy} if proxy else {})
    return urllib.request.build_opener(handler)


def fetch(opener, url, log):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 offline-extractor-learning/1.0'})
    entry = {'url': url, 'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    try:
        with opener.open(req, timeout=25) as resp:
            payload = resp.read()
            entry['final_url'] = resp.url
    except Exception as e:
        entry.update(error=type(e).__name__, accepted=False, reject_reason='fetch failed')
        log.append(entry)
        return None, entry
    text = payload.decode('utf-8', errors='replace')
    entry['sha256'] = hashlib.sha256(payload).hexdigest()
    entry['raw_chars'] = len(text)
    checks = acceptance_checks(payload, text)
    entry.update(checks)
    entry['accepted'] = not checks['reject_reason']
    log.append(entry)
    return (payload, text) if entry['accepted'] else (None, entry)


def acceptance_checks(payload, text):
    out = {'n_blocks': 0, 'has_paragraph_pair': False, 'has_para_ge40': False,
           'title_ok': False, 'reject_reason': None}
    if not (MIN_CHARS <= len(text) <= MAX_CHARS):
        out['reject_reason'] = 'raw_chars %d outside [%d, %d]' % (len(text), MIN_CHARS, MAX_CHARS)
        return out
    try:
        res = extract_html(payload)
        doc = res.to_dict()
    except Exception as e:
        out['reject_reason'] = 'extract_html failed: ' + type(e).__name__
        return out
    blocks = doc['blocks']
    out['n_blocks'] = len(blocks)
    out['title_ok'] = bool((doc.get('title') or '').strip())
    out['has_paragraph_pair'] = any(
        blocks[i]['kind'] == 'paragraph' and blocks[i + 1]['kind'] == 'paragraph'
        for i in range(len(blocks) - 1))
    out['has_para_ge40'] = any(b['kind'] == 'paragraph' and len(b['text'].strip()) >= 40 for b in blocks)
    reasons = []
    if len(blocks) < 3:
        reasons.append('fewer than 3 blocks')
    if not out['has_paragraph_pair']:
        reasons.append('no consecutive paragraph pair (reorder infeasible)')
    if not out['has_para_ge40']:
        reasons.append('no paragraph >=40 chars (missing_paragraph infeasible)')
    if not out['title_ok']:
        reasons.append('empty title')
    out['reject_reason'] = '; '.join(reasons) or None
    return out


def collect_slot(opener, slot, log, budget):
    for url in slot['urls'][:MAX_ARTICLE_ATTEMPTS]:
        if budget[0] >= TOTAL_FETCH_CAP:
            return None
        host = urlparse(url).hostname or ''
        if host in EXCLUDED_HOSTS:
            log.append({'url': url, 'accepted': False, 'reject_reason': 'exposed template family (pre-registered exclusion)'})
            continue
        budget[0] += 1
        got, entry = fetch(opener, url, log)
        if got is not None:
            return {'slot': slot, 'payload': got[0], 'text': got[1], 'entry': entry}
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--log', type=Path, required=True, help='fresh collection provenance log path (refuse overwrite)')
    ap.add_argument('--samples-dir', type=Path, default=ROOT / 'samples')
    args = ap.parse_args(argv)
    log_path = Path(args.log)
    if log_path.exists():
        print('Log exists; choose a new filename.', file=sys.stderr)
        return 3
    samples = Path(args.samples_dir)
    targets = [samples / (s['page_id'] + '.html') for s in SLOTS] + \
              [samples / (FALLBACK['page_id'] + '.html')]
    for t in targets:
        if t.exists():
            print('Sample already exists: %s (refuse overwrite)' % t, file=sys.stderr)
            return 3
    opener = _opener()
    log, budget, accepted = [], [0], {}
    for slot in SLOTS:
        got = collect_slot(opener, slot, log, budget)
        if got is None and budget[0] < TOTAL_FETCH_CAP:
            got = collect_slot(opener, FALLBACK, log, budget)
        if got is not None:
            accepted[got['slot']['page_id']] = got
    status = 'complete' if len(accepted) == 2 else 'incomplete'
    doc = {'tool_version': TOOL_VERSION, 'route': 'A (approved 2026-11-23 hqli631)',
           'status': status, 'total_fetches': budget[0], 'fetch_cap': TOTAL_FETCH_CAP,
           'min_chars': MIN_CHARS, 'max_chars': MAX_CHARS,
           'excluded_hosts': sorted(EXCLUDED_HOSTS),
           'accepted_page_ids': sorted(accepted), 'fetches': log,
           'note': 'Zero model calls. Samples written only when both slots accepted.'}
    if status == 'complete':
        for pid, got in accepted.items():
            slot = got['slot']
            (samples / (pid + '.html')).write_bytes(got['payload'])
            side = {'page_id': pid, 'template': slot['template'],
                    'url': got['entry']['url'], 'final_url': got['entry']['final_url'],
                    'sha256': got['entry']['sha256'], 'raw_chars': got['entry']['raw_chars'],
                    'fetched_at': got['entry']['fetched_at'],
                    'acceptance': {k: got['entry'][k] for k in ('n_blocks', 'has_paragraph_pair', 'has_para_ge40', 'title_ok')}}
            (samples / (pid + '.html.source.json')).write_text(
                json.dumps(side, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'status': status, 'total_fetches': budget[0],
                      'accepted': sorted(accepted), 'log': str(log_path)}, ensure_ascii=False))
    return 0 if status == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
