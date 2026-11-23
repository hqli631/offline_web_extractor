# -*- coding: utf-8 -*-
"""P-F dev gold re-adjudication: audited override view (zero model calls).

Applies annotator-approved anchor re-adjudications (configs/pf_dev_gold_overrides.v1.json)
to the P-B dev gold views WITHOUT rewriting any sealed/upstream file. Reads only the
two dev gold JSONs in outputs/pb.gate.inputs.v1 and the spec; every applied value comes
from the spec (no derived judgements). Fail-closed: unknown/duplicate case ids, wrong
source_file declaration, before-value drift, or malformed specs all exit 2. Output is a
FRESH directory (refuse overwrite, exit 3) containing the two updated gold views, a
byte-level override_audit.json (input/output sha256 + per-case before/after diff) and
OVERRIDE_DIFF.md. Only decision and per-dimension score/severity/note may change; all
other case fields and the upstream overlay provenance chain are preserved. Deterministic
(no timestamps); inputs are re-hashed after writing to prove they were never modified.
"""
import argparse
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_VERSION = '1.0.0'
GOLD_FILES = ('dev.orig.gold.json', 'dev.p2.gold.json')
DECISIONS = ('pass', 'uncertain', 'fail')
SEVERITIES = ('none', 'minor', 'major', 'critical')
DIMENSIONS = ('completeness', 'cleanliness', 'structure', 'title', 'format')


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def write_json(p, v):
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n',
                       encoding='utf-8', newline='')


def validate_spec(spec):
    problems = []
    if spec.get('override_version') != 'pf-dev-gold-overrides-1':
        problems.append('unsupported override_version')
    for k in ('approved_by', 'approved_at', 'approval_quote'):
        if not (isinstance(spec.get(k), str) and spec[k].strip()):
            problems.append('spec missing approval field ' + k)
    entries = spec.get('entries')
    if not isinstance(entries, list) or not entries:
        problems.append('spec entries must be a nonempty list')
        return problems
    seen = set()
    for e in entries:
        cid = e.get('case_id')
        if not isinstance(cid, str) or not cid:
            problems.append('entry missing case_id')
            continue
        if cid in seen:
            problems.append('duplicate case_id ' + cid)
        seen.add(cid)
        if e.get('source_file') not in GOLD_FILES:
            problems.append('%s: source_file must be one of %s' % (cid, GOLD_FILES))
        if not (isinstance(e.get('reason'), str) and e['reason'].strip()):
            problems.append('%s: missing reason' % cid)
        for side in ('before', 'after'):
            blk = e.get(side)
            if not isinstance(blk, dict) or blk.get('decision') not in DECISIONS:
                problems.append('%s: %s.decision invalid' % (cid, side))
                continue
            dims = blk.get('dimensions')
            if not isinstance(dims, dict) or not dims:
                problems.append('%s: %s.dimensions must be a nonempty dict' % (cid, side))
                continue
            for dn, dv in dims.items():
                if dn not in DIMENSIONS:
                    problems.append('%s: %s unknown dimension %s' % (cid, side, dn))
                if not isinstance(dv, dict):
                    problems.append('%s: %s.%s must be object' % (cid, side, dn))
                    continue
                sc = dv.get('score')
                if side == 'before' and (type(sc) is not int or not 0 <= sc <= 4):
                    problems.append('%s: before.%s.score must be int 0..4' % (cid, dn))
                if side == 'after' and sc is not None and (type(sc) is not int or not 0 <= sc <= 4):
                    problems.append('%s: after.%s.score must be int 0..4 or null' % (cid, dn))
                if dv.get('severity') not in SEVERITIES:
                    problems.append('%s: %s.%s.severity invalid' % (cid, side, dn))
        if isinstance(e.get('after'), dict) and isinstance(e.get('before'), dict):
            extra = set((e['after'].get('dimensions') or {})) - set((e['before'].get('dimensions') or {}))
            if extra:
                problems.append('%s: after touches dimensions absent from before: %s' % (cid, sorted(extra)))
    return problems


