# P2 bootstrap statistics (development only)

B=10000 seed=20261119; case-level resampling; agreement is not accuracy; dev is not generalization.

## v1.0 (n_dev=12)

| metric | point | 95% CI |
| --- | --- | --- |
| decision_match_rate | 1.0 | [1.0, 1.0] |
| decision_cohen_kappa | 1.0 | [1.0, 1.0] |
| dim_exact_rate | 0.875 | [0.7708, 0.9722] |
| severity_sign_rate | 0.9 | [0.825, 0.975] |
| severe_miss_rate | 0.0 | [0.0, 0.0] |
| false_alarm_rate | 0.0 | [0.0, 0.0] |
| reject_rate | 0.1667 | [0.0, 0.4167] |

## v1.1 (n_dev=12)

| metric | point | 95% CI |
| --- | --- | --- |
| decision_match_rate | 0.7273 | [0.4545, 1.0] |
| decision_cohen_kappa | 0.5286 | [-0.0633, 1.0] |
| dim_exact_rate | 0.8182 | [0.7, 0.925] |
| severity_sign_rate | 0.8864 | [0.8125, 0.9583] |
| severe_miss_rate | 0.0909 | [0.0, 0.2727] |
| false_alarm_rate | 0.1818 | [0.0, 0.4444] |
| reject_rate | 0.0833 | [0.0, 0.25] |

## v1.2 (n_dev=12)

| metric | point | 95% CI |
| --- | --- | --- |
| decision_match_rate | 0.9167 | [0.75, 1.0] |
| decision_cohen_kappa | 0.8554 | [0.5, 1.0] |
| dim_exact_rate | 0.8333 | [0.7708, 0.8958] |
| severity_sign_rate | 0.875 | [0.8125, 0.9375] |
| severe_miss_rate | 0.0 | [0.0, 0.0] |
| false_alarm_rate | 0.0833 | [0.0, 0.25] |
| reject_rate | 0.0 | [0.0, 0.0] |

## paired v1.0_vs_v1.1
- common accepted: 10; McNemar exact p=0.5; match diff (A-B)=0.2 CI [0.0, 0.5]

## paired v1.1_vs_v1.2
- common accepted: 11; McNemar exact p=0.625; match diff (A-B)=-0.1818 CI [-0.5455, 0.1818]

