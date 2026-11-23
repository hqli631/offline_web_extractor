# -*- coding: utf-8 -*-
"""P-B freeze amendment: v3 data freeze v7 (judge v1.3 pin) -> v9 (v1.2 pin).

Pre-registered consequence of the approved step-4 branch (docs/P_B_AMENDMENT_PROPOSAL.md
D1/D2, approved hqli631 2026-11-23): judge v1.3 failed amendment was rolled back to
v1.2.0 (byte-exact sha edd841ef...). Freeze v7 was sealed under v1.3 and pins the
v1.3 judge source (46f21118...); running v3 under the retained v1.2 requires the
judge SOURCE pin to reflect the restored protocol. This amendment updates ONLY
src/webextractor/rubrics_judge.py's pin. EVERY data file (manifest, sources,
candidates, expected gold, silver labels), the case hash table, manifest_sha256
and batch_config are preserved byte-identical. No threshold or data change.

Fail-closed: the judge file must ALREADY be restored byte-exact to v1.2 (edd841ef);
every non-judge frozen file must match disk bytes (proves data unchanged at
amendment time). Refuses overwrite; --dry-run proves without writing. Zero calls.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_VERSION = '1.0.0'
PARENT = 'outputs/p3.freeze.v7.json'
PARENT_SHA = 'b536ad193d41d5f468801e8c58c42d4193403ece67486780bb5dc854cbffcee5'
JUDGE_REL = 'src/webextractor/rubrics_judge.py'
V12_SHA = 'edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891'
V13_SHA = '46f2111837ba'  # prefix; full old pin read from parent at runtime
APPROVAL_QUOTE = ('批准 D1 保留 v1.2；批准 D2 overlay 基准 + v3 复用 12；'
                  'D3 v3 12 例盲评已完成；批准 D4 预算 14 调用/300k')


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def build(parent_path, output, root=ROOT, dry_run=False):
    parent_path = Path(parent_path)
    pb = parent_path.read_bytes()
    if sha256_bytes(pb) != PARENT_SHA:
        raise ValueError('parent freeze v7 sha256 drift')
    parent = json.loads(pb)
    files = parent.get('files') or {}
    if JUDGE_REL not in files:
        raise ValueError('parent freeze lacks judge source pin')
    old_judge = files[JUDGE_REL]
    cur_judge = sha256_bytes((root / JUDGE_REL).read_bytes())
    if cur_judge != V12_SHA:
        raise ValueError('judge source not restored to v1.2 (edd841ef); got ' + cur_judge)
    # prove every non-judge frozen file matches disk (data unchanged)
    for rel, recorded in files.items():
        if rel == JUDGE_REL:
            continue
        p = root / rel
        if not p.exists():
            raise ValueError('frozen data file missing: ' + rel)
        if sha256_bytes(p.read_bytes()) != recorded:
            raise ValueError('frozen data file drift (data changed?): ' + rel)
    new = copy.deepcopy(parent)
    new['freeze_version'] = 9
    new['files'] = dict(files)
    new['files'][JUDGE_REL] = cur_judge
    # invariants: only judge pin changed
    for rel in files:
        if rel != JUDGE_REL and new['files'][rel] != files[rel]:
            raise ValueError('unexpected change to ' + rel)
    if new.get('manifest_sha256') != parent.get('manifest_sha256'):
        raise ValueError('manifest_sha256 changed')
    if new.get('cases') != parent.get('cases'):
        raise ValueError('case hash table changed')
    if new.get('batch_config') != parent.get('batch_config'):
        raise ValueError('batch_config changed')
    new['amendment'] = {
        'amendment_version': 1,
        'type': 'judge_source_pin_rollback',
        'base_freeze': PARENT,
        'base_freeze_sha256': PARENT_SHA,
        'judge_version': '1.2.0',
        'changed_files': {JUDGE_REL: {'old': old_judge, 'new': cur_judge}},
        'data_unchanged': True,
        'reason': ('P3 step-4 branch (D1/D2 approved 2026-11-23): failed judge v1.3 '
                   'amendment rolled back to v1.2.0; v3 data freeze judge source pin '
                   'updated to restored v1.2. All data files, case hashes, '
                   'manifest_sha256 and batch_config byte-identical to v7. No '
                   'threshold or data change. v3 silver labels retain mutation '
                   'metadata used by the gate (protocol-independent); prompt_chars '
                   'is not used by gate scoring.'),
        'approval_quote': APPROVAL_QUOTE,
        'approved_by': 'hqli631',
        'approved_at': '2026-11-23',
    }
    new['p3_note'] = (parent.get('p3_note', '') +
                      ' | P-B amendment v9: judge source pin rolled back to v1.2 '
                      '(edd841ef); data unchanged.').strip()
    if dry_run:
        return {'dry_run': True, 'changed': {JUDGE_REL: {'old': old_judge, 'new': cur_judge}},
                'data_files_verified': len(files) - 1, 'output': str(output)}
    out = Path(output)
    if out.exists():
        raise FileExistsError('output exists; choose a new path')
    out.write_text(json.dumps(new, ensure_ascii=False, indent=2) + '\n',
                   encoding='utf-8', newline='')
    return {'dry_run': False, 'freeze_sha256': sha256_bytes(out.read_bytes()),
            'changed': {JUDGE_REL: {'old': old_judge, 'new': cur_judge}},
            'data_files_verified': len(files) - 1, 'output': str(out)}


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-B freeze amendment v7 -> v9 (judge pin only).')
    ap.add_argument('--output', type=Path, default=ROOT / 'outputs/pb.freeze.v9.json')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    try:
        res = build(ROOT / PARENT, args.output, dry_run=args.dry_run)
    except FileExistsError as e:
        print(str(e), file=sys.stderr)
        return 3
    except (ValueError, KeyError) as e:
        print('FAIL-CLOSED: ' + str(e), file=sys.stderr)
        return 2
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
