# -*- coding: utf-8 -*-
"""Repair mechanically-invalid blind labels without changing human judgement.

Why this tool exists
--------------------
The blind template asks for two independent columns per dimension:
  status    scored | partial | unscored | not_applicable
  severity  none | minor | major | critical | unknown
An annotator can legitimately put the value "partial" in the wrong column,
which makes ingest fail validation. This tool performs a *mechanical* repair of
that class of error, plus an explicit, annotator-approved override pass, and
nothing else.

Two passes, strictly separated
------------------------------
1. mechanical repair -- severity=="partial" is moved to status, and the real
   severity is derived ONLY from the annotator's own note text through the
   frozen Rubrics v2 severity anchors (configs/severity_keyword_map.v1.json).
2. overrides -- values the annotator explicitly confirmed (recorded in
   configs/human_label_overrides.v1.json with a reason per entry). The tool
   never derives an override; it only validates and applies what was approved,
   and refuses any override that lacks a reason or targets an unknown field.

Hard guarantees
---------------
* It reads ONLY the filled blind labels file and the two config files.
  It never opens the batch report, judge output, metrics, silver labels,
  the sealed blind-code mapping, or any real case id. Every identifier it
  prints is a blind code, so running it cannot leak mutation types.
* It never invents a score, a decision, or a note. score / decision /
  overall_note / per-dimension note are copied through byte-for-byte unless an
  explicit annotator-approved override names that exact field.
* A dimension whose severity is already a legal value is left untouched by the
  mechanical pass; it is only listed as "needs your confirmation" when it looks
  inconsistent with the frozen severity anchors.
* The original labels file is never modified. Repairs are written to a new
  file in --output together with a full audit trail including input sha256.

Usage
-----
  python -m tools.repair_human_labels --labels <blind.json> --output <dir>
      dry run: writes the review reports only
  python -m tools.repair_human_labels --labels <blind.json> --output <dir2> \
      --overrides configs/human_label_overrides.v1.json --apply
      also writes human_labels.blind.r2.json
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ingest_human_labels import (DECISIONS, SEVERITIES, STATUSES,
                                       write_json, write_text)
from tools.score_judge_results import DIMS, load_json

TOOL_VERSION = '2.1.0'
SEVERE = ('major', 'critical')
LOW_CONF_STATUSES = ('partial', 'unscored')
NO_PROBLEM = ('none', 'unknown', None)
OVERRIDE_FIELDS = ('decision', 'status', 'severity')
FIELD_ENUMS = {'decision': DECISIONS, 'status': STATUSES, 'severity': SEVERITIES}
GAP_KIND = 'uncertain_without_defect_or_low_confidence'


def sha256_bytes(b):
    return sha256(b).hexdigest()


def note_text(entry):
    parts = [entry.get('overall_note') or '']
    for v in (entry.get('dimensions') or {}).values():
        if isinstance(v, dict):
            parts.append(v.get('note') or '')
    return '\n'.join(p for p in parts if p)


def derive_severity(dim, text, cfg):
    """Highest-precedence severity implied by the annotator's own note text."""
    order = cfg.get('precedence') or ['critical', 'major', 'minor', 'none']
    rank = {s: i for i, s in enumerate(order)}
    best, best_rule = 'none', None
    for rule in (cfg.get('dim_rules') or {}).get(dim, []):
        if any(k in text for k in rule.get('keywords', [])):
            sev = rule['severity']
            if best_rule is None or rank.get(sev, 99) < rank.get(best, 99):
                best, best_rule = sev, rule
    return best, best_rule


