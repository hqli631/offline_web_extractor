"""Pure-Python deterministic GRPO core (P-H H4 readiness scaffold).

Implements the group-relative advantage + clipped surrogate + k3 KL penalty
mathematics of GRPO over a TABULAR policy, with rewards supplied through the
frozen rubrics_reward v1.0.0 interface. NO deep-learning dependency, NO real
model training: this is an offline plumbing/math verification so a future P-E
run can swap the tabular policy for a real LLM and the mock judge for live
v1.4.1 calls. Real training remains gated (docs/P_E_TRAINING_PLAN.md).

Disclosed simplifications: tabular softmax policy with REINFORCE-style logit
updates (not gradient backprop); per-sequence (not per-token) rewards; mock
judge fixtures in the dry-run are SYNTHETIC, not model outputs.
"""
import math

CLIP_EPS = 0.2
KL_COEF = 0.01


def group_advantages(rewards):
    """GRPO group-relative normalization. std==0 -> all-zero (degenerate flag)."""
    if not isinstance(rewards, (list, tuple)) or not rewards:
        raise ValueError('rewards must be a non-empty sequence')
    if any(isinstance(r, bool) or not isinstance(r, (int, float)) or not math.isfinite(r) for r in rewards):
        raise ValueError('rewards must be finite numbers')
    g = len(rewards)
    mean = sum(rewards) / g
    var = sum((r - mean) ** 2 for r in rewards) / g
    std = math.sqrt(var)
    if std == 0.0:
        return [0.0] * g, {'mean': mean, 'std': 0.0, 'degenerate': True}
    return [(r - mean) / std for r in rewards], {'mean': mean, 'std': std, 'degenerate': False}


def kl_k3(logp, ref_logp):
    """k3 KL estimator (non-negative): exp(ref-logp) - (ref-logp) - 1."""
    d = ref_logp - logp
    return math.exp(d) - d - 1.0


def clipped_surrogate(logp, old_logp, advantage, clip_eps=CLIP_EPS):
    ratio = math.exp(logp - old_logp)
    clipped = min(max(ratio, 1.0 - clip_eps), 1.0 + clip_eps)
    return min(ratio * advantage, clipped * advantage)


def grpo_objective(logprobs, old_logprobs, ref_logprobs, advantages,
                   clip_eps=CLIP_EPS, kl_coef=KL_COEF):
    """Mean over items of clipped surrogate minus KL penalty (maximize)."""
    n = len(logprobs)
    if not (n == len(old_logprobs) == len(ref_logprobs) == len(advantages)) or n == 0:
        raise ValueError('length mismatch or empty inputs')
    total = 0.0
    for lp, olp, rlp, adv in zip(logprobs, old_logprobs, ref_logprobs, advantages):
        total += clipped_surrogate(lp, olp, adv, clip_eps) - kl_coef * kl_k3(lp, rlp)
    return total / n


def softmax(logits):
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    s = sum(exps)
    return [e / s for e in exps]


class TabularPolicy:
    """Deterministic tabular softmax policy (readiness scaffold, not an LLM)."""

    def __init__(self, n_actions, seed=20261124):
        if type(n_actions) is not int or n_actions <= 0:
            raise ValueError('n_actions must be a positive int')
        self.logits = [0.0] * n_actions
        self.seed = seed

    def probs(self):
        return softmax(self.logits)

    def sample_group(self, group_size, rng):
        probs = self.probs()
        actions = []
        for _ in range(group_size):
            u = rng.random()
            acc = 0.0
            for i, p in enumerate(probs):
                acc += p
                if u <= acc:
                    actions.append(i)
                    break
            else:
                actions.append(len(probs) - 1)
        return actions

    def update(self, actions, advantages, lr=0.5):
        for a, adv in zip(actions, advantages):
            self.logits[a] += lr * adv
