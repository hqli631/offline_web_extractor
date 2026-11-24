# -*- coding: utf-8 -*-
"""P-H H4 offline GRPO dry-run + environment audit (ZERO model calls).

Verifies the reward->GRPO plumbing with SYNTHETIC mock judge fixtures through
the frozen rubrics_reward v1.0.0 interface: group advantages (zero mean / unit
std), determinism, reward ordering, tabular policy movement toward high-reward
actions. Audits the real training environment (torch/CUDA etc.) honestly.
This is NOT real training; P-E remains gated (docs/P_E_TRAINING_PLAN.md).
Refuses overwrite.
"""
import argparse
import importlib.util
import json
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.webextractor.grpo_core import TabularPolicy, group_advantages, grpo_objective
from src.webextractor.rubrics_reward import RubricsRewardProvider, REWARD_MAPPING_VERSION
from tools.node5_loop import write_json, sha256_json

TOOL_VERSION = '1.0.0'
SEED = 20261124
STEPS = 6
GROUP_SIZE = 4


def _assess(decision, score, severity):
    dims = {}
    for name in ('completeness', 'cleanliness', 'structure', 'title'):
        dims[name] = {'score': score, 'severity': severity, 'status': 'scored',
                      'reason': 'synthetic dry-run fixture', 'evidence': []}
    dims['format'] = {'score': None, 'severity': 'none', 'status': 'not_applicable'}
    return {'decision': decision, 'dimensions': dims}


ACTION_FIXTURES = (
    ('excellent', _assess('pass', 4, 'none')),
    ('acceptable', _assess('uncertain', 4, 'none')),
    ('noisy', _assess('fail', 2, 'major')),
    ('empty', _assess('fail', 0, 'critical')),
)


def _mock_judge(source, candidate, **kwargs):
    idx = int(candidate['blocks'][0]['text'].split(':')[-1])
    return {'judge_version': '1.4.1', 'status': 'accepted', 'prompt_sha256': 'dryrun',
            'assessment': ACTION_FIXTURES[idx][1],
            'usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}}


def run_dry(seed=SEED, steps=STEPS, group_size=GROUP_SIZE):
    provider = RubricsRewardProvider(_mock_judge)
    action_rewards = []
    for i in range(len(ACTION_FIXTURES)):
        res = provider.reward('dry-source', {'blocks': [{'text': 'action:%d' % i}]}, case_id=ACTION_FIXTURES[i][0])
        action_rewards.append(res['reward'])
    policy = TabularPolicy(len(ACTION_FIXTURES), seed)
    trajectory = [policy.probs()]
    step_rows = []
    for t in range(steps):
        rng = random.Random(seed + t)
        actions = policy.sample_group(group_size, rng)
        rewards = [action_rewards[a] for a in actions]
        advs, stats = group_advantages(rewards)
        mean_abs = abs(sum(advs) / len(advs))
        std_val = stats['std']
        unit_ok = stats['degenerate'] or abs((sum(a * a for a in advs) / len(advs)) ** 0.5 - 1.0) < 1e-9
        objective = grpo_objective([0.0] * group_size, [0.0] * group_size, [0.0] * group_size, advs)
        policy.update(actions, advs, lr=0.5)
        trajectory.append(policy.probs())
        step_rows.append({'step': t, 'actions': actions, 'rewards': rewards,
                          'advantage_mean_abs': mean_abs, 'advantage_std': std_val,
                          'degenerate': stats['degenerate'], 'objective': objective,
                          'zero_mean_ok': mean_abs < 1e-9, 'unit_std_ok': unit_ok})
    checks = {
        'mapping_version_frozen': REWARD_MAPPING_VERSION == '1.0.0',
        'reward_ordering': action_rewards[0] > action_rewards[1] > action_rewards[2] >= action_rewards[3],
        'advantages_zero_mean_all_steps': all(r['zero_mean_ok'] for r in step_rows),
        'advantages_unit_std_all_steps': all(r['unit_std_ok'] for r in step_rows),
        'policy_moves_to_best': trajectory[-1][0] > trajectory[0][0],
        'best_action_reward_is_one': action_rewards[0] == 1.0,
    }
    return {'tool_version': TOOL_VERSION, 'seed': seed, 'steps': steps, 'group_size': group_size,
            'action_fixtures': [n for n, _ in ACTION_FIXTURES], 'action_rewards': action_rewards,
            'mapping_version': REWARD_MAPPING_VERSION, 'step_rows': step_rows,
            'probability_trajectory': trajectory, 'checks': checks,
            'verdict': 'GRPO_PLUMBING_READY' if all(checks.values()) else 'GRPO_PLUMBING_NOT_READY',
            'disclosure': ['SYNTHETIC mock judge fixtures, NOT model outputs',
                           'tabular REINFORCE-style update, NOT gradient backprop',
                           'per-sequence rewards; no real training started (P-E gated)',
                           'worst two fixtures both clip to -1.0 (frozen mapping behavior); ordering check allows the clip tie']}


def env_audit():
    specs = {}
    for name in ('torch', 'numpy', 'transformers', 'trl', 'accelerate'):
        spec = importlib.util.find_spec(name)
        specs[name] = bool(spec)
    cuda = None
    if specs['torch']:
        try:
            import torch
            cuda = bool(torch.cuda.is_available())
        except Exception:
            cuda = None
    return {'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'python': sys.version.split()[0], 'platform': platform.platform(),
            'packages': specs, 'cuda_available': cuda,
            'real_training_feasible_here': bool(specs['torch'] and cuda),
            'note': 'honest audit: real GRPO needs torch+CUDA (or API training) + separate approved budget; not started'}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-out', default=str(ROOT / 'outputs' / 'grpo.dryrun.v1.json'))
    ap.add_argument('--audit-out', default=str(ROOT / 'outputs' / 'grpo.env_audit.v1.json'))
    args = ap.parse_args(argv)
    for p in (args.dry_out, args.audit_out):
        if Path(p).exists():
            print('Refusing overwrite: %s' % p, file=sys.stderr)
            return 3
    dry = run_dry()
    again = run_dry()
    dry['determinism_sha256'] = sha256_json(dry['step_rows'])
    dry['checks']['determinism'] = sha256_json(dry['step_rows']) == sha256_json(again['step_rows'])
    dry['verdict'] = 'GRPO_PLUMBING_READY' if all(dry['checks'].values()) else 'GRPO_PLUMBING_NOT_READY'
    audit = env_audit()
    write_json(args.dry_out, dry)
    write_json(args.audit_out, audit)
    print(json.dumps({'verdict': dry['verdict'], 'checks': dry['checks'],
                      'action_rewards': dry['action_rewards'],
                      'real_training_feasible_here': audit['real_training_feasible_here'],
                      'packages': audit['packages']}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
