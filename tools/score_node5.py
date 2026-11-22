# -*- coding: utf-8 -*-
"""Node 5 paired scorer (post-hoc only; nothing here is fed back to the repairer).

Reads a node5_loop run report + node5.freeze.v1, verifies freeze/hash integrity,
classifies each repaired pair (improved / regressed / no_effect / other_change)
per the frozen classification, computes pre-registered rates, a paired bootstrap
CI over total-score deltas (B/seed from freeze), re-audits every repair prompt
independently, and runs the deterministic programmatic side-check against dev
expected.json where available (report-only). Verdict labels are descriptive
signals, NOT reward gates. Refuses overwrite (exit 3).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.webextractor.extractor import extract_html
from src.webextractor.rubrics_v2 import score as program_score
from tools.bootstrap_stats import bootstrap_ci
from tools.node5_loop import (audit_repair_prompt, check_freeze, critic_feedback,
                              load_json, write_json, sha256_bytes, sha256_json)

TOOL_VERSION = '1.0.0'
DECISION_ORDER = {'fail': 0, 'uncertain': 1, 'pass': 2}
SEVERE = ('major', 'critical')


def _dims(assessment):
    return assessment['dimensions']


def _total(assessment):
    return sum(d['score'] for d in _dims(assessment).values() if type(d['score']) is int)


def _scored_set(assessment):
    return tuple(sorted(k for k, d in _dims(assessment).items() if d['score'] is not None))


def _severe_dims(assessment):
    return {k for k, d in _dims(assessment).items() if d.get('severity') in SEVERE}


def classify_pair(before, after):
    """Frozen classification; regressed takes priority (conservative)."""
    ob, oa = DECISION_ORDER[before['decision']], DECISION_ORDER[after['decision']]
    sb, sa = _severe_dims(before), _severe_dims(after)
    new_severe = sorted(sa - sb)
    tb, ta = _total(before), _total(after)
    comparable = _scored_set(before) == _scored_set(after)
    sig_b = {k: (d['score'], d['severity'], d['status']) for k, d in _dims(before).items()}
    sig_a = {k: (d['score'], d['severity'], d['status']) for k, d in _dims(after).items()}
    decision_improved = oa > ob and not new_severe
    decision_regressed = oa < ob
    score_improved = comparable and ta > tb and not new_severe
    if decision_regressed or new_severe:
        category = 'regressed'
    elif decision_improved or score_improved:
        category = 'improved'
    elif sig_a == sig_b:
        category = 'no_effect'
    else:
        category = 'other_change'
    return {'category': category, 'decision_before': before['decision'], 'decision_after': after['decision'],
            'total_before': tb, 'total_after': ta, 'delta': ta - tb,
            'score_comparable': comparable, 'new_severe_dimensions': new_severe,
            'severe_before': sorted(sb), 'severe_after': sorted(sa)}


def _side_summary(ps):
    d = ps['dimensions']
    def g(name, key):
        return (d.get(name) or {}).get(key)
    return {'decision': ps['decision'], 'issue_count': len(ps['issues']),
            'severe_issue_count': sum(1 for i in ps['issues'] if i['severity'] in SEVERE),
            'completeness_score': g('completeness', 'score'), 'recall': g('completeness', 'recall'),
            'cleanliness_score': g('cleanliness', 'score'), 'precision': g('cleanliness', 'precision'),
            'structure_score': g('structure', 'score'), 'order_ratio': g('structure', 'order_ratio'),
            'attribute_ratio': g('structure', 'attribute_ratio'), 'title_score': g('title', 'score')}


def _candidates(row, freeze_case):
    """Recompute baseline deterministically; recover repaired from the trace.

    Both are hash-verified against the runner's recorded candidate hashes.
    """
    sb = (ROOT / freeze_case['source']).read_bytes()
    if sha256_bytes(sb) != row.get('source_sha256'):
        return None, None, 'source sha mismatch'
    base = extract_html(sb)
    baseline = {'title': base.title, 'blocks': base.to_dict()['blocks']}
    if sha256_json(baseline) != row.get('baseline_candidate_sha256'):
        return None, None, 'baseline candidate sha mismatch'
    repaired = None
    if row.get('status') == 'repaired':
        trace = (row.get('repair') or {}).get('trace') or {}
        try:
            execution = trace['attempts'][-1]['executions'][0]['execution']
            result = execution.get('result') or {}
            repaired = {'title': result.get('title', ''), 'blocks': result.get('blocks') or []}
        except (KeyError, IndexError, TypeError):
            return baseline, None, 'repaired candidate missing from trace'
        if sha256_json(repaired) != row.get('repaired_candidate_sha256'):
            return baseline, None, 'repaired candidate sha mismatch'
    return baseline, repaired, None


def score_run(run, freeze, freeze_sha256):
    if run.get('freeze_sha256') != freeze_sha256:
        raise ValueError('run report was not produced from this freeze')
    problems = check_freeze(freeze)
    if problems:
        raise ValueError('freeze verification failed: ' + '; '.join(problems))
    fmap = {c['case_id']: c for c in freeze['cases']}
    rows = run.get('cases') or []
    per_case, pairs = [], []
    audits = {'prompts_audited': 0, 'failures': []}
    integrity = []
    unnecessary = 0
    counts = {}
    for row in rows:
        cid = row['case_id']
        fc = fmap.get(cid)
        if fc is None:
            raise ValueError('unknown case in run: ' + cid)
        if row.get('source_sha256') != fc['source_sha256']:
            raise ValueError('source sha mismatch for ' + cid)
        status = row.get('status')
        counts[status] = counts.get(status, 0) + 1
        entry = {'case_id': cid, 'template': row.get('template'), 'status': status}
        critic = row.get('critic') or {}
        if critic.get('status') == 'accepted':
            fb = critic_feedback(critic)
            entry['baseline_decision'] = critic['assessment']['decision']
            entry['baseline_defect_count'] = len(fb['defects'])
            if (row.get('repair') or {}).get('triggered') and not fb['defects'] \
                    and critic['assessment']['decision'] != 'fail':
                unnecessary += 1
                entry['unnecessary_repair'] = True
        for log_entry in ((row.get('repair') or {}).get('audit_log') or []):
            audits['prompts_audited'] += 1
            res = audit_repair_prompt(log_entry['prompt'], critic)
            extra = [] if res['prompt_sha256'] == log_entry.get('prompt_sha256') else ['audit log sha mismatch']
            if not res['passed'] or extra:
                audits['failures'].append({'case_id': cid, 'problems': res['problems'] + extra})
        for pa in ((row.get('repair') or {}).get('prompt_audit') or []):
            if not pa.get('passed'):
                audits['failures'].append({'case_id': cid, 'problems': ['recorded prompt audit failed'] + pa.get('problems', [])})
        if status == 'repaired':
            pair = classify_pair(critic['assessment'], row['rejudge']['assessment'])
            entry['pair'] = pair
            pairs.append(pair)
        baseline, repaired, cand_problem = _candidates(row, fc)
        if cand_problem:
            entry['candidate_problem'] = cand_problem
            integrity.append({'case_id': cid, 'problem': cand_problem})
        if fc.get('expected') and baseline is not None:
            gold = load_json(ROOT / fc['expected'])
            side = {'before': _side_summary(program_score(baseline, gold)),
                    'note': 'deterministic reference diagnostic; post-hoc only; uncalibrated; never fed back'}
            if repaired is not None:
                side['after'] = _side_summary(program_score(repaired, gold))
            entry['side_check'] = side
        per_case.append(entry)
    critic_accepted = sum(1 for r in rows if (r.get('critic') or {}).get('status') == 'accepted')
    triggered = sum(1 for r in rows if (r.get('repair') or {}).get('triggered'))
    n = len(pairs)
    improved = sum(1 for p in pairs if p['category'] == 'improved')
    regressed = sum(1 for p in pairs if p['category'] == 'regressed')
    no_effect = sum(1 for p in pairs if p['category'] == 'no_effect')
    other = sum(1 for p in pairs if p['category'] == 'other_change')
    rate = lambda k: round(k / n, 4) if n else None
    deltas = [{'delta': p['delta']} for p in pairs]
    ci = bootstrap_ci(deltas, lambda rs: sum(r['delta'] for r in rs) / len(rs),
                      B=freeze['B'], seed=freeze['seed']) if n else {'point': None, 'ci95': None, 'n': 0}
    sc = freeze['success_criteria']
    checks = {'improvement_rate_ge': n > 0 and improved / n >= sc['improvement_rate_ge'],
              'regression_rate_le': n > 0 and regressed / n <= sc['regression_rate_le'],
              'leakage_audit_all_passed': not audits['failures'],
              'unnecessary_repair_zero': unnecessary == 0,
              'candidate_integrity': not integrity}
    verdict = sc['verdict_labels'][0] if all(checks.values()) else sc['verdict_labels'][1]
    return {'tool_version': TOOL_VERSION, 'run_sha256': sha256_json(run), 'freeze_sha256': freeze_sha256,
            'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'per_case': per_case,
            'metrics': {'total_cases': len(rows), 'status_counts': counts,
                        'critic_accepted': critic_accepted, 'repair_triggered': triggered,
                        'repair_trigger_rate': round(triggered / critic_accepted, 4) if critic_accepted else None,
                        'paired_n': n, 'improved': improved, 'regressed': regressed,
                        'no_effect': no_effect, 'other_change': other,
                        'improvement_rate': rate(improved), 'regression_rate': rate(regressed),
                        'no_effect_rate': rate(no_effect), 'unnecessary_repair_count': unnecessary,
                        'mean_total_score_delta_ci95': ci,
                        'non_comparable_pairs': sum(1 for p in pairs if not p['score_comparable'])},
            'audits': audits, 'candidate_integrity_problems': integrity,
            'success_checks': checks, 'verdict': verdict,
            'budget': run.get('budget'),
            'note': ('Descriptive signal only, NOT a reward gate; judge scores remain reward-ineligible (P3 gate FAIL). '
                     'n=6 dev templates, same family: no generalization claim. Agreement != accuracy; '
                     'judge-judged improvement is not verified real-quality improvement. Side-check is post-hoc only.')}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Node 5 paired scorer (post-hoc; freeze required).')
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--freeze-path', type=Path, default=ROOT / 'outputs/node5.freeze.v1.json')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    if args.output.exists():
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    freeze = load_json(args.freeze_path)
    freeze_sha = sha256_bytes(args.freeze_path.read_bytes())
    run = load_json(args.run)
    report = score_run(run, freeze, freeze_sha)
    write_json(args.output, report)
    print(json.dumps({'output': str(args.output), 'verdict': report['verdict'],
                      'metrics': report['metrics']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
