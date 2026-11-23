# -*- coding: utf-8 -*-
"""P-D2 scorer: generalization metrics + paired classification (post-hoc only).

Reads a run_pd2_generalize report + pd2.freeze.v1, verifies freeze/hash integrity,
classifies each repaired pair with the FROZEN node5 classify_pair, computes
pre-registered rates + paired bootstrap CI (B/seed from freeze), re-audits every
repair prompt, and summarizes the NEW generalization evidence: multi-layout
feedback acceptance, reuse recovery after inline feedback, and repair-call
amortization. Verdict labels are descriptive signals, NOT reward gates.
Nothing is fed back. Refuses overwrite (exit 3).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.bootstrap_stats import bootstrap_ci
from tools.score_node5 import classify_pair
from tools.node5_loop import load_json, write_json, sha256_bytes, sha256_json
from tools.run_pd2_generalize import check_freeze

TOOL_VERSION = '1.0.0'


def _repaired_from_trace(mrow):
    trace = (mrow.get('repair') or {}).get('trace') or {}
    try:
        execution = next(e['execution'] for e in trace['attempts'][-1]['executions']
                         if e['id'] == mrow['case_id'])
        result = execution.get('result') or {}
        return {'title': result.get('title', ''), 'blocks': result.get('blocks') or []}
    except (KeyError, IndexError, TypeError, StopIteration):
        return None


def score_run(run, freeze, freeze_sha):
    problems = check_freeze(freeze)
    freeze_cases = {c['case_id']: c for c in freeze['cases']}
    per_case, pairs, feedback_rows = [], [], []
    audits = {'checked': 0, 'failures': []}
    integrity = []
    unnecessary = 0
    overrides = []
    for crow in run.get('clusters', []):
        cid = crow['cluster_id']
        for mrow in crow.get('members', []):
            mid = mrow['case_id']
            entry = {'cluster_id': cid, 'case_id': mid, 'status': mrow['status'],
                     'reuse': mrow.get('reuse'), 'baseline_decision': mrow.get('baseline_decision'),
                     'baseline_defect_count': mrow.get('baseline_defect_count'),
                     'trigger_reason': (mrow.get('repair') or {}).get('trigger_reason'),
                     'repair_reference_ids': (mrow.get('repair') or {}).get('reference_ids')}
            audits['checked'] += 1
            fc = freeze_cases.get(mid)
            if fc and mrow.get('source_sha256') != fc['source_sha256']:
                integrity.append({'case_id': mid, 'problem': 'source sha mismatch'})
            if (mrow.get('reuse') or {}).get('generalized_override'):
                overrides.append({'cluster_id': cid, 'case_id': mid})
            for pa in ((mrow.get('repair') or {}).get('prompt_audit') or []):
                if not pa.get('passed'):
                    audits['failures'].append({'case_id': mid, 'problems': ['recorded prompt audit failed'] + pa.get('problems', [])})
            repair = mrow.get('repair') or {}
            if repair.get('triggered'):
                drift = bool((mrow.get('reuse') or {}).get('drift_reasons'))
                if not drift and not mrow.get('baseline_defect_count') and mrow.get('baseline_decision') != 'fail':
                    unnecessary += 1
            critic = mrow.get('critic') or {}
            rejudge = mrow.get('rejudge') or {}
            if mrow.get('status') == 'repaired' and critic.get('status') == 'accepted' and rejudge.get('status') == 'accepted':
                pair = classify_pair(critic['assessment'], rejudge['assessment'])
                entry['pair'] = pair
                pairs.append(pair)
                repaired = _repaired_from_trace(mrow)
                if repaired is None or sha256_json(repaired) != mrow.get('repaired_candidate_sha256'):
                    integrity.append({'case_id': mid, 'problem': 'repaired candidate sha mismatch'})
            entry['baseline_quality'] = mrow.get('baseline_quality')
            entry['repaired_quality'] = mrow.get('repaired_quality')
            bq, rq = mrow.get('baseline_quality'), mrow.get('repaired_quality')
            if bq and rq:
                entry['recall_delta'] = round(rq['block_text_recall'] - bq['block_text_recall'], 6)
            per_case.append(entry)
        fb = crow.get('feedback') or {}
        feedback_rows.append({'cluster_id': cid, 'rep_id': crow.get('rep_id'),
                              'multi_layout': crow.get('multi_layout'), 'layouts': crow.get('layouts'),
                              'shared_rule': crow.get('shared_rule'),
                              'attempted': fb.get('attempted'), 'accepted': fb.get('accepted'),
                              'events': fb.get('events'),
                              'reuse_recovery': crow.get('reuse_recovery'),
                              'amortization': crow.get('amortization'),
                              'member_rule_cache': crow.get('member_rule_cache')})
    return _aggregate(run, freeze, freeze_sha, problems, per_case, pairs, feedback_rows,
                      audits, integrity, unnecessary, overrides)


def _aggregate(run, freeze, freeze_sha, problems, per_case, pairs, feedback_rows, audits, integrity, unnecessary, overrides):
    n = len(pairs)
    improved = sum(1 for p in pairs if p['category'] == 'improved')
    regressed = sum(1 for p in pairs if p['category'] == 'regressed')
    no_effect = sum(1 for p in pairs if p['category'] == 'no_effect')
    other = sum(1 for p in pairs if p['category'] == 'other_change')
    rate = lambda k: round(k / n, 4) if n else None
    deltas = [{'delta': p['delta']} for p in pairs]
    ci = bootstrap_ci(deltas, lambda rs: sum(r['delta'] for r in rs) / len(rs),
                      B=freeze['B'], seed=freeze['seed']) if n else {'point': None, 'ci95': None, 'n': 0}
    status_counts = {}
    for e in per_case:
        status_counts[e['status']] = status_counts.get(e['status'], 0) + 1
    triggered = sum(1 for e in per_case if e.get('trigger_reason'))
    multi_layout_accepted = sum(1 for f in feedback_rows if f.get('multi_layout') and f.get('accepted'))
    feedback_accepted = sum(1 for f in feedback_rows if f.get('accepted'))
    feedback_attempted = sum(1 for f in feedback_rows if f.get('attempted'))
    recovery_total = sum(len(f.get('reuse_recovery') or []) for f in feedback_rows)
    gen_calls = sum((f.get('amortization') or {}).get('rule_generation_calls', 0) for f in feedback_rows)
    sc = freeze['success_criteria']
    checks = {'multi_layout_feedback_accepted_ge': multi_layout_accepted >= sc['multi_layout_feedback_accepted_ge'],
              'reuse_recovery_after_feedback_ge': recovery_total >= sc['reuse_recovery_after_feedback_ge'],
              'improvement_rate_ge': n > 0 and improved / n >= sc['improvement_rate_ge'],
              'regression_rate_le': n > 0 and regressed / n <= sc['regression_rate_le'],
              'leakage_audit_all_passed': not audits['failures'],
              'unnecessary_repair_zero': unnecessary == 0,
              'candidate_integrity': not integrity,
              'freeze_integrity': not problems}
    verdict = sc['verdict_labels'][0] if all(checks.values()) else sc['verdict_labels'][1]
    return {'tool_version': TOOL_VERSION, 'run_sha256': sha256_json(run), 'freeze_sha256': freeze_sha,
            'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'freeze_problems': problems, 'per_case': per_case, 'feedback': feedback_rows,
            'metrics': {'total_members': len(per_case), 'status_counts': status_counts,
                        'repair_triggered': triggered, 'paired_n': n, 'improved': improved, 'regressed': regressed,
                        'no_effect': no_effect, 'other_change': other, 'improvement_rate': rate(improved),
                        'regression_rate': rate(regressed), 'no_effect_rate': rate(no_effect),
                        'unnecessary_repair_count': unnecessary, 'mean_total_score_delta_ci95': ci,
                        'feedback_attempted': feedback_attempted, 'feedback_accepted': feedback_accepted,
                        'multi_layout_feedback_accepted': multi_layout_accepted,
                        'reuse_recovery_total': recovery_total,
                        'rule_generation_calls': gen_calls,
                        'calls_per_recovered': round(gen_calls / recovery_total, 4) if recovery_total else None,
                        'generalized_override_events': overrides},
            'audits': audits, 'candidate_integrity_problems': integrity, 'success_checks': checks, 'verdict': verdict,
            'budget': run.get('budget'),
            'note': ('Descriptive signal only, NOT a reward gate; controlled synthetic drift_lab v2 (7 pages), small paired n, wide CI; '
                     'cluster/layout labels authored (purity != accuracy); judge-judged improvement != verified real-quality improvement; '
                     'union XPath noise risk on real complex pages unproven; feedback validation uses dev expected orchestrator-side only; '
                     'judge scores remain NOT training rewards.')}


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-D2 generalization scorer (post-hoc; freeze required).')
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--freeze-path', type=Path, default=ROOT / 'outputs/pd2.freeze.v1.json')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    if args.output.exists():
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    run = load_json(args.run)
    freeze = load_json(args.freeze_path)
    freeze_sha = sha256_bytes(args.freeze_path.read_bytes())
    if run.get('freeze_sha256') != freeze_sha:
        print('Run was not produced against this freeze.', file=sys.stderr)
        return 1
    result = score_run(run, freeze, freeze_sha)
    write_json(args.output, result)
    print(json.dumps({'output': str(args.output), 'verdict': result['verdict'],
                      'metrics': result['metrics'], 'success_checks': result['success_checks']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
