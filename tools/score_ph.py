# -*- coding: utf-8 -*-
"""P-H H1 scorer: guarded-loop v1.1 metrics (post-hoc only).

Mirrors score_pd2.score_run with pg-repair freeze integrity, then reuses the
FROZEN score_pd2._aggregate (classify_pair + bootstrap + generalization metrics +
verdict). Natural pages have no gold: recall_delta only where silver expected
exists; judge classification is the quality evidence. Nothing fed back. Refuses
overwrite.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.score_node5 import classify_pair
from tools.node5_loop import load_json, write_json, sha256_bytes, sha256_json
from tools.run_ph_repair import check_freeze
from tools.score_pd2 import _repaired_from_trace
from tools.bootstrap_stats import bootstrap_ci
from src.webextractor.rubrics_reward import reward_from_report

TOOL_VERSION = '1.0.0'


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
                silver_low = bool(mrow.get('baseline_quality')) and mrow['baseline_quality'].get('block_text_recall', 1) < 1.0
                if not drift and not mrow.get('baseline_defect_count') and mrow.get('baseline_decision') != 'fail' and not silver_low:
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
                              'events': fb.get('events'), 'reuse_recovery': crow.get('reuse_recovery'),
                              'amortization': crow.get('amortization'),
                              'member_rule_cache': crow.get('member_rule_cache')})
    return _ph_aggregate(run, freeze, freeze_sha, problems, per_case, pairs, feedback_rows,
                         audits, integrity, unnecessary, overrides)


def _ph_aggregate(run, freeze, freeze_sha, problems, per_case, pairs, feedback_rows,
                  audits, integrity, unnecessary, overrides):
    n = len(pairs)
    cats = ('improved', 'regressed', 'no_effect', 'other_change')
    counts = {c: sum(1 for p in pairs if p['category'] == c) for c in cats}
    rates = {c + '_rate': round(counts[c] / n, 6) if n else None for c in cats}
    ci = bootstrap_ci(pairs, lambda rs: sum(r['delta'] for r in rs) / len(rs),
                      freeze['B'], freeze['seed']) if pairs else {'point': None, 'ci95': None, 'n': 0}
    gate1_skipped, retention_rejected, retention_violations = [], [], []
    reward_pairs = []
    for crow in run.get('clusters', []):
        for m in crow.get('members', []):
            note = (m.get('repair') or {}).get('note') or ''
            if m.get('status') == 'no_repair_needed' and note.startswith('v1.1 GATE-1'):
                gate1_skipped.append(m['case_id'])
            if m.get('status') == 'repair_rejected_retention':
                retention_rejected.append(m['case_id'])
            rr = (m.get('repair') or {}).get('retention_recall')
            if m.get('status') == 'repaired' and rr is not None and rr < 0.9:
                retention_violations.append(m['case_id'])
            c, r = m.get('critic') or {}, m.get('rejudge') or {}
            if m.get('status') == 'repaired' and c.get('status') == 'accepted' and r.get('status') == 'accepted':
                rb = reward_from_report(c)
                ra = reward_from_report(r)
                reward_pairs.append({'case_id': m['case_id'], 'reward_before': rb['reward'],
                                     'reward_after': ra['reward'],
                                     'reward_delta': round(ra['reward'] - rb['reward'], 6)})
    budget = run.get('budget') or {}
    fb = freeze.get('budget') or {}
    hard = {
        'regression_rate_le_0_10': n > 0 and rates['regressed_rate'] is not None and rates['regressed_rate'] <= 0.10,
        'retention_guard_violations_accepted_zero': not retention_violations,
        'leakage_audit_all_passed': not audits['failures'],
        'integrity_clean': not integrity and not problems,
        'budget_respected': budget.get('used', 0) <= fb.get('token_cap', 0) and budget.get('calls', 0) <= fb.get('max_calls', 0),
    }
    verdict = 'GUARDED_LOOP_SIGNAL' if all(hard.values()) else 'NO_GUARDED_LOOP_SIGNAL'
    return {'tool_version': '1.1.0', 'run_sha256': sha256_bytes(json.dumps(run, ensure_ascii=False, sort_keys=True).encode()),
            'freeze_sha256': freeze_sha, 'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'freeze_problems': problems, 'per_case': per_case, 'feedback': feedback_rows,
            'metrics': {'paired_n': n, 'category_counts': counts, **rates,
                        'mean_total_score_delta_ci95': ci,
                        'gate1_skipped': gate1_skipped, 'gate1_skipped_count': len(gate1_skipped),
                        'retention_rejected': retention_rejected,
                        'retention_violations_accepted': retention_violations,
                        'unnecessary_repair_count': unnecessary,
                        'reward_pairs': reward_pairs,
                        'multi_layout_feedback_accepted': sum(1 for f in feedback_rows if f.get('accepted') and f.get('multi_layout')),
                        'reuse_recovery_total': sum(len(f.get('reuse_recovery') or []) for f in feedback_rows)},
            'audits': audits, 'candidate_integrity_problems': integrity, 'overrides': overrides,
            'hard_checks': hard, 'verdict': verdict, 'budget': budget,
            'note': ('H1 guarded loop v1.1; dev circularity disclosed (gates motivated by G3 regressions on SAME corpus); '
                     'NOT an independent holdout; natural pages no gold; judge reward eligibility remains P-F controlled-synthetic scope; '
                     'reward deltas descriptive sanity, NOT real-page reward validation; negative results honest.')}


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-H H1 guarded-loop scorer (post-hoc).')
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--freeze-path', type=Path, default=ROOT / 'outputs/ph.repair.freeze.v1.json')
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
                      'metrics': result['metrics'], 'hard_checks': result['hard_checks']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
