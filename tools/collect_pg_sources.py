# -*- coding: utf-8 -*-
"""P-G G1 one-shot real-template source collection (plan docs/P_G_REAL_TEMPLATE_PLAN.md).

Collects up to 3 UNEXPOSED classic-layout families x 4 natural pages (apache.org,
openbsd.org, netbsd.org). Acceptance per page: raw chars in [3000, 30000];
extract_html yields >=3 blocks and a nonempty title. Minimal-fetch discipline:
direct URLs only, <=4 attempts per slot, <=20 total fetches; EVERY fetch recorded
(url/final_url/sha256/raw_chars/acceptance checks/reject reason). No model calls.
A family with <3 accepted pages is degraded (accepted pages kept as singletons/
controls, disclosed). Exposed fallback families (freebsd/debian, v4-exposed) are
OFF by default and require --allow-exposed-fallback (disclosed). Refuses overwrite.
Exit 0 if >=2 families accepted (>=3 pages each); exit 2 honest stop otherwise.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.webextractor.extractor import extract_html

TOOL_VERSION = '1.0.0'
MIN_CHARS, MAX_CHARS = 3000, 30000
MAX_SLOT_ATTEMPTS = 4
TOTAL_FETCH_CAP = 20
EXCLUDED_HOSTS = {
    'docs.python.org', 'www.python.org', 'python.org', 'www.iana.org', 'iana.org',
    'www.rfc-editor.org', 'rfc-editor.org', 'html.spec.whatwg.org', 'web.dev',
    'developer.mozilla.org', 'www.w3.org', 'w3.org', 'www.gnu.org', 'gnu.org',
    'text.npr.org', 'github.blog', 'www.nasa.gov', 'nasa.gov',
    'www.sqlite.org', 'sqlite.org',
}
FAMILIES = [
    {'family': 'apache-org', 'exposed': False, 'pages': [
        {'page_id': 'pg_apache_howitworks', 'urls': ['https://www.apache.org/foundation/how-it-works.html']},
        {'page_id': 'pg_apache_faq', 'urls': ['https://www.apache.org/foundation/faq.html']},
        {'page_id': 'pg_apache_marks', 'urls': ['https://www.apache.org/foundation/marks-policy.html']},
        {'page_id': 'pg_apache_license', 'urls': ['https://www.apache.org/licenses/LICENSE-2.0.html']}]},
    {'family': 'openbsd-org', 'exposed': False, 'pages': [
        {'page_id': 'pg_openbsd_index', 'urls': ['https://www.openbsd.org/index.html', 'https://www.openbsd.org/']},
        {'page_id': 'pg_openbsd_goals', 'urls': ['https://www.openbsd.org/goals.html']},
        {'page_id': 'pg_openbsd_security', 'urls': ['https://www.openbsd.org/security.html']},
        {'page_id': 'pg_openbsd_innovations', 'urls': ['https://www.openbsd.org/innovations.html']}]},
    {'family': 'netbsd-org', 'exposed': False, 'pages': [
        {'page_id': 'pg_netbsd_index', 'urls': ['https://www.netbsd.org/', 'https://www.netbsd.org/index.html']},
        {'page_id': 'pg_netbsd_about', 'urls': ['https://www.netbsd.org/about/']},
        {'page_id': 'pg_netbsd_security', 'urls': ['https://www.netbsd.org/security/']},
        {'page_id': 'pg_netbsd_changes', 'urls': ['https://www.netbsd.org/changes/']}]},
]
FALLBACK_FAMILIES = [
    {'family': 'freebsd-org', 'exposed': True, 'pages': [
        {'page_id': 'pg_freebsd_about', 'urls': ['https://www.freebsd.org/about/']},
        {'page_id': 'pg_freebsd_features', 'urls': ['https://www.freebsd.org/features/']},
        {'page_id': 'pg_freebsd_applications', 'urls': ['https://www.freebsd.org/applications/']},
        {'page_id': 'pg_freebsd_projects', 'urls': ['https://www.freebsd.org/projects/']}]},
]


def _opener():
    proxy = os.getenv('OFFLINE_EXTRACTOR_PROXY')
    handler = urllib.request.ProxyHandler({'http': proxy, 'https': proxy} if proxy else {})
    return urllib.request.build_opener(handler)


def acceptance_checks(payload, text):
    checks = {'raw_chars': len(text), 'block_count': 0, 'title_ok': False, 'reject_reason': None}
    if not (MIN_CHARS <= len(text) <= MAX_CHARS):
        checks['reject_reason'] = 'raw_chars out of [%d, %d]' % (MIN_CHARS, MAX_CHARS)
        return checks
    try:
        result = extract_html(payload).to_dict()
    except Exception as e:
        checks['reject_reason'] = 'extract error: ' + type(e).__name__
        return checks
    checks['block_count'] = len(result.get('blocks') or [])
    checks['title_ok'] = bool((result.get('title') or '').strip())
    if checks['block_count'] < 3:
        checks['reject_reason'] = 'fewer than 3 blocks'
    elif not checks['title_ok']:
        checks['reject_reason'] = 'empty title'
    return checks


def fetch(opener, url, log):
    from urllib.parse import urlparse
    host = urlparse(url).hostname or ''
    entry = {'url': url, 'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    if host in EXCLUDED_HOSTS:
        entry.update(accepted=False, reject_reason='excluded host')
        log.append(entry)
        return None, entry
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 offline-extractor-learning/1.0'})
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
    checks = acceptance_checks(payload, text)
    entry.update(checks)
    entry['accepted'] = not checks['reject_reason']
    log.append(entry)
    return (payload, entry) if entry['accepted'] else (None, entry)


def run_collection(output_path, allow_exposed_fallback=False, opener=None, samples_dir=None):
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError('refusing to overwrite existing collection log: %s' % output_path)
    opener = opener or _opener()
    samples_dir = Path(samples_dir) if samples_dir else ROOT / 'samples' / 'pg_v1'
    log, accepted, family_summary = [], [], []
    fetches = 0
    families = list(FAMILIES) + (list(FALLBACK_FAMILIES) if allow_exposed_fallback else [])
    for fam in families:
        fam_accepted = 0
        for slot in fam['pages']:
            if fetches >= TOTAL_FETCH_CAP:
                break
            for attempt in range(MAX_SLOT_ATTEMPTS):
                if fetches >= TOTAL_FETCH_CAP:
                    break
                url = slot['urls'][attempt % len(slot['urls'])]
                payload, entry = fetch(opener, url, log)
                fetches += 1
                entry['page_id'] = slot['page_id']
                entry['family'] = fam['family']
                entry['attempt'] = attempt + 1
                if payload is None:
                    continue
                samples_dir.mkdir(parents=True, exist_ok=True)
                sp = samples_dir / (slot['page_id'] + '.html')
                if sp.exists():
                    entry['accepted'] = False
                    entry['reject_reason'] = 'sample file exists (refuse overwrite)'
                    continue
                sp.write_bytes(payload)
                fam_accepted += 1
                accepted.append({'page_id': slot['page_id'], 'family': fam['family'],
                                 'exposed': fam['exposed'], 'html': 'pg_v1/' + sp.name,
                                 'sha256': entry['sha256'], 'raw_chars': entry['raw_chars'],
                                 'block_count': entry['block_count'], 'url': entry['url'],
                                 'final_url': entry.get('final_url')})
                break
        family_summary.append({'family': fam['family'], 'exposed': fam['exposed'],
                               'accepted': fam_accepted, 'degraded': fam_accepted < 3})
    ok = sum(1 for f in family_summary if f['accepted'] >= 3) >= 2
    report = {'tool_version': TOOL_VERSION,
              'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'fetch_cap': TOTAL_FETCH_CAP, 'total_fetches': fetches,
              'allow_exposed_fallback': allow_exposed_fallback,
              'acceptance': {'min_chars': MIN_CHARS, 'max_chars': MAX_CHARS,
                             'min_blocks': 3, 'title_required': True,
                             'max_slot_attempts': MAX_SLOT_ATTEMPTS},
              'families': family_summary, 'accepted_pages': accepted, 'fetch_log': log,
              'status': 'ok' if ok else 'insufficient_families'}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
    return report, ok


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-G G1 real-template collection (zero model calls).')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--allow-exposed-fallback', action='store_true',
                    help='enable v4-exposed freebsd fallback family (disclosed)')
    args = ap.parse_args(argv)
    if args.output.exists():
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    report, ok = run_collection(args.output, args.allow_exposed_fallback)
    print(json.dumps({'output': str(args.output), 'total_fetches': report['total_fetches'],
                      'families': report['families'], 'accepted_pages': len(report['accepted_pages']),
                      'status': report['status']}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
