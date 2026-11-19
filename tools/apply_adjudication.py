# -*- coding: utf-8 -*-
"""Apply annotator adjudication decisions to the prefilled final labels.

Why this tool exists
--------------------
After Round-1 blind agreement, the annotator reads the adjudication packets
and decides, per case, to keep or revise their blind label. Instead of
hand-editing 23 JSON entries, the annotator gives feedback in chat; the
assistant records it as an auditable spec (one entry per case, an explicit
reason per revision) and this tool validates and applies it.

Hard guarantees
---------------
* Reads ONLY the prefilled final labels file and the decisions spec. It never
  opens the batch report, judge output, silver labels, or the sealed mapping,
  and it never derives a judgement: every applied value comes from the spec.
* Every case must appear exactly once in the spec; there is no implicit
  confirmation. Missing / duplicate / unknown entries fail closed (exit 2).
* keep   -> decision / dimensions are copied through untouched.
  revise -> only decision and per-dimension score/status/severity/note may
  change, and only to values named in the spec. overall_note, case_id,
  blind_code, split, mode are immutable.
* injection_complied may only be set on entries that already carry the field
  (injection cases), must be a boolean, and is mandatory for those entries.
* source_only cases may not be set to pass (frozen protocol rule).
* Input files are never modified. Output goes to a fresh --output directory
  (fail-closed if it exists) together with adjudication_audit.json (input
  sha256 + per-case before/after diff) and ADJUDICATION_DIFF.md.

Usage
-----
  python -m tools.apply_adjudication \
      --labels outputs/human_review/round1.v1/human_labels.final.json \
      --decisions configs/adjudication_decisions.v1.json \
      --output outputs/human_review/final.prep.v1
"""
import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ingest_human_labels import (DATE_RE, DECISIONS, SEVERITIES, STATUSES,
                                       write_json, write_text)
from tools.score_judge_results import DIMS, load_json

TOOL_VERSION = '1.0.0'
DIM_FIELDS = ('score', 'status', 'severity', 'note')
CHANGE_FIELDS = ('decision', 'dimensions')


def sha256_bytes(b):
    return sha256(b).hexdigest()


def _no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError('duplicate key %r' % k)
        d[k] = v
    return d


def dim_problems(v):
    problems = []
    s, st, sev = v.get('score'), v.get('status'), v.get('severity')
    if s is not None and (type(s) is not int or not 0 <= s <= 4):
        problems.append('score must be integer 0-4 or null')
    if st not in STATUSES:
        problems.append('invalid status %r' % (st,))
    if type(s) is int and st not in ('scored', 'partial'):
        problems.append('integer score requires status scored/partial')
    if s is None and st not in ('unscored', 'not_applicable'):
        problems.append('null score requires status unscored/not_applicable')
    if sev not in SEVERITIES:
        problems.append('invalid severity %r' % (sev,))
    if not isinstance(v.get('note', ''), str):
        problems.append('note must be a string')
    return problems


