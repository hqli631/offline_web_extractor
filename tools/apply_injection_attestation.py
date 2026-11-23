# -*- coding: utf-8 -*-
"""Apply annotator-confirmed injection_complied attestations (offline, fail-closed).

The blind template's injection_complied field must be a JSON boolean. Annotators
sometimes type the string "false"/"true" (or leave it missing). This tool applies
ONLY the explicit, annotator-approved entries in a config: it coerces a matching
string placeholder to the approved boolean (or fills a missing field), never
invents a value, never touches any other field, and never reads judge output,
silver labels, or the sealed mapping. The original labels file is not modified;
the repaired copy + audit land in a fresh --output dir (overwrite refused).

Usage:
  python -m tools.apply_injection_attestation --labels <blind.json> \
      --config configs/pf_injection_attestation.v1.json --output <dir>
      dry run: writes attestation_audit.json only (applied=false)
  ... --apply   also writes human_labels.blind.json
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

TOOL_VERSION = '1.0.0'


def sha256_bytes(b):
    return sha256(b).hexdigest()


def load_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def write_json(p, v):
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n',
                       encoding='utf-8', newline='')


def validate_config(cfg, doc):
    problems = []
    if cfg.get('attestation_version') != 1:
        problems.append('attestation_version must be 1')
    if cfg.get('status') != 'approved':
        problems.append('config status must be approved')
    for k in ('approved_by', 'approved_at'):
        if not isinstance(cfg.get(k), str) or not cfg[k].strip():
            problems.append('%s must be a non-empty string' % k)
    known = {e.get('blind_code'): e for e in doc.get('cases') or []}
    entries = cfg.get('entries')
    if not isinstance(entries, list) or not entries:
        return problems + ['entries must be a non-empty list']
    for i, e in enumerate(entries):
        tag = 'entries[%d]' % i
        bc = e.get('blind_code')
        if bc not in known:
            problems.append('%s: unknown blind_code %r' % (tag, bc))
            continue
        if e.get('field') != 'injection_complied':
            problems.append('%s: field must be injection_complied' % tag)
        if type(e.get('value')) is not bool:
            problems.append('%s: value must be a JSON boolean' % tag)
        if not isinstance(e.get('reason'), str) or not e['reason'].strip():
            problems.append('%s: reason must be non-empty' % tag)
        cur = known[bc].get('injection_complied')
        if cur is not None and type(cur) is not str:
            problems.append('%s(%s): existing value %r is not a string placeholder; refuse'
                            % (tag, bc, cur))
        elif isinstance(cur, str) and cur.strip().lower() != str(e.get('value')).lower():
            problems.append('%s(%s): placeholder %r contradicts approved value %r'
                            % (tag, bc, cur, e.get('value')))
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--labels', type=Path, required=True)
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args(argv)
    out = args.output
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    doc = load_json(args.labels)
    if doc.get('stage') != 'blind':
        print('labels stage must be blind', file=sys.stderr)
        return 2
    if any('case_id' in e for e in doc.get('cases') or []):
        print('labels file must stay blind (found case_id key)', file=sys.stderr)
        return 2
    cfg = load_json(args.config)
    problems = validate_config(cfg, doc)
    if problems:
        for p in problems:
            print('CONFIG: ' + p, file=sys.stderr)
        return 2
    out.mkdir(parents=True)
    fixed = json.loads(json.dumps(doc))
    by_code = {e['blind_code']: e for e in fixed['cases']}
    applied = []
    for e in cfg['entries']:
        entry = by_code[e['blind_code']]
        before = entry.get('injection_complied')
        entry['injection_complied'] = e['value']
        applied.append({'blind_code': e['blind_code'], 'field': 'injection_complied',
                        'before': before, 'after': e['value'], 'reason': e['reason']})
    fixed['attestation'] = {'attestation_version': cfg['attestation_version'],
                            'approved_by': cfg['approved_by'],
                            'approved_at': cfg['approved_at'], 'applied': len(applied)}
    audit = {'tool_version': TOOL_VERSION, 'applied': bool(args.apply),
             'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
             'labels_sha256': sha256_bytes(args.labels.read_bytes()),
             'config_sha256': sha256_bytes(args.config.read_bytes()),
             'labels_path': str(args.labels), 'config_path': str(args.config),
             'n_entries': len(applied), 'entries': applied,
             'reads': ['labels file', 'attestation config'],
             'does_not_read': ['judge output', 'silver labels',
                               'sealed_mapping.json', 'metrics']}
    write_json(out / 'attestation_audit.json', audit)
    if args.apply:
        write_json(out / 'human_labels.blind.json', fixed)
    print(json.dumps({'ok': True, 'applied': bool(args.apply),
                      'n_entries': len(applied), 'output': str(out)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
