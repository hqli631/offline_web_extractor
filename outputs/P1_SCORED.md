# P1 development acceptance (descriptive cross-judge/probes)

- verdict: **REJECT**
- reject rate: 0.0833 (<0.10 required); rejected 1/12
- severe_miss: 1 (<=1 required); cases ['cal-blurb-reorder']
- accepted decision mismatches: 3 (<=1 required)
- decision match / kappa: 0.7273 / 0.5286
- dim exact / within1: 0.8182 / 0.9773; severity sign: 0.8864
- false_alarm: ['cal-appetite-missing_paragraph', 'cal-appetite-duplicate']
- freeze check: NONE

Thresholds pre-registered in docs/P1_META_EVAL_PLAN.md. Dev-only; frozen_test sealed.
Agreement is not accuracy; single annotator; judge scores are not training reward.

## Cross-judge (descriptive)
- model2: qwen-plus; both accepted: 6; judge2 rejected: 6
- agreement: {"n_cases": 6, "accepted": 6, "rejected": 0, "decision_match_rate": 0.8333, "decision_cohen_kappa": 0.6667, "n_comparable_dim_pairs": 24, "dim_exact_rate": 0.8333, "dim_within1_rate": 0.9583, "severity_sign_rate": 0.8333, "severe_miss_cases": [], "false_alarm_cases": ["cal-appetite-duplicate"], "rejected_cases": []}

## Probe position (descriptive)
- comparable cases: 6; decision flip rate: 0.1667; dim exact: 0.875

## Probe phrasing (descriptive)
- comparable cases: 4; decision flip rate: 0.0; dim exact: 1.0

## Probe stability (descriptive)
- comparable cases: 2; decision flip rate: 0.0; dim exact: 1.0