def repair(doc, cfg):
    """Pass 1: mechanical repair of the misplaced-partial error class."""
    markers = cfg.get('low_confidence_markers') or []
    changes, kept, flags = [], [], []
    for entry in doc.get('cases') or []:
        bc = entry.get('blind_code')
        text = note_text(entry)
        low_conf = any(m in text for m in markers)
        if low_conf:
            flags.append({'blind_code': bc, 'flag': 'low_confidence_case',
                          'detail': 'note mentions one of %s -> scored dims may use status=partial'
                                    % (markers,)})
        for dim in DIMS:
            v = (entry.get('dimensions') or {}).get(dim) or {}
            score, status, sev = v.get('score'), v.get('status'), v.get('severity')
            if sev in SEVERITIES:
                kept.append({'blind_code': bc, 'dim': dim, 'score': score,
                             'status': status, 'severity': sev})
                if sev == 'critical' and score is not None and score >= 2:
                    flags.append({'blind_code': bc, 'dim': dim,
                                  'flag': 'critical_with_nonzero_score',
                                  'detail': 'Rubrics v2 anchors critical to an empty candidate; '
                                            'score=%s with severity=critical needs your confirmation'
                                            % (score,)})
                continue
            if sev == 'partial' and status == 'scored':
                new_status = 'partial' if low_conf else 'scored'
                new_sev, rule = derive_severity(dim, text, cfg)
                changes.append({
                    'blind_code': bc, 'dim': dim, 'score': score,
                    'status_before': status, 'status_after': new_status,
                    'severity_before': sev, 'severity_after': new_sev,
                    'rationale': (rule or {}).get('rationale')
                                 or 'no defect keyword in your note -> none',
                    'keyword_hit': next((k for k in ((rule or {}).get('keywords') or [])
                                         if k in text), None),
                    'kind': 'misplaced_partial'})
                continue
            flags.append({'blind_code': bc, 'dim': dim, 'flag': 'unrepairable_severity',
                          'detail': 'severity=%r is not a legal value and is not the known '
                                    'misplaced-partial pattern; edit it by hand' % (sev,)})
    return changes, kept, flags


def validate_overrides(ov, doc):
    """Reject any override that is unapproved, malformed, or out of scope."""
    problems = []
    if not isinstance(ov, dict):
        return ['overrides document must be an object']
    if ov.get('overrides_version') != 1:
        problems.append('overrides_version must be 1')
    for key in ('approved_by', 'approved_at'):
        if not isinstance(ov.get(key), str) or not ov[key].strip():
            problems.append('%s must be a non-empty string (who approved these edits)' % key)
    known = {e.get('blind_code'): e for e in doc.get('cases') or []}
    entries = ov.get('entries')
    if not isinstance(entries, list):
        return problems + ['overrides entries must be a list']
    for i, e in enumerate(entries):
        tag = 'entries[%d]' % i
        if not isinstance(e, dict):
            problems.append('%s must be an object' % tag)
            continue
        bc = e.get('blind_code')
        if bc not in known:
            problems.append('%s: unknown blind_code %r' % (tag, bc))
            continue
        tag = 'entries[%d](%s)' % (i, bc)
        field = e.get('field')
        if field not in OVERRIDE_FIELDS:
            problems.append('%s: field must be one of %s (score and notes are never '
                            'overridable)' % (tag, OVERRIDE_FIELDS))
            continue
        if e.get('value') not in FIELD_ENUMS[field]:
            problems.append('%s: value %r not legal for %s' % (tag, e.get('value'), field))
        if not isinstance(e.get('reason'), str) or not e['reason'].strip():
            problems.append('%s: reason must be a non-empty string' % tag)
        dim = e.get('dim')
        if field in ('status', 'severity'):
            if dim not in DIMS:
                problems.append('%s: dim must be one of %s for field=%s' % (tag, DIMS, field))
        elif dim is not None:
            problems.append('%s: dim must be omitted for field=decision' % tag)
    for i, g in enumerate(ov.get('acknowledged_gaps') or []):
        tag = 'acknowledged_gaps[%d]' % i
        if not isinstance(g, dict) or g.get('blind_code') not in known:
            problems.append('%s: unknown blind_code' % tag)
            continue
        if g.get('kind') != GAP_KIND:
            problems.append('%s: kind must be %r' % (tag, GAP_KIND))
        if not isinstance(g.get('reason'), str) or not g['reason'].strip():
            problems.append('%s: reason must be a non-empty string' % tag)
    return problems


