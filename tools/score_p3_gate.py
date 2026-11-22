# -*- coding: utf-8 -*-
"""P3 reward-eligibility gate scorer (zero model calls, config-driven).

Scores judge batches on the dev pool (original dev12 + P2 dev6, reported
separately AND pooled) and the one-shot sealed test v3 against sealed human
gold, then applies the PRE-REGISTERED gate thresholds from a frozen gate
config JSON (docs/P3_GATE_PLAN.md section 4). The config must be
status='frozen' with a recorded user approval; draft configs are refused
(exit 1) so thresholds can never be applied before pre-registration.

Hard checks: dev pooled reject/severe_miss/false_alarm; decision-match and
Cohen kappa on the configured original-dev12 subset only (kappa requires
non-degenerate mixed human decisions); v3 reject/severe_miss/false_alarm/
decision-match/pass-recall (pass-recall = among accepted human=pass cases,
fraction judge=pass; undefined -> FAIL, pass-class generalization untestable).
All metrics get case-level bootstrap 95% CIs (B/seed from the frozen config).
Verdict PASS requires EVERY hard check to pass; FAIL is final and honest --
no re-test, no tuning. frozen_test v1 stays permanently sealed; frozen_test
v2 was consumed one-shot in P2 and is never re-scored here.

Integrity is fail-closed: per-batch data freezes (manifest + case hashes)
and protocol parameters checked against the gate config's frozen
batch_config (including judge_version/rubrics_version). Output refuses
overwrite (exit 3). Judge scores are NOT training rewards until gate PASS,
and even then only within the validated scope; reward wiring is separate
future work.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ingest_human_labels import compare_human_case, aggregate_human
from tools.bootstrap_stats import (m_decision_match, m_kappa, m_false_alarm,
                                   m_reject, bootstrap_ci)
from tools.score_p2_results import ci_block
from tools.score_judge_results import sha256_bytes, sha256_json

TOOL_VERSION = '1.0.0'
DEV_REQUIRED = ('reject_rate_lt', 'severe_miss_count_le', 'false_alarm_rate_le',
                'decision_match_ge', 'kappa_ge', 'match_kappa_subset_label')
V3_REQUIRED = ('reject_rate_lt', 'severe_miss_count_le', 'false_alarm_rate_le',
               'decision_match_ge', 'pass_recall_ge')
RATE_KEYS = ('reject_rate_lt', 'false_alarm_rate_le', 'decision_match_ge',
             'kappa_ge', 'pass_recall_ge')


def load_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def write_json(p, v):
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n',
                       encoding='utf-8', newline='')


def m_pass_recall(recs):
    """Among accepted human=pass cases, fraction with judge=pass."""
    a = [r for r in recs
         if r['judge_status'] == 'accepted' and r.get('human_decision') == 'pass']
    if not a:
        return None
    return sum(r.get('judge_decision') == 'pass' for r in a) / len(a)


def severe_miss_count(recs):
    return sum(bool(r.get('severe_miss')) for r in recs
               if r['judge_status'] == 'accepted')


def validate_gate_config(cfg):
    problems = []
    if cfg.get('status') != 'frozen':
        problems.append("gate config status must be 'frozen' (pre-registered "
                        "and user-approved); got %r" % cfg.get('status'))
    for k in ('approved_by', 'approved_at'):
        if not (isinstance(cfg.get(k), str) and cfg.get(k).strip()):
            problems.append('gate config missing approval field ' + k)
    if type(cfg.get('seed')) is not int or cfg['seed'] <= 0:
        problems.append('gate config seed must be a positive int')
    if type(cfg.get('B')) is not int or cfg['B'] < 100:
        problems.append('gate config B must be an int >= 100')
    bc = cfg.get('batch_config')
    if not isinstance(bc, dict) or not bc:
        problems.append('gate config batch_config must be a non-empty dict')
    elif not bc.get('judge_version'):
        problems.append('gate config batch_config must pin judge_version')
    for scope, required in (('dev', DEV_REQUIRED), ('v3', V3_REQUIRED)):
        sec = cfg.get(scope)
        if not isinstance(sec, dict):
            problems.append('gate config missing section ' + scope)
            continue
        for k in required:
            if k not in sec:
                problems.append('gate config %s missing %s' % (scope, k))
        for k in RATE_KEYS:
            if k in sec and not (isinstance(sec[k], (int, float))
                                 and 0 <= sec[k] <= 1):
                problems.append('gate config %s.%s out of [0,1]' % (scope, k))
        if 'severe_miss_count_le' in sec and (
                type(sec['severe_miss_count_le']) is not int
                or sec['severe_miss_count_le'] < 0):
            problems.append('gate config %s.severe_miss_count_le must be int >= 0' % scope)
    return problems


def check_data_freeze(batch, freeze, manifest_path=None):
    """Data integrity vs a per-batch data freeze (manifest + case hashes)."""
    problems = []
    frozen_files = freeze.get('files') or {}
    if batch.get('manifest_sha256') not in frozen_files.values():
        problems.append('batch manifest hash not among frozen file hashes')
    if manifest_path is not None:
        mb = Path(manifest_path).read_bytes()
        if sha256_bytes(mb) != batch.get('manifest_sha256'):
            problems.append('manifest file bytes differ from batch manifest_sha256')
        if freeze.get('manifest_sha256') is not None and \
                sha256_json(json.loads(mb)) != freeze['manifest_sha256']:
            problems.append('manifest canonical hash differs from freeze')
    frozen = {r['case_id']: r for r in freeze.get('cases', [])}
    for row in batch.get('cases', []):
        frow = frozen.get(row['case_id'])
        meta = row.get('case_meta') or {}
        if frow is None:
            problems.append('case not frozen: ' + row['case_id'])
            continue
        for key in ('candidate_sha256', 'source_sha256', 'gold_sha256'):
            if key in frow and meta.get(key) != frow[key]:
                problems.append('%s drift %s' % (key, row['case_id']))
    return problems


def check_protocol(batch, cfg):
    problems = []
    sig = batch.get('signature') or {}
    for k, v in (cfg.get('batch_config') or {}).items():
        if sig.get(k) != v:
            problems.append('batch signature %s=%r != frozen %r' % (k, sig.get(k), v))
    return problems


def records_for(batch, gold, silver_dir):
    cases = gold['cases'] if isinstance(gold, dict) else gold
    gm = {c['case_id']: c for c in cases}
    recs = []
    for row in batch['cases']:
        entry = gm.get(row['case_id'])
        if entry is None:
            raise ValueError('No human gold for ' + row['case_id'])
        sp = Path(silver_dir) / (row['case_id'] + '.label.json')
        silver = load_json(sp) if sp.exists() else None
        r, _ = compare_human_case(row, entry, silver)
        recs.append(r)
    return recs


def _check(scope, metric, op, threshold, observed, note=None):
    if observed is None:
        ok = False
        note = note or 'metric undefined (no eligible cases)'
    elif op == 'lt':
        ok = observed < threshold
    elif op == 'le':
        ok = observed <= threshold
    elif op == 'ge':
        ok = observed >= threshold
    else:
        raise ValueError('unknown op ' + op)
    row = {'scope': scope, 'metric': metric, 'op': op,
           'threshold': threshold,
           'observed': round(observed, 4) if isinstance(observed, float) else observed,
           'pass': bool(ok)}
    if note:
        row['note'] = note
    return row


def evaluate_gate(dev_by_label, v3_recs, cfg):
    """Apply frozen hard thresholds. PASS iff every check passes."""
    d, v = cfg['dev'], cfg['v3']
    pooled = [r for recs in dev_by_label.values() for r in recs]
    subset_label = d['match_kappa_subset_label']
    subset = dev_by_label.get(subset_label) or []
    checks = []
    checks.append(_check('dev_pooled', 'reject_rate', 'lt', d['reject_rate_lt'], m_reject(pooled)))
    checks.append(_check('dev_pooled', 'severe_miss_count', 'le', d['severe_miss_count_le'],
                         severe_miss_count(pooled) if pooled else None))
    checks.append(_check('dev_pooled', 'false_alarm_rate', 'le', d['false_alarm_rate_le'],
                         m_false_alarm(pooled)))
    checks.append(_check('dev_subset:' + subset_label, 'decision_match_rate', 'ge',
                         d['decision_match_ge'], m_decision_match(subset)))
    classes = {r.get('human_decision') for r in subset
               if r['judge_status'] == 'accepted'}
    kappa_note = None if len(classes) >= 2 else \
        'degenerate single-class human gold in kappa subset; non-degenerate mixed decisions required'
    kappa_check = _check('dev_subset:' + subset_label, 'cohen_kappa', 'ge',
                         d['kappa_ge'], m_kappa(subset), kappa_note)
    if len(classes) < 2:
        kappa_check['pass'] = False  # degenerate subset can never satisfy the gate
    checks.append(kappa_check)
    checks.append(_check('v3', 'reject_rate', 'lt', v['reject_rate_lt'], m_reject(v3_recs)))
    checks.append(_check('v3', 'severe_miss_count', 'le', v['severe_miss_count_le'],
                         severe_miss_count(v3_recs) if v3_recs else None))
    checks.append(_check('v3', 'false_alarm_rate', 'le', v['false_alarm_rate_le'],
                         m_false_alarm(v3_recs)))
    checks.append(_check('v3', 'decision_match_rate', 'ge', v['decision_match_ge'],
                         m_decision_match(v3_recs)))
    pr = m_pass_recall(v3_recs)
    checks.append(_check('v3', 'pass_recall', 'ge', v['pass_recall_ge'], pr,
                         None if pr is not None else
                         'no accepted human=pass cases in v3; pass-class generalization untestable'))
    verdict = 'PASS' if all(c['pass'] for c in checks) else 'FAIL'
    return {'verdict': verdict, 'checks': checks,
            'kappa_subset_label': subset_label,
            'kappa_subset_human_classes': sorted(c for c in classes if c)}


def gate_ci_block(recs, B, seed):
    out = ci_block(recs, B, seed)
    out['pass_recall'] = bootstrap_ci(recs, m_pass_recall, B, seed)
    return out


def _label_path(items, what):
    out = {}
    for item in items or []:
        if '=' not in item:
            raise ValueError('%s expects label=path, got %r' % (what, item))
        label, path = item.split('=', 1)
        if label in out:
            raise ValueError('duplicate %s label %r' % (what, label))
        out[label] = Path(path)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description='P3 gate scorer (zero calls; frozen config required).')
    ap.add_argument('--gate-config', type=Path, required=True)
    ap.add_argument('--dev-batch', action='append', required=True, help='label=path (repeatable)')
    ap.add_argument('--dev-gold', action='append', required=True, help='label=path (repeatable)')
    ap.add_argument('--dev-freeze', action='append', required=True, help='label=path (repeatable)')
    ap.add_argument('--dev-silver-dir', action='append', default=None, help='label=path (optional)')
    ap.add_argument('--dev-manifest', action='append', default=None, help='label=path (optional)')
    ap.add_argument('--v3-batch', type=Path, required=True)
    ap.add_argument('--v3-gold', type=Path, required=True)
    ap.add_argument('--v3-freeze', type=Path, required=True)
    ap.add_argument('--v3-silver-dir', type=Path, default=None)
    ap.add_argument('--v3-manifest', type=Path, default=None)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    cfg = load_json(args.gate_config)
    problems = validate_gate_config(cfg)
    if problems:
        for p in problems:
            print('GATE-CONFIG: ' + p, file=sys.stderr)
        return 1
    try:
        batches = _label_path(args.dev_batch, '--dev-batch')
        golds = _label_path(args.dev_gold, '--dev-gold')
        freezes = _label_path(args.dev_freeze, '--dev-freeze')
        silvers = _label_path(args.dev_silver_dir, '--dev-silver-dir')
        manifests = _label_path(args.dev_manifest, '--dev-manifest')
    except ValueError as e:
        print('ARGS: ' + str(e), file=sys.stderr)
        return 1
    if not (set(batches) == set(golds) == set(freezes)):
        print('ARGS: dev batch/gold/freeze labels must match', file=sys.stderr)
        return 1
    if cfg['dev']['match_kappa_subset_label'] not in batches:
        print('GATE-CONFIG: kappa subset label not among dev batches', file=sys.stderr)
        return 1
    integrity = []
    dev_by_label = {}
    seen = set()
    for label, bp in batches.items():
        batch = load_json(bp)
        integrity += ['%s: %s' % (label, p) for p in check_protocol(batch, cfg)]
        integrity += ['%s: %s' % (label, p) for p in
                      check_data_freeze(batch, load_json(freezes[label]), manifests.get(label))]
        for row in batch.get('cases', []):
            if row.get('split') != 'development':
                integrity.append('%s: case %s split != development' % (label, row['case_id']))
            if row['case_id'] in seen:
                integrity.append('%s: duplicate dev case %s' % (label, row['case_id']))
            seen.add(row['case_id'])
        try:
            dev_by_label[label] = records_for(batch, load_json(golds[label]),
                                              silvers.get(label, ROOT / 'samples/calibration/labels'))
        except ValueError as e:
            integrity.append('%s: %s' % (label, e))
    v3batch = load_json(args.v3_batch)
    integrity += ['v3: ' + p for p in check_protocol(v3batch, cfg)]
    integrity += ['v3: ' + p for p in check_data_freeze(v3batch, load_json(args.v3_freeze), args.v3_manifest)]
    for row in v3batch.get('cases', []):
        if row.get('split') != 'frozen_test':
            integrity.append('v3: case %s split != frozen_test' % row['case_id'])
    try:
        v3_recs = records_for(v3batch, load_json(args.v3_gold),
                              args.v3_silver_dir or Path('nonexistent_v3_silver'))
    except ValueError as e:
        integrity.append('v3: ' + str(e))
        v3_recs = []
    if integrity:
        for p in integrity:
            print('INTEGRITY: ' + p, file=sys.stderr)
        return 1
    B, seed = cfg['B'], cfg['seed']
    gate = evaluate_gate(dev_by_label, v3_recs, cfg)
    pooled = [r for recs in dev_by_label.values() for r in recs]
    subset_label = cfg['dev']['match_kappa_subset_label']
    result = {'tool_version': TOOL_VERSION, 'gate_config_sha256': sha256_bytes(args.gate_config.read_bytes()),
              'seed': seed, 'B': B,
              'inputs': {'dev_batches': {l: sha256_bytes(p.read_bytes()) for l, p in batches.items()},
                         'dev_golds': {l: sha256_bytes(p.read_bytes()) for l, p in golds.items()},
                         'dev_freezes': {l: sha256_bytes(p.read_bytes()) for l, p in freezes.items()},
                         'v3_batch_sha256': sha256_bytes(args.v3_batch.read_bytes()),
                         'v3_gold_sha256': sha256_bytes(args.v3_gold.read_bytes()),
                         'v3_freeze_sha256': sha256_bytes(args.v3_freeze.read_bytes())},
              'dev_by_label': {l: {'aggregate': aggregate_human(recs),
                                   'ci95': gate_ci_block(recs, B, seed)}
                               for l, recs in dev_by_label.items()},
              'dev_pooled': {'aggregate': aggregate_human(pooled), 'ci95': gate_ci_block(pooled, B, seed)},
              'v3': {'aggregate': aggregate_human(v3_recs), 'ci95': gate_ci_block(v3_recs, B, seed),
                     'severe_miss_count': severe_miss_count(v3_recs)},
              'gate': gate,
              'limitations': ['单一标注者，IAA 未测（用户决定取消第二标注者）。',
                              '一致率不是准确率；人类 gold 也只是参考之一。',
                              '原 dev12 gold 经 P0 裁决，存在锚定局限；P2 dev6 为纯盲评。',
                              'v3 为一次性封存评估；FAIL 不重测、不调参后重报。',
                              'frozen_test v1 永久封存；v2 已在 P2 一次性消耗，本工具不重评。',
                              'κ 硬阈值仅适用于非退化混合决策的原 dev12 子集。',
                              'gate PASS 仅授权在已验证范围（同模板族、冻结协议、受控变异分布）内奖励化；接线为后续独立工作。',
                              'gate FAIL 时 judge 分数继续禁止作为训练奖励。']}
    out.mkdir(parents=True)
    write_json(out / 'p3.gate.json', result)
    lines = ['# P3 gate 评分摘要', '',
             '- 判定：**%s**（%d/%d 硬检查通过）' % (gate['verdict'],
               sum(c['pass'] for c in gate['checks']), len(gate['checks'])),
             '- bootstrap B=%d seed=%d；输入哈希见 p3.gate.json。' % (B, seed), '',
             '| 范围 | 指标 | 阈值 | 观测 | 通过 |', '| --- | --- | --- | --- | --- |']
    for c in gate['checks']:
        lines.append('| %s | %s | %s %s | %s | %s |' % (
            c['scope'], c['metric'], c['op'], c['threshold'], c['observed'],
            'YES' if c['pass'] else 'NO'))
    lines += ['', '局限：单一标注者；一致率≠准确率；v3 一次性；FAIL 不重测。']
    (out / 'P3_GATE_SUMMARY.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'verdict': gate['verdict'],
                      'checks_passed': sum(c['pass'] for c in gate['checks']),
                      'checks_total': len(gate['checks']), 'output': str(out)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
