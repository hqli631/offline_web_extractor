# P1 development acceptance (descriptive cross-judge/probes)

- verdict: **ACCEPT**
- reject rate: 0.0 (<0.10 required); rejected 0/12
- severe_miss: 0 (<=1 required); cases []
- accepted decision mismatches: 1 (<=1 required)
- decision match / kappa: 0.9167 / 0.8554
- dim exact / within1: 0.8333 / 1.0; severity sign: 0.875
- false_alarm: ['cal-appetite-reorder']
- freeze check: NONE

Thresholds pre-registered in docs/P1_META_EVAL_PLAN.md. Dev-only; frozen_test sealed.
Agreement is not accuracy; single annotator; judge scores are not training reward.

## Probe stability (descriptive)
- comparable cases: 2; decision flip rate: 0.0; dim exact: 1.0