def apply_overrides(doc, changes, ov):
    """Pass 2: apply annotator-confirmed overrides on top of the mechanical repair."""
    out = json.loads(json.dumps(doc))
    repaired = {(c['blind_code'], c['dim']): c for c in changes}
    by_code = {e.get('blind_code'): e for e in out.get('cases') or []}
    applied = []
    for e in ov.get('entries') or []:
        bc, dim, field, value = e['blind_code'], e.get('dim'), e['field'], e['value']
        entry = by_code[bc]
        if field == 'decision':
            before = entry.get('decision')
            entry['decision'] = value
        else:
            # The document is authoritative; the pass-1 change record is updated
            # as well so REPAIR_DIFF.md shows the provenance of the final value.
            before = (entry['dimensions'][dim] or {}).get(field)
            entry['dimensions'][dim][field] = value
            r = repaired.get((bc, dim))
            if r and field in ('severity', 'status'):
                r[field + '_after'] = value
                r['overridden_by_annotator'] = True
                r['override_reason'] = e['reason']
        applied.append({'blind_code': bc, 'dim': dim, 'field': field,
                        'before': before, 'after': value, 'reason': e['reason'],
                        'kind': 'annotator_confirmed_override'})
    out['overrides'] = {'overrides_version': ov.get('overrides_version'),
                        'approved_by': ov.get('approved_by'),
                        'approved_at': ov.get('approved_at'),
                        'applied': len(applied),
                        'acknowledged_gaps': [g['blind_code']
                                              for g in (ov.get('acknowledged_gaps') or [])]}
    return out, applied


def apply_changes(doc, changes):
    """Write pass-1 results into a copy of the document (input never mutated)."""
    out = json.loads(json.dumps(doc))
    idx = {(c['blind_code'], c['dim']): c for c in changes}
    for entry in out.get('cases') or []:
        for dim in DIMS:
            c = idx.get((entry.get('blind_code'), dim))
            if not c:
                continue
            v = (entry.get('dimensions') or {}).get(dim) or {}
            v['status'] = c['status_after']
            v['severity'] = c['severity_after']
            entry['dimensions'][dim] = v
    out['repair'] = {'tool_version': TOOL_VERSION,
                     'applied': len(changes),
                     'note': 'mechanical status/severity repair; score, decision and notes unchanged'}
    return out


def consistency_warnings(doc, severity_of, decision_of=None, acknowledged=None):
    """Tensions between the labels and the frozen Rubrics v2 decision rules.

    These are never auto-fixed. acknowledged is a set of (blind_code, kind)
    pairs the annotator explicitly confirmed to keep; they are still reported,
    but tagged as acknowledged so they cannot be silently dropped.
    """
    acknowledged = acknowledged or set()
    warns = []
    for entry in doc.get('cases') or []:
        bc = entry.get('blind_code')
        dec = decision_of(bc, entry.get('decision')) if decision_of else entry.get('decision')
        dims = entry.get('dimensions') or {}
        sevs = {d: severity_of((bc, d), (dims.get(d) or {}).get('severity')) for d in DIMS}
        stats = {d: (dims.get(d) or {}).get('status') for d in DIMS}
        severe = [d for d in DIMS if sevs[d] in SEVERE]
        low = [d for d in DIMS if stats[d] in LOW_CONF_STATUSES]
        defects = [d for d in DIMS if sevs[d] not in NO_PROBLEM]

        def add(kind, detail):
            warns.append((bc, dec, kind, detail, (bc, kind) in acknowledged))
        if dec not in DECISIONS:
            add('illegal_decision', 'must be one of %s' % (DECISIONS,))
        elif dec == 'fail' and not severe:
            add('decision_fail_without_major_or_critical',
                'Rubrics v2: fail requires a major/critical problem. Either raise a severity '
                'or change the decision. dims=%s' % ({d: sevs[d] for d in DIMS},))
        elif dec in ('pass', 'uncertain') and severe:
            add('major_or_critical_but_not_fail',
                'Rubrics v2: a major/critical problem implies fail. severe dims=%s' % (severe,))
        elif dec == 'uncertain' and not defects and not low \
                and entry.get('mode') != 'source_only':
            # The source_only clause of Rubrics v2 ("only uncertain or fail, never
            # pass") takes precedence: with no reference answer, uncertain is the
            # correct ceiling even when no defect is alleged, so it is not a gap.
            add(GAP_KIND,
                'Rubrics v2: uncertain requires a non-severe problem or partial/unscored '
                'evidence; this case has neither. Not auto-changed - annotator judgement.')
        if dec == 'pass' and low:
            add('pass_with_low_confidence',
                'Rubrics v2: pass requires sufficient evidence; status=%s on %s'
                % ([stats[d] for d in low], low))
        if dec == 'pass' and defects:
            add('pass_with_defect',
                'Rubrics v2: pass requires no problem on any dimension; defects=%s'
                % ({d: sevs[d] for d in defects},))
    return warns


def pending(warns):
    return [w for w in warns if not w[4]]


