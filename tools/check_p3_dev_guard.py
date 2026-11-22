# -*- coding: utf-8 -*-
"""P3 dev-pool regression guard (zero model calls).

Pre-registered in docs/P3_AMENDMENT_PROPOSAL.md section 3: judge v1.3 is
evaluated on the dev pool (tunable round) BEFORE the sealed v3 one-shot is
consumed further. Guard thresholds are read from the FROZEN gate config
(dev section): reject_rate < 0.10, severe_miss_count <= 1,
false_alarm_rate <= 0.15. GUARD_FAIL means the amendment regressed ->
rollback to v1.2 and report honestly (no score chasing). Also reports
decision-match/kappa on the original dev12 subset descriptively (hard gate
checks happen later in score_p3_gate with v3). Integrity fail-closed: data
freezes (v6 for orig, v5 for P2) + frozen protocol signature incl
judge_version. Output refuses overwrite (exit 3).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ingest_human_labels import aggregate_human
from tools.bootstrap_stats import m_reject, m_false_alarm, m_decision_match, m_kappa
from tools.score_p2_results import all_split_records, ci_block, check_p2_freeze
from tools.score_p3_gate import (severe_miss_count, check_protocol, load_json,
                                 write_json, gate_ci_block)
from tools.score_judge_results import check_freeze, sha256_bytes

TOOL_VERSION = '1.0.0'


def guard_checks(pooled, subset, cfg_dev):
    checks = []
    def add(metric, op, thr, obs):
        ok = obs is not None and ((obs < thr) if op == 'lt' else (obs <= thr))
        checks.append({'metric': metric, 'op': op, 'threshold': thr,
                       'observed': round(obs, 4) if isinstance(obs, float) else obs,
                       'pass': bool(ok)})
    add('reject_rate', 'lt', cfg_dev['reject_rate_lt'], m_reject(pooled))
    add('severe_miss_count', 'le', cfg_dev['severe_miss_count_le'],
        severe_miss_count(pooled) if pooled else None)
    add('false_alarm_rate', 'le', cfg_dev['false_alarm_rate_le'], m_false_alarm(pooled))
    return {'verdict': 'GUARD_PASS' if all(c['pass'] for c in checks) else 'GUARD_FAIL',
            'checks': checks,
            'descriptive_subset': {'decision_match_rate': m_decision_match(subset),
                                   'cohen_kappa': m_kappa(subset)}}


def main(argv=None):
    ap = argparse.ArgumentParser(description='P3 dev regression guard (zero calls).')
    ap.add_argument('--gate-config', type=Path, default=ROOT / 'outputs/p3.gate.config.v1.json')
    ap.add_argument('--orig-batch', type=Path, default=ROOT / 'outputs/p3.dev.orig.v1.json')
    ap.add_argument('--orig-gold', type=Path, default=ROOT / 'outputs/human_review/final.v1/human_gold.final.json')
    ap.add_argument('--orig-freeze', type=Path, default=ROOT / 'outputs/rubrics_judge.node3.freeze.v6.json')
    ap.add_argument('--p2-batch', type=Path, default=ROOT / 'outputs/p3.dev.p2.v1.json')
    ap.add_argument('--p2-gold', type=Path, default=ROOT / 'outputs/human_review/p2.gold.v1/human_gold.p2.blind.json')
    ap.add_argument('--p2-freeze', type=Path, default=ROOT / 'outputs/p2.freeze.v5.json')
    ap.add_argument('--silver-dir', type=Path, default=ROOT / 'samples/calibration/labels')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    cfg = load_json(args.gate_config)
    if cfg.get('status') != 'frozen':
        print('GATE-CONFIG: not frozen', file=sys.stderr)
        return 1
    orig = load_json(args.orig_batch)
    p2 = load_json(args.p2_batch)
    problems = []
    problems += ['orig: ' + p for p in check_protocol(orig, cfg)]
    problems += ['orig: ' + p for p in check_freeze(orig, {'cases': []}, load_json(args.orig_freeze))]
    problems += ['p2: ' + p for p in check_protocol(p2, cfg)]
    problems += ['p2: ' + p for p in check_p2_freeze(p2, load_json(args.p2_freeze), ROOT / 'samples/p2_manifest.json')]
    if problems:
        for p in problems:
            print('INTEGRITY: ' + p, file=sys.stderr)
        return 1
    # Dev guard scores the DEV pool only; filter out any frozen_test rows
    # (e.g. when reusing the historical P2 batch which also contains test12).
    orig_recs = [r for r in all_split_records(orig, {c['case_id']: c for c in load_json(args.orig_gold)['cases']}, args.silver_dir)
                 if r['split'] == 'development']
    p2_recs = [r for r in all_split_records(p2, {c['case_id']: c for c in load_json(args.p2_gold)['cases']}, args.silver_dir)
               if r['split'] == 'development']
    pooled = orig_recs + p2_recs
    B, seed = cfg['B'], cfg['seed']
    guard = guard_checks(pooled, orig_recs, cfg['dev'])
    result = {'tool_version': TOOL_VERSION, 'seed': seed, 'B': B,
              'gate_config_sha256': sha256_bytes(args.gate_config.read_bytes()),
              'inputs': {'orig_batch_sha256': sha256_bytes(args.orig_batch.read_bytes()),
                         'p2_batch_sha256': sha256_bytes(args.p2_batch.read_bytes()),
                         'orig_gold_sha256': sha256_bytes(args.orig_gold.read_bytes()),
                         'p2_gold_sha256': sha256_bytes(args.p2_gold.read_bytes())},
              'orig_dev12': {'aggregate': aggregate_human(orig_recs), 'ci95': gate_ci_block(orig_recs, B, seed)},
              'p2_dev6': {'aggregate': aggregate_human(p2_recs), 'ci95': gate_ci_block(p2_recs, B, seed)},
              'pooled_dev18': {'aggregate': aggregate_human(pooled), 'ci95': gate_ci_block(pooled, B, seed)},
              'regression_guard': guard,
              'limitations': ['dev 池为可调参轮；护栏阈值来自冻结 gate-config（修订提案 §3 预注册）。',
                              '原 dev12 gold 经 P0 裁决（锚定局限）；P2 dev6 为盲评 gold（全 uncertain）。',
                              '一致率不是准确率；单一标注者。',
                              'GUARD_FAIL -> 回滚 v1.2 并如实报告，不刷分。']}
    out.mkdir(parents=True)
    write_json(out / 'p3.dev.guard.json', result)
    lines = ['# P3 dev 回归护栏摘要', '',
             '- 判定：**%s**' % guard['verdict'],
             '- orig dev12 match=%s κ=%s；p2 dev6 match=%s' % (
                 guard['descriptive_subset']['decision_match_rate'],
                 guard['descriptive_subset']['cohen_kappa'],
                 result['p2_dev6']['aggregate'].get('decision_match_rate')), '',
             '| 指标 | 阈值 | 观测 | 通过 |', '| --- | --- | --- | --- |']
    for c in guard['checks']:
        lines.append('| %s | %s %s | %s | %s |' % (c['metric'], c['op'], c['threshold'],
                                                   c['observed'], 'YES' if c['pass'] else 'NO'))
    (out / 'P3_DEV_GUARD_SUMMARY.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'verdict': guard['verdict'], 'output': str(out),
                      'orig_match': guard['descriptive_subset']['decision_match_rate'],
                      'orig_kappa': guard['descriptive_subset']['cohen_kappa']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
