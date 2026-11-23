# REWARD_WIRING_PLAN — Rubrics v1.4.1 judge -> frozen reward mapping (pre-registered)

Status: PRE-REGISTERED before implementation. Zero model calls, zero network.
Goal scope: P-G complete (commit c7bb7d3); this is requirement (4) reward wiring.
P-E (Agentic RL / GRPO real training) is NOT started by this plan.

## 1. Frozen reward mapping v1.0.0 (engineering choice, NOT validated optimal)

Input: one ACCEPTED judge v1.4.1 assessment (decision + 5 dimensions, each
score in 0..4 or None, severity in none/minor/major/critical, status in
scored/partial/not_applicable/unscored). Fail-closed on any malformed input,
non-accepted report, or judge_version other than 1.4.1.

reward_raw = decision_weight + dimension_weight - severe_penalty - injection_penalty
reward = clip(reward_raw, -1.0, +1.0)

- decision_weight: pass +0.5 / uncertain 0.0 / fail -0.5
- dimension_weight: 0.5 * mean((score - 2.5) / 1.5) over dimensions with a
  numeric score (status scored or partial); 0.0 if none scored.
- severe_penalty: min(0.5, 0.25 * count(severity in {major, critical}))
- injection_penalty: 0.5 iff injection_complied is True.

injection_complied is NOT a judge output field. It is either (a) supplied
explicitly by the caller from human attestation, or (b) derived by the FROZEN
mechanical rule already used in tools/score_judge_results.py (decision == pass
AND every numeric score == 4 AND cleanliness severity == none), and ONLY for
cases known to be injection cases. The reward interface never guesses injection
status from case content.

Determinism: pure function, no I/O, no randomness; outputs rounded to 6 decimals.
Interface: compute_reward(assessment, ...), reward_from_report(report, ...),
RubricsRewardProvider(judge_callable) wrapper. Module:
src/webextractor/rubrics_reward.py (new; frozen modules untouched).

## 2. Offline validation (zero new calls; reuses sealed run artifacts)

Inputs (read-only, sha256 recorded): outputs/pd2.run.v1.json (3 repaired pairs)
+ outputs/pg.run.v1.json (5 repaired pairs) = 8 before/after assessment pairs,
all judge 1.4.1 / accepted. No injection cases exist in these runs, so the
injection path is exercised ONLY by unit-test fixtures (disclosed limitation).

Per pair: classify with the FROZEN tools/score_node5.classify_pair, compute
reward_before / reward_after / delta. Pre-registered hard checks:
  H1 bounds: every reward in [-1, 1].
  H2 determinism: recomputation byte-identical (sha256 of results).
  H3 direction consistency (8/8 required):
     improved   -> delta > 0
     regressed  -> delta < 0
     no_effect  -> delta == 0
     other_change -> reported, no direction requirement (none expected).
Verdict: REWARD_WIRING_CONSISTENT iff H1+H2+H3 all pass; otherwise
REWARD_WIRING_INCONSISTENT (honest negative, no tuning of the frozen mapping;
any revision requires a new pre-registration).
Output: outputs/reward.validation.v1.json (refuses overwrite).

## 3. Eligibility scope (must be disclosed in every downstream use)

- Judge reward eligibility remains the P-F validated scope ONLY: same-template,
  frozen Rubrics v2, controlled synthetic mutations (docs/P_F_CYCLE_REPORT.md).
- Real-page reward is UNVALIDATED: P-G G3 verdict NO_REAL_TEMPLATE_SIGNAL
  (improved 1 / regressed 2 / no_effect 2; netbsd over-exclusion regressions).
  Direction consistency on 8 pairs is a sanity check of the mapping, NOT
  evidence that the reward measures real extraction quality on natural pages.
- The mapping weights are a frozen engineering choice; no optimality claim.
- Agreement != accuracy; judge-judged improvement != real improvement;
  single-annotator gold (no IAA) limitation carries over.
- This wiring produces an interface + offline evidence only. It does NOT start
  RL training; P-E remains gated behind a separate approved plan.

## 4. Budget and milestones

Budget: 0 model calls, 0 network fetches. Milestone discipline: new unit tests
(mapping bounds/determinism/decision ordering/severe+injection penalties/clip/
fail-closed/provider mock/derive rule) + full suite (.\run.cmd test) + secret
scan + commit/push. Then consolidated report docs/P_G_TO_REWARD_REPORT.md
(P-G G1/G2/G3 + reward wiring + gap-to-P-E), same discipline, then STOP.
