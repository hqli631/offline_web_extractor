# -*- coding: utf-8 -*-
"""P2 scoring + pre-registered generalization acceptance (zero model calls).

Scores the judge v1.2 batch on the P2 expansion (dev6 + frozen_test v2 12,
one-shot) against sealed P2 human gold, with case-level bootstrap 95% CIs
(B=10000, seed 20261119). Acceptance per docs/P2_META_EVAL_PLAN.md §4 (R1-R4
revisions): frozen_test v2 reject rate < 10%, severe_miss <= 1, match/κ CIs
reported; dev->test decision-match drop flagged as overfitting risk when the
unpaired bootstrap 95% CI excludes 0 AND the drop > 0.15. (Pre-reg said
'paired'; dev6 and test12 are disjoint case sets, so the difference CI is
unpaired case-level bootstrap — documented operationalization, thresholds
unchanged.) qwen4-max cross-model comparison on the original dev12 is
DESCRIPTIVE ONLY (same family; not cross-family). frozen_test v1 never
 touched. Output refuses overwrite (exit 3).
"""
import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ingest_human_labels import compare_human_case, aggregate_human
from tools.bootstrap_stats import (_accepted, m_decision_match, m_kappa,
                                   m_severe_miss, m_false_alarm, m_reject,
                                   m_dim_exact, m_severity_sign, bootstrap_ci)
from tools.score_judge_results import check_freeze, sha256_bytes, sha256_json

TOOL_VERSION = '1.0.0'
SEED = 20261119
B = 10000
SILVER_DIR = ROOT / 'samples/calibration/labels'
THRESHOLDS = {'reject_rate_lt': 0.10, 'severe_miss_le': 1, 'overfit_drop_gt': 0.15}


def load_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def write_json(p, v):
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')


def all_split_records(batch, gm, silver_dir):
    """Like bootstrap_stats._records but keeps BOTH splits (P2 test12 is scored)."""
    recs = []
    for row in batch['cases']:
        cid = row['case_id']
        entry = gm.get(cid)
        if entry is None:
            raise ValueError('No human gold for ' + cid)
        sp = Path(silver_dir) / (cid + '.label.json')
        silver = load_json(sp) if sp.exists() else None
        r, _ = compare_human_case(row, entry, silver)
        recs.append(r)
    return recs


def gold_map(gold):
    cases = gold['cases'] if isinstance(gold, dict) else gold
    return {c['case_id']: c for c in cases}


def check_p2_freeze(batch, freeze, manifest_path):
    problems = []
    files = freeze.get('files') or {}
    rel = 'samples/p2_manifest.json'
    if batch.get('manifest_sha256') != files.get(rel):
        problems.append('batch manifest file hash differs from freeze v5 files entry')
    mb = Path(manifest_path).read_bytes()
    if sha256_bytes(mb) != files.get(rel):
        problems.append('manifest file bytes differ from freeze v5')
    if sha256_json(json.loads(mb)) != freeze.get('manifest_sha256'):
        problems.append('manifest canonical hash differs from freeze v5')
    sig = batch.get('signature') or {}
    for k, v in (freeze.get('batch_config') or {}).items():
        if sig.get(k) != v:
            problems.append('batch signature %s=%r != frozen %r' % (k, sig.get(k), v))
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


def unpaired_diff_ci(recsA, recsB, fn, B, seed):
    a, b = _accepted(recsA), _accepted(recsB)
    if not a or not b:
        return None
    rng = random.Random(seed)
    diffs = []
    for _ in range(B):
        sa = [a[rng.randrange(len(a))] for _ in a]
        sb = [b[rng.randrange(len(b))] for _ in b]
        va, vb = fn(sa), fn(sb)
        if va is None or vb is None:
            continue
        diffs.append(va - vb)
    if not diffs:
        return None
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[min(len(diffs) - 1, int(0.975 * len(diffs)))]
    point = fn(a) - fn(b)
    return {'diff_A_minus_B': round(point, 4), 'ci95': [round(lo, 4), round(hi, 4)],
            'excludes_zero': bool(lo > 0 or hi < 0), 'B_effective': len(diffs)}


def ci_block(recs, B, seed):
    out = {}
    for name, fn in (('decision_match', m_decision_match), ('kappa', m_kappa),
                     ('dim_exact', m_dim_exact), ('severity_sign', m_severity_sign),
                     ('severe_miss', m_severe_miss), ('false_alarm', m_false_alarm),
                     ('reject', m_reject)):
        out[name] = bootstrap_ci(recs, fn, B, seed)
    return out


