"""A small, deterministic rule-search environment for PPO/GRPO study.

This module is intentionally a one-step bandit.  Its purpose is to make reward
design, sparse feedback and group-relative updates observable without a deep
learning dependency; it is not an implementation of production Agentic RL.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import math
import random
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class Candidate:
    name: str
    blocks: tuple[str, ...]
    kinds: tuple[str, ...]
    xpath: str


@dataclass(frozen=True)
class Outcome:
    action: str
    predicted_blocks: tuple[str, ...]
    predicted_kinds: tuple[str, ...]
    exact: bool
    precision: float
    recall: float
    f1: float


GOLD_BLOCKS = ("Introduction", "Main result")
GOLD_KINDS = ("paragraph", "paragraph")

# The over-inclusive candidate is deliberately plausible: a DOM rule that
# reaches the article plus navigation/recommendations.  It contains all gold
# text, so recall-only or length-biased rewards prefer it.
DEFAULT_CANDIDATES = (
    Candidate("exact", GOLD_BLOCKS, GOLD_KINDS, "//article[@id='post']/div[@class='content']"),
    Candidate("long-noise", ("Navigation", *GOLD_BLOCKS, "Recommended", "Comments"),
              ("navigation", *GOLD_KINDS, "recommendation", "comments"), "//article"),
    Candidate("partial", ("Introduction",), ("paragraph",), "//article[@id='post']/p[1]"),
    Candidate("empty", (), (), "//missing"),
)


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def assess(candidate: Candidate, gold: tuple[str, ...] = GOLD_BLOCKS) -> Outcome:
    predicted = Counter(candidate.blocks)
    expected = Counter(gold)
    matched = sum((predicted & expected).values())
    precision = matched / len(candidate.blocks) if candidate.blocks else 0.0
    recall = matched / len(gold) if gold else (1.0 if not candidate.blocks else 0.0)
    exact = candidate.blocks == gold and candidate.kinds == GOLD_KINDS
    return Outcome(candidate.name, candidate.blocks, candidate.kinds, exact,
                   precision, recall, _f1(precision, recall))


def sparse_reward(outcome: Outcome) -> float:
    """Terminal reward: only a structurally exact extraction receives 1."""
    return 1.0 if outcome.exact else 0.0


def proxy_reward(outcome: Outcome, gold_size: int = 2) -> float:
    """A deliberately bad recall/length reward used to expose reward hacking."""
    # It rewards returning more text and ignores precision and block kinds.
    return len(outcome.predicted_blocks) / max(1, gold_size)


def corrected_reward(outcome: Outcome) -> float:
    """Dense reward that penalizes noise through precision and structure."""
    structure = 1.0 if outcome.predicted_kinds == GOLD_KINDS else 0.0
    return 0.45 * outcome.precision + 0.45 * outcome.recall + 0.10 * structure


REWARDS: dict[str, Callable[[Outcome], float]] = {
    "sparse": sparse_reward,
    "proxy": proxy_reward,
    "corrected": corrected_reward,
}


class RuleSearchEnv:
    """Finite one-step environment whose actions are fixed candidate rules."""

    def __init__(self, candidates: Iterable[Candidate] = DEFAULT_CANDIDATES,
                 gold: tuple[str, ...] = GOLD_BLOCKS):
        self.candidates = tuple(candidates)
        self.gold = tuple(gold)
        if not self.candidates or len({c.name for c in self.candidates}) != len(self.candidates):
            raise ValueError("Candidates must be nonempty and uniquely named")
        self._done = False

    @property
    def action_names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.candidates)

    def reset(self) -> dict[str, object]:
        self._done = False
        return {"observation": "choose_one_xpath", "actions": self.action_names}

    def step(self, action: str) -> tuple[Outcome, float, bool, dict[str, object]]:
        if self._done:
            raise RuntimeError("Episode is finished; call reset()")
        matches = [c for c in self.candidates if c.name == action]
        if not matches:
            raise ValueError(f"Unknown action: {action}")
        self._done = True
        outcome = assess(matches[0], self.gold)
        return outcome, 0.0, True, {"xpath": matches[0].xpath}


def _softmax(logits: list[float]) -> list[float]:
    maximum = max(logits)
    weights = [math.exp(value - maximum) for value in logits]
    total = sum(weights)
    return [weight / total for weight in weights]


def _sample(probabilities: list[float], rng: random.Random) -> int:
    draw = rng.random()
    total = 0.0
    for index, probability in enumerate(probabilities):
        total += probability
        if draw <= total:
            return index
    return len(probabilities) - 1


def _update(logits: list[float], index: int, advantage: float,
            probabilities: list[float], learning_rate: float) -> None:
    for position in range(len(logits)):
        logits[position] += learning_rate * advantage * ((1.0 if position == index else 0.0) - probabilities[position])


def train_reinforce(env: RuleSearchEnv, reward_name: str, *, seed: int = 7,
                    episodes: int = 300, learning_rate: float = 0.25) -> dict:
    if reward_name not in REWARDS:
        raise ValueError(f"Unknown reward: {reward_name}")
    if episodes < 1 or learning_rate <= 0:
        raise ValueError("episodes and learning_rate must be positive")
    rng = random.Random(seed)
    logits = [0.0] * len(env.candidates)
    history = []
    reward = REWARDS[reward_name]
    for episode in range(episodes):
        probabilities = _softmax(logits)
        action_index = _sample(probabilities, rng)
        env.reset()
        outcome, _, done, info = env.step(env.action_names[action_index])
        value = reward(outcome)
        _update(logits, action_index, value, probabilities, learning_rate)
        if episode < 5 or episode == episodes - 1:
            history.append({"episode": episode + 1, "action": outcome.action,
                            "reward": value, "done": done, "probabilities": probabilities,
                            "xpath": info["xpath"]})
    final = _softmax(logits)
    choice = env.action_names[max(range(len(final)), key=final.__getitem__)]
    chosen = assess(next(c for c in env.candidates if c.name == choice), env.gold)
    return {"algorithm": "reinforce", "reward": reward_name, "seed": seed,
            "episodes": episodes, "learning_rate": learning_rate,
            "final_probabilities": dict(zip(env.action_names, final)),
            "greedy_action": choice, "greedy_exact": chosen.exact,
            "greedy_f1": chosen.f1, "history": history}


def train_grpo(env: RuleSearchEnv, reward_name: str, *, seed: int = 7,
               updates: int = 120, group_size: int = 4,
               learning_rate: float = 0.25) -> dict:
    """A group-relative policy-gradient update, analogous to GRPO's core idea."""
    if reward_name not in REWARDS:
        raise ValueError(f"Unknown reward: {reward_name}")
    if updates < 1 or group_size < 2 or learning_rate <= 0:
        raise ValueError("updates, group_size and learning_rate are invalid")
    rng = random.Random(seed)
    logits = [0.0] * len(env.candidates)
    reward = REWARDS[reward_name]
    history = []
    for update in range(updates):
        probabilities = _softmax(logits)
        sampled = [_sample(probabilities, rng) for _ in range(group_size)]
        outcomes = []
        values = []
        for index in sampled:
            env.reset()
            outcome, _, _, _ = env.step(env.action_names[index])
            outcomes.append(outcome)
            values.append(reward(outcome))
        average = sum(values) / len(values)
        variance = sum((value - average) ** 2 for value in values) / len(values)
        scale = math.sqrt(variance) + 1e-8
        advantages = [(value - average) / scale for value in values]
        for index, advantage in zip(sampled, advantages):
            _update(logits, index, advantage, probabilities, learning_rate / group_size)
        if update < 3 or update == updates - 1:
            history.append({"update": update + 1, "actions": [o.action for o in outcomes],
                            "rewards": values, "advantages": advantages})
    final = _softmax(logits)
    choice = env.action_names[max(range(len(final)), key=final.__getitem__)]
    chosen = assess(next(c for c in env.candidates if c.name == choice), env.gold)
    return {"algorithm": "grpo-like", "reward": reward_name, "seed": seed,
            "updates": updates, "group_size": group_size, "learning_rate": learning_rate,
            "final_probabilities": dict(zip(env.action_names, final)),
            "greedy_action": choice, "greedy_exact": chosen.exact,
            "greedy_f1": chosen.f1, "history": history}