def render_diff(doc, changes, kept, flags, overrides_applied=None):
    by_code = {e.get('blind_code'): e for e in doc.get('cases') or []}
    lines = ['# P0 盲评标签 · 机械修复对照表', '',
             '- 标注者：%s' % doc.get('annotator'),
             '- 机械修复条目：%d；保持不动：%d；提示：%d；标注者确认覆盖：%d'
             % (len(changes), len(kept), len(flags), len(overrides_applied or [])),
             '- 机械修复的 severity 只从**标注者本人 note** + 冻结的 Rubrics v2 严重度锚点推导，',
             '  未读取 judge / silver / 变异类型 / 密封映射。', '',
             '## A. 机械修复（severity 误填为 partial）', '',
             '| 盲码 | 维度 | score | status | severity | 依据 |',
             '| --- | --- | --- | --- | --- | --- |']
    for c in changes:
        basis = ('关键词「%s」：%s' % (c['keyword_hit'], c['rationale'])) \
            if c['keyword_hit'] else c['rationale']
        if c.get('overridden_by_annotator'):
            basis += ' → **标注者确认覆盖**：%s' % c['override_reason']
        lines.append('| %s | %s | %s | %s -> %s | %s -> %s | %s |' % (
            c['blind_code'], c['dim'], c['score'],
            c['status_before'], c['status_after'],
            c['severity_before'], c['severity_after'], basis))
    lines += ['', '## B. 标注者确认的覆盖项（工具不自行推导）', '']
    if overrides_applied:
        lines += ['| 盲码 | 维度 | 字段 | 改前 | 改后 | 理由 |', '| --- | --- | --- | --- | --- | --- |']
        for o in overrides_applied:
            lines.append('| %s | %s | %s | %s | %s | %s |' % (
                o['blind_code'], o.get('dim') or '-', o['field'],
                o['before'], o['after'], o['reason']))
    else:
        lines.append('（本次未提供 --overrides，无覆盖项）')
    lines += ['', '## C. 已填合法值、工具不动的维度（仅列可疑项）', '']
    suspicious = [f for f in flags if f['flag'] != 'low_confidence_case']
    if suspicious:
        lines += ['| 盲码 | 维度 | 提示 | 说明 |', '| --- | --- | --- | --- |']
        for f in suspicious:
            lines.append('| %s | %s | %s | %s |' % (
                f['blind_code'], f.get('dim', '-'), f['flag'], f['detail']))
    else:
        lines.append('（无）')
    lines += ['', '## D. 低置信案卷（note 提到源截断/无参考答案）', '',
              '| 盲码 | decision | overall_note |', '| --- | --- | --- |']
    for f in [f for f in flags if f['flag'] == 'low_confidence_case']:
        e = by_code.get(f['blind_code']) or {}
        lines.append('| %s | %s | %s |' % (f['blind_code'], e.get('decision'),
                                            (e.get('overall_note') or '').replace('\n', ' ')))
    lines += ['', '## E. 未改动字段', '',
              'score、note、overall_note、annotator、annotation_date 全部原样保留；'
              'decision 与个别 severity 仅在标注者书面确认（B 节）时才变更；原文件不会被覆盖。', '']
    return '\n'.join(lines) + '\n'