def generalization_acceptance(dev_recs, test_recs, B, seed):
    agg_test = aggregate_human(test_recs)
    n = agg_test['n_cases']
    reject_rate = round(agg_test['rejected'] / n, 4) if n else None
    severe_miss = len(agg_test.get('severe_miss_cases', []))
    checks = {'reject_rate_lt_0.10': reject_rate is not None and reject_rate < THRESHOLDS['reject_rate_lt'],
              'severe_miss_le_1': severe_miss <= THRESHOLDS['severe_miss_le']}
    drop = unpaired_diff_ci(dev_recs, test_recs, m_decision_match, B, seed)
    overfit = bool(drop and drop['excludes_zero'] and drop['diff_A_minus_B'] > THRESHOLDS['overfit_drop_gt'])
    return {'n_test': n, 'reject_rate': reject_rate, 'severe_miss_count': severe_miss,
            'thresholds': THRESHOLDS, 'checks': checks,
            'verdict': 'ACCEPT' if all(checks.values()) else 'REJECT',
            'dev_minus_test_match': drop, 'overfit_flag': overfit,
            'note': 'one-shot frozen_test v2; no tuning. Overfit flag is an honest risk marker, not a threshold rewrite.'}


def status_artifact(rows):
    n = 0
    for r in rows:
        for d in (r.get('dimensions') or {}).values():
            if d.get('human_status') == 'scored' and d.get('judge_status') == 'partial':
                n += 1
    return {'human_scored_judge_partial_dims': n,
            'note': 'mechanical truncation downgrade (judge forces partial when source truncated); not a semantic disagreement.'}


def cross_model_section(cross_batch, p15_batch, p0_gold, silver_dir):
    if cross_batch is None:
        return None
    gm = gold_map(p0_gold) if p0_gold is not None else {}
    b1 = {r['case_id']: r for r in (p15_batch or {}).get('cases', [])}
    jj, jh = [], []
    for row2 in cross_batch['cases']:
        cid = row2['case_id']
        rep2 = row2.get('report') or {}
        silver = None
        sp = Path(silver_dir) / (cid + '.label.json')
        if sp.exists():
            silver = load_json(sp)
        if rep2.get('status') == 'accepted' and cid in gm:
            r, _ = compare_human_case(row2, gm[cid], silver)
            jh.append(r)
        row1 = b1.get(cid)
        if row1 is None:
            continue
        rep1 = row1.get('report') or {}
        if rep1.get('status') != 'accepted' or rep2.get('status') != 'accepted':
            jj.append({'case_id': cid, 'judge_status': 'rejected_pair',
                       'judge1_status': rep1.get('status'), 'judge2_status': rep2.get('status')})
            continue
        a2 = rep2['assessment']
        entry2 = {'decision': a2['decision'], 'dimensions': a2['dimensions']}
        r, _ = compare_human_case(row1, entry2, silver)
        r['case_id'] = cid
        jj.append(r)
    jj_acc = [r for r in jj if r.get('judge_status') == 'accepted']
    return {'model2': (cross_batch.get('signature') or {}).get('model'),
            'n_cases': len(cross_batch['cases']),
            'judge2_rejected': sum(1 for r in cross_batch['cases'] if (r.get('report') or {}).get('status') != 'accepted'),
            'judge1_vs_judge2': {'both_accepted': len(jj_acc),
                                 'agreement': aggregate_human(jj_acc) if jj_acc else {}},
            'judge2_vs_p0_human': aggregate_human(jh) if jh else {},
            'note': 'DESCRIPTIVE cross-model (same Qwen family) agreement; not cross-family, not accuracy.'}