def run_experiment(*, seed: int = 7, episodes: int = 300) -> dict:
    env = RuleSearchEnv()
    rankings = []
    for candidate in env.candidates:
        outcome = assess(candidate, env.gold)
        rankings.append({"action": candidate.name, "proxy": proxy_reward(outcome),
                         "corrected": corrected_reward(outcome), "sparse": sparse_reward(outcome),
                         "f1": outcome.f1})
    runs = []
    for algorithm in ("reinforce", "grpo"):
        for reward_name in ("sparse", "proxy", "corrected"):
            result = (train_reinforce(env, reward_name, seed=seed, episodes=episodes)
                      if algorithm == "reinforce" else
                      train_grpo(env, reward_name, seed=seed, updates=max(20, episodes // 3)))
            runs.append(result)
    proxy_choice = next(r for r in runs if r["algorithm"] == "reinforce" and r["reward"] == "proxy")["greedy_action"]
    corrected_choice = next(r for r in runs if r["algorithm"] == "reinforce" and r["reward"] == "corrected")["greedy_action"]
    return {"protocol": "finite one-step rule search; fixed seed; no external model",
            "seed": seed, "candidates": [c.name for c in env.candidates],
            "rankings": rankings, "runs": runs,
            "reward_hacking_observed": proxy_choice == "long-noise" and corrected_choice == "exact",
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "note": "Toy evidence only; no PPO/GRPO training or industrial conclusion."}
