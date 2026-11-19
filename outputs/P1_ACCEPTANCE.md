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