def validate_spec(spec, doc):
    """Return (errors, resolved). resolved = [(entry, decision, note), ...]."""
    errors = []
    if not isinstance(spec, dict):
        return ['decisions spec must be an object'], []
    if spec.get('spec_version') != 1:
        errors.append('spec_version must be 1')
    annotator = spec.get('annotator')
    if not isinstance(annotator, str) or not annotator.strip():
        errors.append('annotator must be a non-empty string')
    elif annotator != doc.get('annotator'):
        errors.append('spec annotator %r differs from labels annotator %r'
                      % (annotator, doc.get('annotator')))
    date = spec.get('adjudication_date')
    if not isinstance(date, str) or not DATE_RE.match(date):
        errors.append('adjudication_date must be YYYY-MM-DD')
    default_note = spec.get('default_keep_note', '')
    if not isinstance(default_note, str):
        errors.append('default_keep_note must be a string')
        default_note = ''
    entries = doc.get('cases')
    if not isinstance(entries, list) or not entries:
        return errors + ['labels cases must be a non-empty list'], []
    by_code = {e.get('blind_code'): e for e in entries}
    by_id = {e.get('case_id'): e for e in entries}
    decisions = spec.get('decisions')
    if not isinstance(decisions, list):
        return errors + ['decisions must be a list'], []
    seen = set()
    resolved = []
    for i, d in enumerate(decisions):
        tag = 'decisions[%d]' % i
        if not isinstance(d, dict):
            errors.append(tag + ': must be an object')
            continue
        bc, cid = d.get('blind_code'), d.get('case_id')
        if bc is None and cid is None:
            errors.append(tag + ': needs blind_code or case_id')
            continue
        entry = None
        if bc is not None:
            entry = by_code.get(bc)
            if entry is None:
                errors.append('%s: unknown blind_code %r' % (tag, bc))
                continue
            tag = bc
        if cid is not None:
            e2 = by_id.get(cid)
            if e2 is None:
                errors.append('%s: unknown case_id %r' % (tag, cid))
                continue
            if entry is not None and e2 is not entry:
                errors.append('%s: blind_code and case_id refer to different cases' % tag)
                continue
            entry = e2
        key = entry['case_id']
        if key in seen:
            errors.append('%s: duplicate decision' % tag)
            continue
        seen.add(key)
        action = d.get('action')
        if action not in ('keep', 'revise'):
            errors.append('%s: action must be keep/revise' % tag)
        note = d.get('note', '')
        if not isinstance(note, str):
            errors.append('%s: note must be a string' % tag)
            note = ''
        if action == 'keep' and not note.strip():
            note = default_note
        if not note.strip():
            errors.append('%s: adjudication note required '
                          '(keep may fall back to default_keep_note)' % tag)
        changes = d.get('changes')
        if action == 'keep' and changes is not None:
            errors.append('%s: keep must not carry changes' % tag)
        if action == 'revise' and (not isinstance(changes, dict) or not changes):
            errors.append('%s: revise requires non-empty changes' % tag)
        if isinstance(changes, dict):
            for k in changes:
                if k not in CHANGE_FIELDS:
                    errors.append('%s: changes field %r not allowed '
                                  '(only decision/dimensions)' % (tag, k))
            if 'decision' in changes:
                nd = changes['decision']
                if nd not in DECISIONS:
                    errors.append('%s: decision must be one of %s' % (tag, DECISIONS))
                elif entry.get('mode') == 'source_only' and nd == 'pass':
                    errors.append('%s: source_only decision must not be pass' % tag)
            if 'dimensions' in changes:
                pd = changes['dimensions']
                if not isinstance(pd, dict) or not pd:
                    errors.append('%s: dimensions patch must be a non-empty object' % tag)
                else:
                    for n, patch in pd.items():
                        if n not in DIMS:
                            errors.append('%s: unknown dimension %r' % (tag, n))
                            continue
                        if not isinstance(patch, dict) or not patch:
                            errors.append('%s/%s: patch must be a non-empty object'
                                          % (tag, n))
                            continue
                        for f in patch:
                            if f not in DIM_FIELDS:
                                errors.append('%s/%s: field %r not allowed'
                                              % (tag, n, f))
                        merged = dict(entry.get('dimensions', {}).get(n) or {})
                        merged.update({f: v for f, v in patch.items()
                                       if f in DIM_FIELDS})
                        for p in dim_problems(merged):
                            errors.append('%s/%s: %s' % (tag, n, p))
        if 'injection_complied' in d:
            if 'injection_complied' not in entry:
                errors.append('%s: injection_complied only allowed on injection cases'
                              % tag)
            elif type(d['injection_complied']) is not bool:
                errors.append('%s: injection_complied must be true/false' % tag)
        resolved.append((entry, d, note))
    for e in entries:
        if e['case_id'] not in seen:
            errors.append('%s: missing decision (every case must be adjudicated)'
                          % e.get('blind_code'))
    for entry, d, _note in resolved:
        if 'injection_complied' in entry and 'injection_complied' not in d:
            errors.append('%s: injection case requires injection_complied true/false'
                          % entry.get('blind_code'))
    return errors, resolved


def field_diff(before, after):
    out = {}
    if before.get('decision') != after.get('decision'):
        out['decision'] = {'before': before.get('decision'),
                           'after': after.get('decision')}
    for n in DIMS:
        b = (before.get('dimensions') or {}).get(n) or {}
        a = (after.get('dimensions') or {}).get(n) or {}
        for f in DIM_FIELDS:
            if b.get(f) != a.get(f):
                out['dimensions.%s.%s' % (n, f)] = {'before': b.get(f),
                                                    'after': a.get(f)}
    if 'injection_complied' in after and \
            before.get('injection_complied') != after.get('injection_complied'):
        out['injection_complied'] = {'before': before.get('injection_complied'),
                                     'after': after['injection_complied']}
    return out


def apply_decisions(doc, resolved, spec):
    out = copy.deepcopy(doc)
    entries = {e['case_id']: e for e in out['cases']}
    diffs = []
    for entry_src, d, note in resolved:
        e = entries[entry_src['case_id']]
        before = copy.deepcopy(e)
        changes = d.get('changes') or {}
        if 'decision' in changes:
            e['decision'] = changes['decision']
        for n, patch in (changes.get('dimensions') or {}).items():
            for f, v in patch.items():
                if f in DIM_FIELDS:
                    e['dimensions'][n][f] = v
        if 'injection_complied' in d:
            e['injection_complied'] = d['injection_complied']
        e['adjudication_note'] = note
        e['confirmed'] = True
        diffs.append({'blind_code': e.get('blind_code'), 'case_id': e['case_id'],
                      'action': d.get('action'), 'note': note,
                      'fields': field_diff(before, e)})
    out['annotation_date'] = spec['adjudication_date']
    return out, diffs


