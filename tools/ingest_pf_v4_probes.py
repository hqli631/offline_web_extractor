# -*- coding: utf-8 -*-
"""P-F v4 probe ingestion (A2-minimal approved, ZERO network, zero model calls).

Ingests accepted probe payloads (already fetched and logged within the <=10
fetch budget) into samples/ as formal v4 sources, avoiding duplicate fetches.
Fail-closed: payload sha256 must match the logged probe entry; acceptance
checks are RE-RUN with the current extractor (post A2-minimal id=content
last-resort fallback); two DIFFERENT template families required. Priority
(pre-registered A2): pf_v4_debian, pf_v4_freebsd, pf_v4_lua, pf_v4_sqlite.
Refuses sample overwrite. The collection log's fetch entries are never
rewritten; only status/accepted_page_ids/ingestion metadata are appended.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.collect_pf_v4_sources import acceptance_checks

TOOL_VERSION = '1.0.0'
PRIORITY = ['pf_v4_debian', 'pf_v4_freebsd', 'pf_v4_lua', 'pf_v4_sqlite']


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def select_probes(log):
    by_id = {}
    for i, e in enumerate(log.get('fetches', [])):
        if e.get('probe') and e.get('accepted') and e.get('probe_file') and e.get('page_id'):
            by_id.setdefault(e['page_id'], (i, e))
    chosen, problems = [], []
    families = set()
    for pid in PRIORITY:
        if pid not in by_id:
            continue
        i, e = by_id[pid]
        if e['template'] in families:
            continue
        pf = ROOT / e['probe_file']
        if not pf.exists():
            problems.append('%s: probe file missing %s' % (pid, e['probe_file']))
            continue
        payload = pf.read_bytes()
        if sha256_bytes(payload) != e.get('sha256'):
            problems.append('%s: payload sha256 drift vs logged probe' % pid)
            continue
        text = payload.decode('utf-8', errors='replace')
        checks = acceptance_checks(payload, text)
        if checks['reject_reason']:
            problems.append('%s: re-acceptance failed: %s' % (pid, checks['reject_reason']))
            continue
        chosen.append({'page_id': pid, 'template': e['template'], 'entry_index': i,
                       'entry': e, 'payload': payload, 'checks': checks})
        families.add(e['template'])
        if len(chosen) == 2:
            break
    return chosen, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--log', type=Path, default=ROOT / 'outputs/pf.collection.v1.log.json')
    ap.add_argument('--samples-dir', type=Path, default=ROOT / 'samples')
    args = ap.parse_args(argv)
    log_path = Path(args.log)
    log = json.loads(log_path.read_text(encoding='utf-8'))
    fetches_before = json.dumps(log.get('fetches', []), ensure_ascii=False, sort_keys=True)
    chosen, problems = select_probes(log)
    if problems:
        for p in problems:
            print('INGEST: ' + p, file=sys.stderr)
        return 2
    if len(chosen) != 2:
        print('INGEST: need 2 different-family accepted probes; got %d' % len(chosen), file=sys.stderr)
        return 2
    samples = Path(args.samples_dir)
    for pid in PRIORITY:
        for suffix in ('.html', '.html.source.json'):
            if (samples / (pid + suffix)).exists():
                print('Refusing overwrite: %s' % (samples / (pid + suffix)), file=sys.stderr)
                return 3
    for c in chosen:
        pid = c['page_id']
        (samples / (pid + '.html')).write_bytes(c['payload'])
        e = c['entry']
        side = {'page_id': pid, 'template': c['template'], 'url': e['url'],
                'final_url': e.get('final_url', e['url']), 'sha256': e['sha256'],
                'raw_chars': e['raw_chars'], 'fetched_at': e['fetched_at'],
                'acceptance': {k: c['checks'][k] for k in ('n_blocks', 'has_paragraph_pair', 'has_para_ge40', 'title_ok')},
                'probe_ingest': True, 'log_entry_index': c['entry_index']}
        (samples / (pid + '.html.source.json')).write_text(
            json.dumps(side, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
    log['status'] = 'complete'
    log['accepted_page_ids'] = [c['page_id'] for c in chosen]
    log['ingestion'] = {'tool_version': TOOL_VERSION,
                        'note': 'A2-minimal (approved hqli631 2026-11-23): id=content last-resort fallback; '
                                'payloads from logged probes, zero new fetches; acceptance re-run post-patch.',
                        'page_ids': [c['page_id'] for c in chosen],
                        'entry_indices': [c['entry_index'] for c in chosen]}
    assert json.dumps(log.get('fetches', []), ensure_ascii=False, sort_keys=True) == fetches_before
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'status': 'complete', 'ingested': [c['page_id'] for c in chosen],
                      'templates': [c['template'] for c in chosen]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