def render_warnings(warns):
    pend, ack = pending(warns), [w for w in warns if w[4]]
    lines = ['# P0 盲评标签 · 协议一致性待确认项', '',
             '这些不是格式错误，是标注判断与冻结 Rubrics v2 决策规则之间的张力。',
             '**工具不会替你改**：待确认项须由标注者决定；已确认项按标注者书面决定保留并留痕。', '',
             '## 待确认（%d）' % len(pend), '']
    if pend:
        lines += ['| 盲码 | decision | 提示 | 说明 |', '| --- | --- | --- | --- |']
        for bc, dec, kind, detail, _ in pend:
            lines.append('| %s | %s | %s | %s |' % (bc, dec, kind, detail))
    else:
        lines.append('（无）')
    lines += ['', '## 标注者已确认保留（%d，记为校准发现）' % len(ack), '']
    if ack:
        lines += ['| 盲码 | decision | 提示 | 说明 |', '| --- | --- | --- | --- |']
        for bc, dec, kind, detail, _ in ack:
            lines.append('| %s | %s | %s | %s |' % (bc, dec, kind, detail))
    else:
        lines.append('（无）')
    lines.append('')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--labels', required=True)
    ap.add_argument('--map', dest='map_path',
                    default=str(ROOT / 'configs' / 'severity_keyword_map.v1.json'))
    ap.add_argument('--overrides', default=None,
                    help='annotator-confirmed corrections (decision/status/severity only)')
    ap.add_argument('--output', required=True)
    ap.add_argument('--apply', action='store_true',
                    help='also write human_labels.blind.r2.json (default: review reports only)')
    args = ap.parse_args(argv)

    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    doc = load_json(args.labels)
    cfg = load_json(args.map_path)
    if not isinstance(doc, dict) or doc.get('stage') != 'blind':
        print(json.dumps({'error': 'labels stage must be blind'}, ensure_ascii=False))
        return 2
    for entry in doc.get('cases') or []:
        if 'case_id' in entry:
            print(json.dumps({'error': 'labels file must stay blind (found case_id key)'},
                             ensure_ascii=False))
            return 2

    changes, kept, flags = repair(doc, cfg)
    ov, overrides_applied = None, []
    if args.overrides:
        ov = load_json(args.overrides)
        problems = validate_overrides(ov, doc)
        if problems:
            print(json.dumps({'error': 'overrides_validation', 'problems': problems},
                             ensure_ascii=False, indent=1))
            return 2

    repaired = apply_changes(doc, changes)
    if ov:
        repaired, overrides_applied = apply_overrides(repaired, changes, ov)
    by_code = {e.get('blind_code'): e for e in repaired.get('cases') or []}
    sev_of = lambda k, cur: (by_code.get(k[0], {}).get('dimensions', {}).get(k[1]) or {}).get(
        'severity', cur)
    dec_of = lambda bc, cur: by_code.get(bc, {}).get('decision', cur)
    ack = {(g['blind_code'], g['kind']) for g in ((ov or {}).get('acknowledged_gaps') or [])}
    warns = consistency_warnings(repaired, sev_of, dec_of, ack)

    out.mkdir(parents=True)
    raw = Path(args.labels).read_bytes()
    write_text(out / 'REPAIR_DIFF.md', render_diff(doc, changes, kept, flags, overrides_applied))
    write_text(out / 'CONSISTENCY_WARNINGS.md', render_warnings(warns))
    write_json(out / 'severity_repairs.json',
               {'map_version': cfg.get('map_version'), 'tool_version': TOOL_VERSION,
                'changes': changes, 'flags': flags, 'overrides': overrides_applied})
    write_json(out / 'repair_audit.json',
               {'tool_version': TOOL_VERSION,
                'map_version': cfg.get('map_version'),
                'overrides_version': (ov or {}).get('overrides_version'),
                'overrides_approved_by': (ov or {}).get('approved_by'),
                'overrides_approved_at': (ov or {}).get('approved_at'),
                'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'labels_sha256': sha256_bytes(raw),
                'labels_path': str(Path(args.labels)),
                'n_cases': len(doc.get('cases') or []),
                'n_changes': len(changes),
                'n_overrides': len(overrides_applied),
                'n_kept_legal': len(kept),
                'n_flags': len(flags),
                'n_consistency_warnings_pending': len(pending(warns)),
                'n_consistency_warnings_acknowledged': len(warns) - len(pending(warns)),
                'acknowledged_gaps': sorted(ack),
                'applied': bool(args.apply),
                'reads': ['labels file', 'keyword map config', 'overrides config'],
                'does_not_read': ['batch report', 'judge output', 'metrics',
                                  'silver labels', 'sealed_mapping.json']})
    if args.apply:
        write_json(out / 'human_labels.blind.r2.json', repaired)
    summary = {'tool_version': TOOL_VERSION, 'applied': bool(args.apply),
               'n_changes': len(changes), 'n_overrides': len(overrides_applied),
               'n_kept_legal': len(kept), 'n_flags': len(flags),
               'n_consistency_warnings_pending': len(pending(warns)),
               'n_consistency_warnings_acknowledged': len(warns) - len(pending(warns)),
               'changed_by_severity': {}, 'output': str(out)}
    for c in changes:
        k = '%s->%s' % (c['severity_before'], c['severity_after'])
        summary['changed_by_severity'][k] = summary['changed_by_severity'].get(k, 0) + 1
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