def final_problems(doc):
    """Mirror of ingest final-stage structural checks (no batch/silver needed)."""
    problems = []
    for e in doc['cases']:
        bc = e.get('blind_code')
        if e.get('confirmed') is not True:
            problems.append('%s: confirmed must be true' % bc)
        note = e.get('adjudication_note')
        if not isinstance(note, str) or not note.strip():
            problems.append('%s: adjudication_note must be a non-empty string' % bc)
        if e.get('decision') not in DECISIONS:
            problems.append('%s: invalid decision' % bc)
        if e.get('mode') == 'source_only' and e.get('decision') == 'pass':
            problems.append('%s: source_only decision must not be pass' % bc)
        dims = e.get('dimensions') or {}
        if set(dims) != set(DIMS):
            problems.append('%s: dimensions must cover exactly %s' % (bc, DIMS))
            continue
        for n in DIMS:
            for p in dim_problems(dims.get(n) or {}):
                problems.append('%s/%s: %s' % (bc, n, p))
        if 'injection_complied' in e and type(e['injection_complied']) is not bool:
            problems.append('%s: injection_complied must be true/false' % bc)
    return problems


def render_diff(diffs, audit):
    lines = ['# 裁决落盘差异（ADJUDICATION_DIFF）', '',
             '- 标注者：%s；裁决日期：%s' % (audit['annotator'],
                                            audit['adjudication_date']),
             '- 案例：%d；维持 %d；修改 %d' % (audit['n_cases'], audit['kept'],
                                              audit['revised']),
             '- 标签输入 sha256：%s' % audit['labels_sha256'],
             '- 裁决spec sha256：%s' % audit['decisions_sha256'], '',
             '## 字段级修改', '']
    changed = [d for d in diffs if d['fields']]
    if not changed:
        lines += ['（无字段级修改）', '']
    for d in changed:
        lines += ['### %s（%s，%s）' % (d['blind_code'], d['case_id'], d['action']),
                  '', '理由：%s' % d['note'], '',
                  '| 字段 | 原值 | 新值 |', '| --- | --- | --- |']
        for f, vv in d['fields'].items():
            lines.append('| %s | %s | %s |' % (f, json.dumps(vv['before'],
                                                           ensure_ascii=False),
                                               json.dumps(vv['after'],
                                                          ensure_ascii=False)))
        lines.append('')
    lines += ['## 逐例裁决记录', '', '| 盲码 | 动作 | 理由 |', '| --- | --- | --- |']
    for d in diffs:
        lines.append('| %s | %s | %s |' % (d['blind_code'], d['action'],
                                           d['note'].replace('|', '\\|')))
    lines += ['', '注：本文件由工具生成；原始盲评标签与预填模板均未被修改。', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--decisions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    out = args.output
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    labels_bytes = args.labels.read_bytes()
    spec_bytes = args.decisions.read_bytes()
    doc = json.loads(labels_bytes.decode('utf-8'))
    try:
        spec = json.loads(spec_bytes.decode('utf-8'), object_pairs_hook=_no_dupes)
    except ValueError as exc:
        print(json.dumps({'error': 'spec_parse', 'problems': [str(exc)]},
                         ensure_ascii=False))
        return 2
    if not isinstance(doc, dict) or doc.get('stage') != 'final' \
            or doc.get('label_version') != 1:
        print(json.dumps({'error': 'labels', 'problems':
                          ['labels must be a stage=final, label_version=1 document']},
                         ensure_ascii=False))
        return 2
    errors, resolved = validate_spec(spec, doc)
    if errors:
        print(json.dumps({'error': 'validation', 'problems': errors},
                         ensure_ascii=False, indent=1))
        return 2
    new_doc, diffs = apply_decisions(doc, resolved, spec)
    problems = final_problems(new_doc)
    if problems:
        print(json.dumps({'error': 'post_apply_validation', 'problems': problems},
                         ensure_ascii=False, indent=1))
        return 2
    out.mkdir(parents=True)
    write_json(out / 'human_labels.final.json', new_doc)
    kept = [d for d in diffs if d['action'] == 'keep']
    revised = [d for d in diffs if d['action'] == 'revise']
    audit = {'tool_version': TOOL_VERSION,
             'generated_at': datetime.now(timezone.utc).isoformat(),
             'annotator': new_doc['annotator'],
             'adjudication_date': new_doc['annotation_date'],
             'labels_sha256': sha256_bytes(labels_bytes),
             'decisions_sha256': sha256_bytes(spec_bytes),
             'feedback_source': spec.get('feedback_source', ''),
             'n_cases': len(diffs), 'kept': len(kept), 'revised': len(revised),
             'decisions': diffs}
    write_json(out / 'adjudication_audit.json', audit)
    write_text(out / 'ADJUDICATION_DIFF.md', render_diff(diffs, audit))
    print(json.dumps({'output': str(out), 'confirmed': len(diffs),
                      'kept': len(kept), 'revised': len(revised),
                      'changed_cases': [d['blind_code'] for d in diffs
                                        if d['fields']]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
