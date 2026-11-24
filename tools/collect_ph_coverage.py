# -*- coding: utf-8 -*-
"""P-H H3 coverage probe collector (<=8 fetches, zero model calls).

Fetches openbsd.org pages that the G1 acceptance window rejected, RETAINING
raw HTML regardless of acceptance (coverage probes, not corpus pages).
Discipline: <=2 attempts/slot, transient errors only (4xx/deterministic ->
next URL, no retry); every fetch records url/final_url/sha256/raw_chars/
timestamp; refuses overwrite of samples and output. After collection, runs
extract_html vs extract_with_density_fallback offline and reports the
pre-registered coverage criterion (>=2/4 pages: baseline 0-block/no_candidate
AND density >=3 blocks). Plan: docs/P_H_PRE_PE_PLAN.md (H3).
"""
import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.webextractor.extractor import extract_html
from src.webextractor.extractor_density import extract_with_density_fallback
from tools.node5_loop import write_json

TOOL_VERSION = '1.0.0'
FETCH_CAP = 8
MAX_SLOT_ATTEMPTS = 2
TARGETS = [
    ('index', 'https://www.openbsd.org/index.html'),
    ('innovations', 'https://www.openbsd.org/innovations.html'),
    ('security', 'https://www.openbsd.org/security.html'),
    ('goals', 'https://www.openbsd.org/goals.html'),
]


def fetch_raw(opener, url, log):
    entry = {'url': url, 'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 offline-extractor-learning/1.0'})
    try:
        with opener.open(req, timeout=25) as resp:
            payload = resp.read()
            entry['final_url'] = resp.url
            entry['http_status'] = getattr(resp, 'status', 200)
    except urllib.error.HTTPError as e:
        entry.update(error='HTTPError', http_status=e.code, deterministic=(400 <= e.code < 500))
        log.append(entry)
        return None, entry
    except Exception as e:
        entry.update(error=type(e).__name__, deterministic=False)
        log.append(entry)
        return None, entry
    entry['sha256'] = hashlib.sha256(payload).hexdigest()
    entry['raw_chars'] = len(payload.decode('utf-8', errors='replace'))
    entry['deterministic'] = False
    log.append(entry)
    return payload, entry


def collect(output_path, opener=None, samples_dir=None):
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError('refusing overwrite: %s' % output_path)
    samples_dir = Path(samples_dir) if samples_dir else ROOT / 'samples'
    opener = opener or urllib.request.build_opener()
    log, retained = [], []
    for slug, url in TARGETS:
        html_path = samples_dir / ('ph_openbsd_%s.html' % slug)
        meta_path = samples_dir / ('ph_openbsd_%s.html.source.json' % slug)
        if html_path.exists() or meta_path.exists():
            raise FileExistsError('refusing overwrite sample: %s' % html_path)
        payload = None
        for attempt in range(MAX_SLOT_ATTEMPTS):
            if len(log) >= FETCH_CAP:
                break
            payload, entry = fetch_raw(opener, url, log)
            entry['slot'] = slug
            entry['attempt'] = attempt + 1
            if payload is not None or entry.get('deterministic'):
                break
        if payload is None:
            continue
        html_path.write_bytes(payload)
        meta = {'url': url, 'final_url': log[-1].get('final_url'),
                'sha256': log[-1]['sha256'], 'raw_chars': log[-1]['raw_chars'],
                'fetched_at': log[-1]['fetched_at'], 'purpose': 'H3 coverage probe (raw retained regardless of G1 window)',
                'plan': 'docs/P_H_PRE_PE_PLAN.md'}
        write_json(meta_path, meta)
        try:
            rel = str(html_path.relative_to(ROOT))
        except ValueError:
            rel = str(html_path)
        retained.append({'slot': slug, 'html': rel, 'sha256': log[-1]['sha256']})
    coverage = []
    for item in retained:
        hp = Path(item['html'])
        sb = (hp if hp.is_absolute() else ROOT / hp).read_bytes()
        base = extract_html(sb)
        dens = extract_with_density_fallback(sb)
        base_blocks = len(base.blocks)
        dens_blocks = len(dens.blocks)
        gap = base.status in ('no_candidate', 'empty_body') or base_blocks == 0
        coverage.append({'slot': item['slot'], 'baseline_status': base.status,
                         'baseline_blocks': base_blocks, 'density_status': dens.status,
                         'density_blocks': dens_blocks, 'density_title': dens.title,
                         'coverage_gap_confirmed': gap,
                         'criterion_met': gap and dens_blocks >= 3})
    met = sum(1 for c in coverage if c['criterion_met'])
    verdict = 'H3_COVERAGE_FIX_CONFIRMED' if met >= 2 else 'H3_COVERAGE_FIX_NOT_CONFIRMED'
    report = {'tool_version': TOOL_VERSION, 'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'fetch_cap': FETCH_CAP, 'total_fetches': len(log), 'fetch_log': log,
              'retained': retained, 'coverage': coverage, 'criterion_met_count': met,
              'criterion': '>=2/4 pages: baseline 0-block/no_candidate AND density >=3 blocks',
              'verdict': verdict,
              'note': 'coverage probes only; NOT corpus pages; extract_html byte-frozen; density opt-in not wired into frozen rule_cache'}
    write_json(output_path, report)
    return report


def reeval(output_path, samples_dir=None):
    """Offline re-evaluation of retained probes after an extractor revision.

    Zero fetches. The first-pass collection report stays untouched (honest
    negative record); this writes a NEW evaluation artifact.
    """
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError('refusing overwrite: %s' % output_path)
    samples_dir = Path(samples_dir) if samples_dir else ROOT / 'samples'
    coverage = []
    for slug, _url in TARGETS:
        hp = samples_dir / ('ph_openbsd_%s.html' % slug)
        if not hp.exists():
            continue
        sb = hp.read_bytes()
        base = extract_html(sb)
        dens = extract_with_density_fallback(sb)
        gap = base.status in ('no_candidate', 'empty_body') or len(base.blocks) == 0
        coverage.append({'slot': slug, 'baseline_status': base.status,
                         'baseline_blocks': len(base.blocks), 'density_status': dens.status,
                         'density_blocks': len(dens.blocks), 'density_title': dens.title,
                         'coverage_gap_confirmed': gap,
                         'criterion_met': gap and len(dens.blocks) >= 3})
    met = sum(1 for c in coverage if c['criterion_met'])
    report = {'tool_version': TOOL_VERSION, 'mode': 'offline_reeval',
              'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'coverage': coverage, 'criterion_met_count': met,
              'criterion': '>=2/4 pages: baseline 0-block/no_candidate AND density >=3 blocks',
              'verdict': 'H3_COVERAGE_FIX_CONFIRMED' if met >= 2 else 'H3_COVERAGE_FIX_NOT_CONFIRMED',
              'note': 'first pass ph.coverage.collect.v1.json NOT_CONFIRMED (density set lacked //body); extractor_density revised (dev iteration disclosed); zero new fetches'}
    write_json(output_path, report)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', default=str(ROOT / 'outputs' / 'ph.coverage.collect.v1.json'))
    ap.add_argument('--reeval', action='store_true')
    args = ap.parse_args(argv)
    try:
        report = reeval(args.output) if args.reeval else collect(args.output)
    except FileExistsError as e:
        print(str(e), file=sys.stderr)
        return 3
    print(json.dumps({'verdict': report['verdict'], 'fetches': report.get('total_fetches', 0),
                      'retained': len(report.get('retained', [])), 'criterion_met': report['criterion_met_count'],
                      'coverage': report['coverage'], 'output': args.output}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
