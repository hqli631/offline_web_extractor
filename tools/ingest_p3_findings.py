# -*- coding: utf-8 -*-
"""P3 calibration findings ingestion (offline, zero model calls, fail-closed).

Validates the reviewer-filled p3_findings.json against the kit template and
integrity hashes, summarizes verdicts by divergence category, and emits
calibration_findings_p3.json + FINDINGS_SUMMARY.md. Read-only on P2 sealed
artifacts: never rewrites gold/batch, never re-scores frozen_test v2. The
amendment_signal is a FLAG for drafting a pre-registered freeze amendment
proposal; it never auto-modifies the protocol. Refuses overwrite (exit 3).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_p3_review_kit import VERDICTS
from tools.score_p2_results import load_json, write_json
from tools.score_judge_results import sha256_bytes

TOOL_VERSION = '1.0.0'
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def write_text(p, t):
    Path(p).write_text(t, encoding='utf-8', newline='')


def category_of(case_id, categories):
    if 'instruction_interference' in case_id:
        return 'A_injection_gold_miss'
    if any(c.startswith('judge_severe_human_not') for c in categories):
        return 'B_judge_stricter'
    if any(c.startswith('judge_missed_defect') for c in categories):
        return 'C_judge_missed'
    return 'D_other'


def validate_findings(doc, template_cases):
    errors = []
    if doc.get('findings_version') != 1:
        errors.append('findings_version must be 1')
    if not isinstance(doc.get('reviewer'), str) or not doc['reviewer'].strip():
        errors.append('reviewer must be a nonempty string')
    d = doc.get('review_date')
    if not isinstance(d, str) or not DATE_RE.match(d):
        errors.append('review_date must be YYYY-MM-DD')
    if doc.get('discipline_ack') is not True:
        errors.append('discipline_ack must be true (no P2 gold rewrite, no v2 re-score, amendments pre-registered)')
    entries = doc.get('cases')
    if not isinstance(entries, list):
        return errors + ['cases must be a list']
    expected = {c['case_id']: c for c in template_cases}
    seen = {}
    for e in entries:
        if not isinstance(e, dict):
            errors.append('case entry must be an object')
            continue
        cid = e.get('case_id')
        if cid in seen:
            errors.append('%s: duplicate entry' % cid)
        seen[cid] = e
    for cid in expected:
        if cid not in seen:
            errors.append('%s: missing entry' % cid)
    for cid in seen:
        if cid not in expected:
            errors.append('%s: unknown case' % cid)
    for cid, e in seen.items():
        if cid not in expected:
            continue
        v = e.get('verdict')
        if v not in VERDICTS:
            errors.append('%s: verdict must be one of %s (got %r)' % (cid, VERDICTS, v))
        if not isinstance(e.get('note', ''), str):
            errors.append('%s: note must be a string' % cid)
        if not isinstance(e.get('anchor_revision_suggestion', ''), str):
            errors.append('%s: anchor_revision_suggestion must be a string' % cid)
        t = expected[cid]
        if e.get('categories') != t.get('categories'):
            errors.append('%s: categories altered from kit template' % cid)
    return errors


def summarize(rows):
    counts = {v: 0 for v in VERDICTS}
    by_cat = {}
    suggestions = []
    for r in rows:
        counts[r['verdict']] += 1
        cat = r['category']
        by_cat.setdefault(cat, {v: 0 for v in VERDICTS})
        by_cat[cat][r['verdict']] += 1
        if r.get('anchor_revision_suggestion', '').strip():
            suggestions.append({'case_id': r['case_id'], 'suggestion': r['anchor_revision_suggestion']})
    amendment_signal = (counts['anchor_ambiguous'] + counts['both_partially_correct'] > 0) or bool(suggestions)
    return {'verdict_counts': counts, 'by_category': by_cat,
            'anchor_suggestions': suggestions,
            'amendment_signal': amendment_signal,
            'note': 'amendment_signal only flags drafting a PRE-REGISTERED proposal; protocol is never auto-modified.'}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Ingest P3 calibration findings (offline).')
    ap.add_argument('--findings', type=Path, default=ROOT / 'outputs/human_review/p3.calibration.v1/p3_findings.json')
    ap.add_argument('--kit-dir', type=Path, default=ROOT / 'outputs/human_review/p3.calibration.v1')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    km = load_json(args.kit_dir / 'kit_manifest.json')
    problems = []
    # kit_manifest inputs use logical names; map them to the sealed P2 paths.
    input_paths = {'p2_batch': 'outputs/p2.judge.v2.json',
                   'gold': 'outputs/human_review/p2.gold.v1/human_gold.p2.blind.json',
                   'freeze': 'outputs/p2.freeze.v5.json',
                   'manifest': 'samples/p2_manifest.json'}
    for name, recorded in (km.get('inputs') or {}).items():
        rel = input_paths.get(name)
        if rel is None:
            problems.append('kit input unknown logical name: ' + name)
            continue
        p = ROOT / rel
        if not p.exists() or sha256_bytes(p.read_bytes()) != recorded:
            problems.append('kit input drift: ' + name + ' (' + rel + ')')
    for rel, recorded in (km.get('files') or {}).items():
        if rel == 'p3_findings.json':
            continue
        p = args.kit_dir / rel
        if not p.exists() or sha256_bytes(p.read_bytes()) != recorded:
            problems.append('kit file drift: ' + rel)
    if problems:
        for p in problems:
            print('INTEGRITY: ' + p, file=sys.stderr)
        return 1
    template = load_json(args.kit_dir / 'p3_findings.json')
    doc = load_json(args.findings)
    errors = validate_findings(doc, template['cases'])
    if errors:
        for e in errors:
            print('VALIDATION: ' + e, file=sys.stderr)
        print('%d validation error(s); no findings written.' % len(errors), file=sys.stderr)
        return 2
    rows = []
    for e in doc['cases']:
        rows.append({'case_id': e['case_id'], 'split': e.get('split'),
                     'categories': e['categories'], 'category': category_of(e['case_id'], e['categories']),
                     'verdict': e['verdict'], 'note': e.get('note', ''),
                     'anchor_revision_suggestion': e.get('anchor_revision_suggestion', '')})
    summary = summarize(rows)
    result = {'tool_version': TOOL_VERSION, 'reviewer': doc['reviewer'], 'review_date': doc['review_date'],
              'provenance': {'findings_sha256': sha256_bytes(args.findings.read_bytes()),
                             'kit_manifest_sha256': sha256_bytes((args.kit_dir / 'kit_manifest.json').read_bytes()),
                             'kit_inputs': km.get('inputs')},
              'discipline': 'P2 gold/batch read-only; frozen_test v2 not re-scored; amendments pre-registered only.',
              'cases': rows, 'summary': summary}
    out.mkdir(parents=True)
    write_json(out / 'calibration_findings_p3.json', result)
    L = ['# P3 校准复审 findings 摘要', '',
         '- 复审者：%s（%s）｜ 案卷：%d' % (doc['reviewer'], doc['review_date'], len(rows)),
         '- verdict 分布：%s' % json.dumps(summary['verdict_counts'], ensure_ascii=False),
         '- 分类分布：%s' % json.dumps({k: v for k, v in summary['by_category'].items()}, ensure_ascii=False),
         '- 锚点修订建议：%d 条；amendment_signal=%s（仅触发预注册提案起草，不自动改协议）' % (len(summary['anchor_suggestions']), summary['amendment_signal']), '',
         '| 案卷 | 类别 | verdict | note |', '| --- | --- | --- | --- |']
    for r in rows:
        L.append('| %s | %s | %s | %s |' % (r['case_id'], r['category'], r['verdict'], r['note'].replace('|', '/')))
    write_text(out / 'FINDINGS_SUMMARY.md', '\n'.join(L) + '\n')
    print(json.dumps({'ok': True, 'output': str(out), 'n': len(rows),
                      'verdicts': summary['verdict_counts'], 'amendment_signal': summary['amendment_signal']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