def main(argv=None):
    ap = argparse.ArgumentParser(description='P2 scoring + generalization acceptance (offline).')
    ap.add_argument('--p2-batch', type=Path, required=True)
    ap.add_argument('--gold', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, default=ROOT / 'samples/p2_manifest.json')
    ap.add_argument('--freeze-v5', type=Path, default=ROOT / 'outputs/p2.freeze.v5.json')
    ap.add_argument('--cross-batch', type=Path, default=None)
    ap.add_argument('--p15-batch', type=Path, default=ROOT / 'outputs/p1_5.dev.v1.json')
    ap.add_argument('--p0-gold', type=Path, default=ROOT / 'outputs/human_review/final.v1/human_gold.final.json')
    ap.add_argument('--freeze-v4', type=Path, default=ROOT / 'outputs/rubrics_judge.node3.freeze.v4.json')
    ap.add_argument('--bootstrap-B', type=int, default=B)
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    batch = load_json(args.p2_batch)
    freeze5 = load_json(args.freeze_v5)
    problems = check_p2_freeze(batch, freeze5, args.manifest)
    if problems:
        for p in problems:
            print('FREEZE: ' + p, file=sys.stderr)
        return 1
    gm = gold_map(load_json(args.gold))
    recs = all_split_records(batch, gm, SILVER_DIR)
    dev = [r for r in recs if r['split'] == 'development']
    test = [r for r in recs if r['split'] == 'frozen_test']
    cross = None
    if args.cross_batch is not None:
        cb = load_json(args.cross_batch)
        fz4 = load_json(args.freeze_v4)
        cp = check_freeze(cb, {'cases': []}, fz4)
        sig = cb.get('signature') or {}
        for k, v in (fz4.get('batch_config') or {}).items():
            if k != 'model' and sig.get(k) != v:
                cp.append('cross batch signature %s != frozen %r' % (k, v))
        if cp:
            for p in cp:
                print('FREEZE(cross): ' + p, file=sys.stderr)
            return 1
        cross = cross_model_section(cb, load_json(args.p15_batch) if args.p15_batch.exists() else None,
                                    load_json(args.p0_gold) if args.p0_gold.exists() else None, SILVER_DIR)
    acc = generalization_acceptance(dev, test, args.bootstrap_B, args.seed)
    result = {'tool_version': TOOL_VERSION, 'seed': args.seed, 'B': args.bootstrap_B,
              'inputs': {'p2_batch_sha256': sha256_bytes(args.p2_batch.read_bytes()),
                         'gold_sha256': sha256_bytes(args.gold.read_bytes()),
                         'freeze_v5_sha256': sha256_bytes(args.freeze_v5.read_bytes()),
                         'cross_batch_sha256': sha256_bytes(args.cross_batch.read_bytes()) if args.cross_batch else None},
              'dev6': {'aggregate': aggregate_human(dev), 'ci95': ci_block(dev, args.bootstrap_B, args.seed),
                       'status_artifact': status_artifact(dev)},
              'frozen_test_v2': {'aggregate': aggregate_human(test), 'ci95': ci_block(test, args.bootstrap_B, args.seed),
                                 'status_artifact': status_artifact(test)},
              'generalization_acceptance': acc,
              'cross_model_descriptive': cross,
              'limitations': ['单一标注者，IAA 未测（用户决定）。',
                              '人类 gold 决策若为单类（全 uncertain），Cohen κ 退化（pe=1）；决策一致率是首要指标，κ 仅作参考。',
                              '一致率不是准确率；dev 与泛化分开报告。',
                              'qwen4-max 为同家族跨模型比较，非跨家族。',
                              'frozen_test v2 一次性评估，未调参；frozen_test v1 永久封存。',
                              'Judge 分数仍不作为训练奖励。']}
    out.mkdir(parents=True)
    write_json(out / 'p2.scored.json', result)
    lines = ['# P2 评分摘要', '',
             '- dev6 决策一致率：%s（κ=%s）' % (result['dev6']['aggregate'].get('decision_match_rate'), result['dev6']['aggregate'].get('decision_cohen_kappa')),
             '- frozen_test v2 决策一致率：%s（κ=%s）' % (result['frozen_test_v2']['aggregate'].get('decision_match_rate'), result['frozen_test_v2']['aggregate'].get('decision_cohen_kappa')),
             '- 泛化验收：%s（reject=%s, severe_miss=%s, overfit_flag=%s）' % (acc['verdict'], acc['reject_rate'], acc['severe_miss_count'], acc['overfit_flag']),
             '- 详见 p2.scored.json（bootstrap B=%d seed=%d）。' % (args.bootstrap_B, args.seed)]
    (out / 'P2_SCORED_SUMMARY.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'verdict': acc['verdict'], 'overfit_flag': acc['overfit_flag'],
                      'test_match': result['frozen_test_v2']['aggregate'].get('decision_match_rate'),
                      'output': str(out)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
