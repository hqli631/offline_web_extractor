# P3 dev 回归护栏摘要

- 判定：**GUARD_FAIL**
- orig dev12 match=0.75 κ=0.5443；p2 dev6 match=0.8333

| 指标 | 阈值 | 观测 | 通过 |
| --- | --- | --- | --- |
| reject_rate | lt 0.1 | 0.0 | YES |
| severe_miss_count | le 1 | 3 | NO |
| false_alarm_rate | le 0.15 | 0.0556 | YES |
