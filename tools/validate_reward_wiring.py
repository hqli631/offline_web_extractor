# -*- coding: utf-8 -*-
"""Offline reward-wiring validation (docs/REWARD_WIRING_PLAN.md, zero calls).

Reuses the sealed P-D2 / P-G run artifacts: every repaired member with an
accepted critic + accepted rejudge forms a before/after pair. Classifies with
the FROZEN score_node5.classify_pair, computes frozen-mapping rewards, and
checks pre-registered hard checks H1 bounds / H2 determinism / H3 direction
consistency (improved delta>0, regressed delta<0, no_effect delta==0).
Verdict is a mapping sanity check, NOT evidence of real-page reward validity.
Refuses overwrite (exit 3). No network, no model calls, no artifact rewrite.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.node5_loop import load_json, write_json, sha256_bytes, sha256_json
from tools.score_node5 import classify_pair
from src.webextractor.rubrics_reward import (REWARD_MAPPING_VERSION, reward_from_report)

TOOL_VERSION = '1.0.0'
EXPECTED_DIRECTION = {'improved': 1, 'regressed': -1, 'no_effect': 0}


def collect_pairs(run):
    pairs = []
    for crow in run.get('clusters', []):
        for mrow in crow.get('members', []):
            critic, rejudge = mrow.get('critic'), mrow.get('rejudge')
            if not critic or not rejudge:
                continue
            if critic.get('status') != 'accepted' or rejudge.get('status') != 'accepted':
                continue
            pairs.append({'cluster_id': crow.get('cluster_id'), 'case_id': mrow.get('case_id'),
                          'before_report': critic, 'after_report': rejudge})
    return pairs


def validate(runs):
    rows, problems = [], []
    for label, run in runs:
        for pair in collect_pairs(run):
            before = reward_from_report(pair['before_report'])
            after = reward_from_report(pair['after_report'])
            cls = classify_pair(pair['before_report']['assessment'], pair['after_report']['assessment'])
            delta = round(after['reward'] - before['reward'], 6)
            category = cls['category']
            expected = EXPECTED_DIRECTION.get(category)
            if expected is None:
                consistent = None
            elif expected == 0:
                consistent = delta == 0
            else:
                consistent = (delta > 0) if expected > 0 else (delta < 0)
            if consistent is False:
                problems.append('direction mismatch: %s (%s) delta=%s' % (pair['case_id'], category, delta))
            for side, res in (('before', before), ('after', after)):
                if not -1.0 <= res['reward'] <= 1.0:
                    problems.append('bounds violation: %s %s' % (pair['case_id'], side))
            rows.append({'run': label, 'cluster_id': pair['cluster_id'], 'case_id': pair['case_id'],
                         'category': category, 'decision_before': cls['decision_before'],
                         'decision_after': cls['decision_after'],
                         'reward_before': before['reward'], 'reward_after': after['reward'],
                         'delta': delta, 'direction_consistent': consistent,
                         'components_before': before['components'], 'components_after': after['components']})
    if not rows:
        problems.append('no repaired pairs found')
    return rows, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pd2-run', default=str(ROOT / 'outputs' / 'pd2.run.v1.json'))
    parser.add_argument('--pg-run', default=str(ROOT / 'outputs' / 'pg.run.v1.json'))
    parser.add_argument('--out', default=str(ROOT / 'outputs' / 'reward.validation.v1.json'))
    args = parser.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        print('Refusing overwrite: %s' % out)
        return 3
    inputs = {}
    runs = []
    for label, path in (('pd2', args.pd2_run), ('pg', args.pg_run)):
        p = Path(path)
        inputs[label] = {'path': str(p), 'sha256': sha256_bytes(p.read_bytes())}
        runs.append((label, load_json(p)))
    rows, problems = validate(runs)
    again, _ = validate(runs)
    determinism = sha256_json(rows) == sha256_json(again)
    if not determinism:
        problems.append('nondeterministic recomputation')
    directional = [r for r in rows if r['direction_consistent'] is not None]
    consistent = sum(1 for r in directional if r['direction_consistent'])
    hard = {'H1_bounds': all(-1.0 <= r[k] <= 1.0 for r in rows for k in ('reward_before', 'reward_after')),
            'H2_determinism': determinism,
            'H3_direction_consistency': bool(directional) and consistent == len(directional)
            and len(rows) == len(directional)}
    verdict = 'REWARD_WIRING_CONSISTENT' if all(hard.values()) and not problems else 'REWARD_WIRING_INCONSISTENT'
    rewards = [r[k] for r in rows for k in ('reward_before', 'reward_after')]
    report = {
        'tool_version': TOOL_VERSION,
        'mapping_version': REWARD_MAPPING_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'inputs': inputs,
        'pairs': rows,
        'metrics': {'pairs': len(rows), 'directional_pairs': len(directional),
                    'direction_consistent': consistent,
                    'by_category': {c: sum(1 for r in rows if r['category'] == c)
                                    for c in sorted({r['category'] for r in rows})},
                    'reward_min': min(rewards) if rewards else None,
                    'reward_max': max(rewards) if rewards else None,
                    'reward_mean': round(sum(rewards) / len(rewards), 6) if rewards else None},
        'hard_checks': hard,
        'problems': problems,
        'verdict': verdict,
        'scope_disclosure': [
            'Mapping sanity check only; NOT evidence of real-page reward validity.',
            'Judge reward eligibility remains P-F controlled-synthetic scope only.',
            'Real-page reward UNVALIDATED: P-G G3 NO_REAL_TEMPLATE_SIGNAL (over-exclusion regressions).',
            'No injection cases in these runs; injection path covered by unit fixtures only.',
            'Frozen engineering weights, not a validated optimum; no RL training started (P-E gated).',
        ],
        'budget': {'model_calls': 0, 'network_fetches': 0},
    }
    write_json(out, report)
    print(json.dumps({'verdict': verdict, 'hard_checks': hard, 'metrics': report['metrics'],
                      'problems': problems, 'out': str(out),
                      'out_sha256': sha256_bytes(out.read_bytes())}, ensure_ascii=False, indent=2))
    return 0 if verdict == 'REWARD_WIRING_CONSISTENT' else 1


if __name__ == '__main__':
    sys.exit(main())