def apply_overrides(spec, inputs_dir):
    """Return (views, audit_entries, problems). Never writes anything."""
    docs = {n: load_json(Path(inputs_dir) / n) for n in GOLD_FILES}
    index = {}
    for n, doc in docs.items():
        for i, c in enumerate(doc['cases']):
            index.setdefault(c['case_id'], []).append((n, i))
    problems, audit = [], []
    views = deepcopy(docs)
    for e in spec['entries']:
        cid = e['case_id']
        locs = index.get(cid, [])
        if len(locs) != 1:
            problems.append('%s: expected exactly one occurrence across dev golds, found %d' % (cid, len(locs)))
            continue
        n, i = locs[0]
        if n != e['source_file']:
            problems.append('%s: declared source_file %s but found in %s' % (cid, e['source_file'], n))
            continue
        case = docs[n]['cases'][i]
        before_obs = {'decision': case['decision'],
                      'dimensions': {dn: {'score': case['dimensions'][dn]['score'],
                                          'severity': case['dimensions'][dn]['severity']}
                                     for dn in e['before']['dimensions']}}
        if before_obs != e['before']:
            problems.append('%s: before-value drift; observed %s' % (cid, json.dumps(before_obs, ensure_ascii=False)))
            continue
        tgt = views[n]['cases'][i]
        tgt['decision'] = e['after']['decision']
        for dn, dv in e['after']['dimensions'].items():
            tgt['dimensions'][dn]['score'] = dv.get('score')
            tgt['dimensions'][dn]['severity'] = dv['severity']
            if 'note' in dv:
                tgt['dimensions'][dn]['note'] = dv['note']
        after_obs = {'decision': tgt['decision'],
                     'dimensions': {dn: {'score': tgt['dimensions'][dn]['score'],
                                         'severity': tgt['dimensions'][dn]['severity']}
                                    for dn in e['after']['dimensions']}}
        audit.append({'case_id': cid, 'source_file': n, 'blind_code': case.get('blind_code'),
                      'before': before_obs, 'after': after_obs, 'reason': e['reason']})
    return views, audit, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--spec', type=Path, default=ROOT / 'configs/pf_dev_gold_overrides.v1.json')
    ap.add_argument('--inputs-dir', type=Path, default=ROOT / 'outputs/pb.gate.inputs.v1')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    spec = load_json(args.spec)
    problems = validate_spec(spec)
    if problems:
        for p in problems:
            print('SPEC: ' + p, file=sys.stderr)
        return 2
    input_sha = {n: sha256_bytes((Path(args.inputs_dir) / n).read_bytes()) for n in GOLD_FILES}
    views, audit, problems = apply_overrides(spec, args.inputs_dir)
    if problems:
        for p in problems:
            print('APPLY: ' + p, file=sys.stderr)
        return 2
    spec_sha = sha256_bytes(Path(args.spec).read_bytes())
    for n in GOLD_FILES:
        v = views[n]
        v['gold_version'] = 'pf-dev-gold-v2-' + ('orig' if n == GOLD_FILES[0] else 'p2')
        prov = v.setdefault('provenance', {})
        prov['pf_override'] = {
            'spec': str(Path(args.spec).relative_to(ROOT)) if Path(args.spec).is_relative_to(ROOT) else str(args.spec),
            'spec_sha256': spec_sha,
            'base_view_sha256': input_sha[n],
            'applied_case_ids': [a['case_id'] for a in audit if a['source_file'] == n],
            'approved_by': spec['approved_by'], 'approved_at': spec['approved_at'],
            'note': 'Anchor re-adjudication view for v1.4 dev calibration; upstream sealed files never rewritten.',
        }
        lims = prov.setdefault('limitations', [])
        extra = 'P-F: 3 dev cases re-adjudicated to adjudicated anchors (missing x2, reorder x1); anchoring circularity on dev track now up to 6/18 (3 overlay + 3 re-adjudicated); v4 is the independent generalization test.'
        if extra not in lims:
            lims.append(extra)
    out.mkdir(parents=True)
    for n in GOLD_FILES:
        write_json(out / n, views[n])
    unchanged = all(sha256_bytes((Path(args.inputs_dir) / n).read_bytes()) == input_sha[n] for n in GOLD_FILES)
    if not unchanged:
        print('FATAL: input files changed during run', file=sys.stderr)
        return 2
    audit_doc = {'tool_version': TOOL_VERSION, 'spec_sha256': spec_sha,
                 'input_sha256': input_sha,
                 'output_sha256': {n: sha256_bytes((out / n).read_bytes()) for n in GOLD_FILES},
                 'inputs_unchanged_verified': True,
                 'approved_by': spec['approved_by'], 'approved_at': spec['approved_at'],
                 'approval_quote': spec['approval_quote'], 'entries': audit}
    write_json(out / 'override_audit.json', audit_doc)
    lines = ['# P-F dev gold 重裁决差异（审计视图，密封历史未改写）', '',
             '批准：%s（%s）' % (spec['approved_by'], spec['approved_at']), '',
             '| 案例 | 文件 | 维度 | 改前 | 改后 | decision |',
             '| --- | --- | --- | --- | --- | --- |']
    for a in audit:
        for dn in a['after']['dimensions']:
            b, af = a['before']['dimensions'][dn], a['after']['dimensions'][dn]
            lines.append('| %s | %s | %s | %s/%s | %s/%s | %s -> %s |' % (
                a['case_id'], a['source_file'], dn, b['score'], b['severity'],
                af['score'], af['severity'], a['before']['decision'], a['after']['decision']))
    lines += ['', '其余 15 例 dev gold 逐字段不变；上游 sealed/overlay 文件零改写（输入哈希复核通过）。',
              '锚定循环披露：dev 轨道最多 6/18（overlay 3 + 本次改判 3）；v4 为独立泛化测试。']
    (out / 'OVERRIDE_DIFF.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'output': str(out), 'applied': [a['case_id'] for a in audit],
                      'inputs_unchanged': True}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
