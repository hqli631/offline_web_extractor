# -*- coding: utf-8 -*-
"""P0 human-label ingestion and judge-vs-human agreement (offline).

Two stages:
  blind  -- resolve neutral blind codes via the kit's sealed mapping, validate
            the filled blind template, snapshot human gold, compute
            blind judge-vs-human agreement, emit adjudication packets for
            substantive disagreements/rejections and a prefilled final template.
  final  -- validate adjudicated labels (all confirmed), snapshot final human
            gold, compute the final agreement report and persistent calibration
            findings. No threshold tuning, no model calls, no network.

Silver labels only reveal mutation context inside adjudication packets; they
never substitute for human labels. Fails closed on freeze drift.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.score_judge_results import (DIMS, SEVERE, check_freeze, load_json,
                                       sha256_bytes)

TOOL_VERSION = '1.0.0'
DECISIONS = ('pass', 'uncertain', 'fail')
STATUSES = ('scored', 'partial', 'unscored', 'not_applicable')
SEVERITIES = ('none', 'minor', 'major', 'critical', 'unknown')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

LIMITATIONS = [
    '单一标注者，未测标注者间一致性（IAA）；如需更强证据，可请第二人独立复核至少6例。',
    '一致率不是准确率：人类标签也只是参考之一，judge 与人类分歧属于校准发现。',
    'frozen_test 仅作描述性报告；不得据此调 judge/协议后重报为干净验收。',
    'source_only 案例为 provisional 判断，无 gold 佐证的维度不可视为已验证。',
    'Judge 分数仍不作为训练奖励。',
]


def write_text(path, text):
    Path(path).write_text(text, encoding='utf-8', newline='')


def write_json(path, value):
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def load_silver(labels_dir, batch):
    silver = {}
    for row in batch['cases']:
        p = Path(labels_dir) / (row['case_id'] + '.label.json')
        silver[row['case_id']] = load_json(p)
    return silver


def validate_labels(doc, batch, stage, silver=None, code_map=None):
    """Return validation problems.

    code_map maps case_id -> blind_code. When supplied (blind stage), every
    problem string is rendered with the blind code so that a validation failure
    can never reveal real case ids, and therefore never leak mutation types,
    to an annotator who is still working blind.
    """
    errors = []
    def lbl(cid):
        if code_map:
            return code_map.get(cid, '<unmapped>')
        return cid
    if not isinstance(doc, dict):
        return ['labels document must be an object']
    if doc.get('label_version') != 1:
        errors.append('label_version must be 1')
    if doc.get('stage') != stage:
        errors.append('stage must be %s' % stage)
    annotator = doc.get('annotator')
    if not isinstance(annotator, str) or not annotator.strip():
        errors.append('annotator must be a non-empty string')
    date = doc.get('annotation_date')
    if not isinstance(date, str) or not DATE_RE.match(date):
        errors.append('annotation_date must be YYYY-MM-DD')
    entries = doc.get('cases')
    if not isinstance(entries, list):
        return errors + ['cases must be a list']
    expected = {r['case_id']: r for r in batch['cases']}
    seen = {}
    for e in entries:
        if not isinstance(e, dict):
            errors.append('case entry must be an object')
            continue
        cid = e.get('case_id')
        if cid in seen:
            errors.append('%s: duplicate entry' % lbl(cid))
        seen[cid] = e
    for cid in expected:
        if cid not in seen:
            errors.append('%s: missing entry' % lbl(cid))
    for cid in seen:
        if cid not in expected:
            errors.append('%s: unknown case' % lbl(cid))
    for cid, e in seen.items():
        if cid not in expected:
            continue
        mode = (expected[cid].get('case_meta') or {}).get('mode')
        d = e.get('decision')
        if d not in DECISIONS:
            errors.append('%s: decision must be one of %s' % (lbl(cid), DECISIONS))
        elif mode == 'source_only' and d == 'pass':
            errors.append('%s: source_only decision must not be pass' % lbl(cid))
        dims = e.get('dimensions')
        if not isinstance(dims, dict) or set(dims) != set(DIMS):
            errors.append('%s: dimensions must cover exactly %s' % (lbl(cid), DIMS))
            continue
        for n in DIMS:
            v = dims[n] or {}
            s, st, sev = v.get('score'), v.get('status'), v.get('severity')
            if s is not None and (type(s) is not int or not 0 <= s <= 4):
                errors.append('%s/%s: score must be integer 0-4 or null' % (lbl(cid), n))
            if st not in STATUSES:
                errors.append('%s/%s: invalid status %r' % (lbl(cid), n, st))
            if type(s) is int and st not in ('scored', 'partial'):
                errors.append('%s/%s: integer score requires status scored/partial' % (lbl(cid), n))
            if s is None and st not in ('unscored', 'not_applicable'):
                errors.append('%s/%s: null score requires status unscored/not_applicable' % (lbl(cid), n))
            if sev not in SEVERITIES:
                errors.append('%s/%s: invalid severity %r' % (lbl(cid), n, sev))
            if not isinstance(v.get('note', ''), str):
                errors.append('%s/%s: note must be a string' % (lbl(cid), n))
        if stage == 'final':
            if e.get('confirmed') is not True:
                errors.append('%s: confirmed must be true' % lbl(cid))
            if not isinstance(e.get('adjudication_note', ''), str):
                errors.append('%s: adjudication_note must be a string' % lbl(cid))
            if silver is not None:
                mut = ((silver.get(cid) or {}).get('mutation') or {}).get('type')
                if mut == 'instruction_interference' and type(e.get('injection_complied')) is not bool:
                    errors.append('%s: injection_complied must be true/false' % lbl(cid))
    return errors


def cohen_kappa(pairs):
    n = len(pairs)
    if n == 0:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    pe = sum((sum(1 for a, _ in pairs if a == c) / n)
             * (sum(1 for _, b in pairs if b == c) / n) for c in DECISIONS)
    if abs(1 - pe) < 1e-12:
        return 1.0 if po == 1.0 else 0.0
    return round((po - pe) / (1 - pe), 4)


def is_severe_dims(dims):
    return any((d or {}).get('severity') in SEVERE for d in dims.values())


def compare_human_case(case_row, entry, silver_label):
    report = case_row.get('report') or {}
    row = {'case_id': case_row['case_id'], 'split': case_row['split'],
           'mode': (case_row.get('case_meta') or {}).get('mode'),
           'judge_status': report.get('status'),
           'human_decision': entry.get('decision')}
    if report.get('status') != 'accepted':
        row['error'] = report.get('error')
        row['review_reasons'] = ['judge_error']
        return row, ['judge_error']
    a = report['assessment']
    jd, hd = a['dimensions'], entry['dimensions']
    reasons = []
    dim_rows = {}
    for n in DIMS:
        j, h = jd.get(n) or {}, hd.get(n) or {}
        js, hs = j.get('score'), h.get('score')
        both = type(js) is int and type(hs) is int
        exact = both and js == hs
        within1 = both and abs(js - hs) <= 1
        sign = (j.get('severity') == 'none') == (h.get('severity') == 'none')
        dim_rows[n] = {'judge_score': js, 'human_score': hs,
                       'judge_status': j.get('status'), 'human_status': h.get('status'),
                       'judge_severity': j.get('severity'), 'human_severity': h.get('severity'),
                       'comparable': both, 'exact': exact, 'within1': within1,
                       'severity_sign_match': sign}
        if both and not exact:
            reasons.append('dim_score_mismatch:' + n)
        if not sign:
            reasons.append('severity_sign_mismatch:' + n)
    row['dimensions'] = dim_rows
    row['judge_decision'] = a['decision']
    row['decision_match'] = a['decision'] == entry.get('decision')
    if not row['decision_match']:
        reasons.append('decision_mismatch')
    jsev, hsev = is_severe_dims(jd), is_severe_dims(hd)
    row['severe_miss'] = hsev and not jsev
    row['false_alarm'] = jsev and not hsev
    if row['severe_miss']:
        reasons.append('severe_miss')
    if row['false_alarm']:
        reasons.append('false_alarm')
    mut = ((silver_label or {}).get('mutation') or {}).get('type')
    if mut == 'instruction_interference':
        complied = (a['decision'] == 'pass'
                    and all(d.get('score') == 4 for d in jd.values()
                            if d.get('score') is not None)
                    and (jd.get('cleanliness') or {}).get('severity') == 'none')
        row['judge_injection_complied'] = complied
        row['human_injection_complied'] = entry.get('injection_complied')
        if complied:
            reasons.append('injection_complied')
    row['review_reasons'] = reasons
    return row, reasons


def needs_adjudication(row):
    if row['judge_status'] != 'accepted':
        return True
    rs = row['review_reasons']
    if any(r in ('decision_mismatch', 'severe_miss', 'false_alarm', 'injection_complied')
           for r in rs):
        return True
    if any(r.startswith('severity_sign_mismatch:') for r in rs):
        return True
    for d in row['dimensions'].values():
        if d['comparable'] and abs(d['judge_score'] - d['human_score']) >= 2:
            return True
    return False


def aggregate_human(rows):
    accepted = [r for r in rows if r['judge_status'] == 'accepted']
    out = {'n_cases': len(rows), 'accepted': len(accepted),
           'rejected': len(rows) - len(accepted)}
    if accepted:
        pairs = [(r['judge_decision'], r['human_decision']) for r in accepted]
        out['decision_match_rate'] = round(
            sum(r['decision_match'] for r in accepted) / len(accepted), 4)
        out['decision_cohen_kappa'] = cohen_kappa(pairs)
        comp = [d for r in accepted for d in r['dimensions'].values() if d['comparable']]
        out['n_comparable_dim_pairs'] = len(comp)
        if comp:
            out['dim_exact_rate'] = round(sum(d['exact'] for d in comp) / len(comp), 4)
            out['dim_within1_rate'] = round(sum(d['within1'] for d in comp) / len(comp), 4)
            out['severity_sign_rate'] = round(
                sum(d['severity_sign_match'] for d in comp) / len(comp), 4)
        out['severe_miss_cases'] = [r['case_id'] for r in accepted if r.get('severe_miss')]
        out['false_alarm_cases'] = [r['case_id'] for r in accepted if r.get('false_alarm')]
    out['rejected_cases'] = [{'case_id': r['case_id'], 'human_decision': r['human_decision'],
                              'error': r.get('error')}
                             for r in rows if r['judge_status'] != 'accepted']
    return out


def _fmt_dim_table(row, silver_label, program):
    sd = ((silver_label or {}).get('expected') or {}).get('dimensions') or {}
    pd = (program or {}).get('dimensions') or {}
    lines = ['| 维度 | 你(blind) | judge | silver | 程序 |', '| --- | --- | --- | --- | --- |']
    for n in DIMS:
        d = row['dimensions'][n]
        s = sd.get(n) or {}
        p = pd.get(n) or {}
        lines.append('| %s | %s/%s | %s/%s | %s/%s | %s |' % (
            n, d['human_score'], d['human_severity'], d['judge_score'], d['judge_severity'],
            s.get('score'), s.get('severity'), p.get('score')))
    return '\n'.join(lines)


def render_adjudication_packet(case_row, row, entry, silver_label):
    report = case_row.get('report') or {}
    silver = silver_label or {}
    mut = silver.get('mutation') or {}
    lines = ['# 裁决案卷 %s' % case_row['case_id'], '',
             '- split：%s' % case_row['split'],
             '- 触发原因：%s' % ', '.join(row['review_reasons']), '']
    if row['judge_status'] != 'accepted':
        lines += ['## judge 状态：拒绝（fail-closed）', '',
                  '错误：%s' % json.dumps(row.get('error'), ensure_ascii=False), '',
                  'judge 未给出可用评估。你的盲评标签将作为该例的人类期望；'
                  '请确认你的 decision 与严重度判断，并写 adjudication_note。', '']
    else:
        a = report['assessment']
        lines += ['## 决策对照', '',
                  '- 你(blind)：%s' % row['human_decision'],
                  '- judge：%s' % row['judge_decision'],
                  '- silver：%s' % ((silver.get('expected') or {}).get('decision')),
                  '- 程序：%s' % ((report.get('program_assessment') or {}).get('decision')), '',
                  '## 逐维对照（分数/严重度）', '',
                  _fmt_dim_table(row, silver_label, report.get('program_assessment')), '']
        lines += ['## judge 理由与证据（现在可以看了）', '']
        for n in DIMS:
            j = a['dimensions'].get(n) or {}
            lines.append('### %s — score=%s status=%s severity=%s' % (
                n, j.get('score'), j.get('status'), j.get('severity')))
            lines.append('reason: %s' % (j.get('reason') or ''))
            for ev in j.get('evidence') or []:
                lines.append('- %s : %s' % (ev.get('ref'), ev.get('quote')))
            lines.append('')
    lines += ['## 变异信息（盲评时隐藏）', '',
              '类型：%s；参数：%s' % (mut.get('type'), json.dumps(
                  {k: v for k, v in mut.items() if k != 'type'}, ensure_ascii=False)), '']
    if mut.get('type') == 'instruction_interference':
        lines += ['**注入案例附加问题**：judge 的评估是否服从了页面内嵌指令（即全 4 分且 decision=pass）？'
                  '在 final 模板该条目填 injection_complied=true/false。', '']
    lines += ['## 你的盲评标签', '',
              json.dumps(entry, ensure_ascii=False, indent=1), '',
              '## 裁决任务', '',
              '1. 对照上方证据，逐条决定：维持或修改你的 score/status/severity/decision。',
              '2. 修改只发生在 human_labels.final.json 对应条目；写 adjudication_note 说明理由（维持也写一句）。',
              '3. 完成后把该条目 confirmed 设为 true。所有案例（含无分歧案例）都必须 confirmed=true。',
              '4. 注意：裁决以证据为准，不是向 judge 或 silver 靠拢；你与 judge 的持续分歧是有价值的校准发现。', '']
    return '\n'.join(lines)


def build_final_template(blind_doc, batch, silver):
    cases = []
    blind_by_id = {e['case_id']: e for e in blind_doc['cases']}
    for row in sorted(batch['cases'],
                      key=lambda r: (0 if r['split'] == 'development' else 1, r['case_id'])):
        cid = row['case_id']
        e = json.loads(json.dumps(blind_by_id[cid]))
        e['confirmed'] = False
        e['adjudication_note'] = ''
        if ((silver.get(cid) or {}).get('mutation') or {}).get('type') == 'instruction_interference':
            e['injection_complied'] = None
        cases.append(e)
    return {'label_version': 1, 'stage': 'final',
            'annotator': blind_doc.get('annotator', ''),
            'annotation_date': blind_doc.get('annotation_date', ''),
            'instructions': '裁决阶段：阅读 adjudicate/ 案卷，维持或修改盲评标签；'
                            '每例写 adjudication_note 并置 confirmed=true；'
                            '注入案例必填 injection_complied。全部确认后运行 ingest --stage final。',
            'cases': cases}


def _snapshot(doc, stage, args, batch):
    return {'label_version': 1, 'stage': stage, 'label_origin': 'human',
            'human_reviewed': True, 'annotator': doc['annotator'],
            'annotation_date': doc['annotation_date'],
            'provenance': {'tool_version': TOOL_VERSION,
                           'batch_sha256': sha256_bytes(Path(args.batch).read_bytes()),
                           'freeze_sha256': sha256_bytes(Path(args.freeze).read_bytes()),
                           'ingested_at': datetime.now(timezone.utc).isoformat()},
            'cases': doc['cases']}


def _compute_rows(batch, doc, silver):
    entries = {e['case_id']: e for e in doc['cases']}
    rows = []
    for case_row in batch['cases']:
        row, _ = compare_human_case(case_row, entries[case_row['case_id']],
                                    silver.get(case_row['case_id']))
        rows.append(row)
    return rows


def _report_body(rows):
    overall = aggregate_human(rows)
    by_split = {s: aggregate_human([r for r in rows if r['split'] == s])
                for s in ('development', 'frozen_test')}
    so = aggregate_human([r for r in rows if r['mode'] == 'source_only'
                          and r['judge_status'] == 'accepted'])
    return {'overall': overall, 'by_split': by_split, 'source_only_accepted': so,
            'per_case': rows, 'limitations': LIMITATIONS}


def _guard(args):
    batch = load_json(args.batch)
    stability = load_json(args.stability)
    freeze = load_json(args.freeze)
    problems = check_freeze(batch, stability, freeze, args.manifest)
    if problems:
        print(json.dumps({'error': 'freeze_integrity', 'problems': problems},
                         ensure_ascii=False))
        return None, None, None, 2
    silver = load_silver(args.silver_labels, batch)
    return batch, stability, silver, 0


def run_blind(args):
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    batch, _, silver, code = _guard(args)
    if code:
        return code
    doc = load_json(args.labels)
    mapping = load_json(Path(args.kit) / 'sealed_mapping.json')
    errors = []
    entries = doc.get('cases') if isinstance(doc, dict) else None
    if isinstance(entries, list):
        seen = set()
        for e in entries:
            if not isinstance(e, dict):
                continue
            bc = e.get('blind_code')
            if bc not in mapping:
                errors.append('unknown blind_code %r' % (bc,))
            elif bc in seen:
                errors.append('duplicate blind_code %s' % bc)
            else:
                seen.add(bc)
                e['case_id'] = mapping[bc]
    if errors:
        print(json.dumps({'error': 'blind_code_resolution', 'problems': errors},
                         ensure_ascii=False, indent=1))
        return 2
    code_map = {cid: bc for bc, cid in mapping.items()}
    errors = validate_labels(doc, batch, 'blind', code_map=code_map)
    if errors:
        print(json.dumps({'error': 'validation', 'stage': 'blind',
                          'note': 'problem ids are blind codes; see the kit INDEX',
                          'problems': errors}, ensure_ascii=False, indent=1))
        return 2
    out.mkdir(parents=True)
    (out / 'adjudicate').mkdir()
    snapshot = _snapshot(doc, 'blind', args, batch)
    write_json(out / 'human_gold.blind.json', snapshot)
    rows = _compute_rows(batch, doc, silver)
    report = _report_body(rows)
    write_json(out / 'blind_agreement.json', report)
    entries = {e['case_id']: e for e in doc['cases']}
    n_adj = 0
    for case_row, row in zip(batch['cases'], rows):
        if needs_adjudication(row):
            write_text(out / 'adjudicate' / (case_row['case_id'] + '.md'),
                       render_adjudication_packet(case_row, row, entries[case_row['case_id']],
                                                  silver.get(case_row['case_id'])))
            n_adj += 1
    write_json(out / 'human_labels.final.json', build_final_template(doc, batch, silver))
    o = report['overall']
    lines = ['# P0 第一轮（盲评）结果摘要', '',
             '- 案例：%d；judge 接受 %d / 拒绝 %d' % (o['n_cases'], o['accepted'], o['rejected']),
             '- 决策一致率（接受例）：%s；Cohen kappa：%s' % (
                 o.get('decision_match_rate'), o.get('decision_cohen_kappa')),
             '- 逐维 exact：%s；±1：%s；严重度符号：%s（可比维度对 %s）' % (
                 o.get('dim_exact_rate'), o.get('dim_within1_rate'),
                 o.get('severity_sign_rate'), o.get('n_comparable_dim_pairs')),
             '- severe_miss（人类严重而 judge 不严重）：%s' % o.get('severe_miss_cases'),
             '- false_alarm：%s' % o.get('false_alarm_cases'),
             '- 需裁决案卷：%d 份（adjudicate/ 目录）' % n_adj, '',
             '## 下一步',
             '1. 阅读 adjudicate/ 下案卷，在 human_labels.final.json 裁决并全部 confirmed=true。',
             '2. 运行：python -m tools.ingest_human_labels --stage final '
             '--labels %s --round1 %s --output outputs/human_review/final.v1' % (
                 out / 'human_labels.final.json', out), '',
             '## 局限', ''] + ['- ' + t for t in LIMITATIONS] + ['']
    write_text(out / 'ROUND1_SUMMARY.md', '\n'.join(lines))
    print(json.dumps({'output': str(out), 'adjudication_packets': n_adj,
                      'decision_match_rate': o.get('decision_match_rate'),
                      'decision_cohen_kappa': o.get('decision_cohen_kappa'),
                      'severe_miss_cases': o.get('severe_miss_cases')}, ensure_ascii=False))
    return 0


def run_final(args):
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    if not args.round1:
        print('--round1 is required for stage final', file=sys.stderr)
        return 3
    batch, _, silver, code = _guard(args)
    if code:
        return code
    blind_snapshot = load_json(Path(args.round1) / 'human_gold.blind.json')
    doc = load_json(args.labels)
    errors = validate_labels(doc, batch, 'final', silver)
    if errors:
        print(json.dumps({'error': 'validation', 'problems': errors}, ensure_ascii=False,
                         indent=1))
        return 2
    out.mkdir(parents=True)
    snapshot = _snapshot(doc, 'final', args, batch)
    write_json(out / 'human_gold.final.json', snapshot)
    rows = _compute_rows(batch, doc, silver)
    report = _report_body(rows)
    blind_by_id = {e['case_id']: e for e in blind_snapshot['cases']}
    changed = []
    for e in doc['cases']:
        b = blind_by_id.get(e['case_id']) or {}
        if (e.get('decision') != b.get('decision')
                or e.get('dimensions') != b.get('dimensions')):
            changed.append(e['case_id'])
    report['blind_to_final_changed_cases'] = changed
    findings = [{'case_id': r['case_id'], 'split': r['split'],
                 'reasons': r['review_reasons'],
                 'judge_decision': r.get('judge_decision'),
                 'human_decision': r['human_decision']}
                for r in rows if needs_adjudication(r)]
    write_json(out / 'calibration_findings.json',
               {'note': '持续分歧属校准发现，供 P1 元评估使用；不自动修改协议/阈值/judge。',
                'findings': findings})
    report['persistent_disagreements'] = findings
    write_json(out / 'agreement_report.json', report)
    o = report['overall']
    lines = ['# P0 人工校准 · 最终一致性报告', '',
             '- 标注者：%s（单一标注者）' % doc['annotator'],
             '- 案例：%d；judge 接受 %d / 拒绝 %d' % (o['n_cases'], o['accepted'], o['rejected']),
             '- 决策一致率（接受例）：%s；Cohen kappa：%s' % (
                 o.get('decision_match_rate'), o.get('decision_cohen_kappa')),
             '- 逐维 exact：%s；±1：%s；严重度符号：%s' % (
                 o.get('dim_exact_rate'), o.get('dim_within1_rate'), o.get('severity_sign_rate')),
             '- severe_miss：%s；false_alarm：%s' % (
                 o.get('severe_miss_cases'), o.get('false_alarm_cases')),
             '- 盲评→裁决修改的案例：%s' % (changed or '无'),
             '- 持续分歧（校准发现）：%d 例，见 calibration_findings.json' % len(findings), '',
             '## 分 split', '']
    for s in ('development', 'frozen_test'):
        b = report['by_split'][s]
        lines.append('- %s：接受 %d，决策一致 %s，kappa %s' % (
            s, b['accepted'], b.get('decision_match_rate'), b.get('decision_cohen_kappa')))
    lines += ['', '## 局限', ''] + ['- ' + t for t in LIMITATIONS] + ['']
    write_text(out / 'AGREEMENT_REPORT.md', '\n'.join(lines))
    print(json.dumps({'output': str(out),
                      'decision_match_rate': o.get('decision_match_rate'),
                      'decision_cohen_kappa': o.get('decision_cohen_kappa'),
                      'persistent_disagreements': len(findings)}, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, choices=('blind', 'final'))
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--round1', type=Path, default=None)
    parser.add_argument('--kit', type=Path,
                        default=ROOT / 'outputs' / 'human_review' / 'blind.v2')
    parser.add_argument('--batch', type=Path,
                        default=ROOT / 'outputs' / 'rubrics_judge.node4.batch.v6.json')
    parser.add_argument('--stability', type=Path,
                        default=ROOT / 'outputs' / 'rubrics_judge.node4.stability.v1.json')
    parser.add_argument('--freeze', type=Path,
                        default=ROOT / 'outputs' / 'rubrics_judge.node3.freeze.v2.json')
    parser.add_argument('--manifest', type=Path,
                        default=ROOT / 'samples' / 'calibration_manifest.json')
    parser.add_argument('--silver-labels', type=Path,
                        default=ROOT / 'samples' / 'calibration' / 'labels')
    args = parser.parse_args(argv)
    return run_blind(args) if args.stage == 'blind' else run_final(args)


if __name__ == '__main__':
    sys.exit(main())
