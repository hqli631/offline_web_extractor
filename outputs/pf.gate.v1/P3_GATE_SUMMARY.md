# P3 gate 评分摘要

- 判定：**PASS**（10/10 硬检查通过）
- bootstrap B=10000 seed=20261119；输入哈希见 p3.gate.json。

| 范围 | 指标 | 阈值 | 观测 | 通过 |
| --- | --- | --- | --- | --- |
| dev_pooled | reject_rate | lt 0.1 | 0.0 | YES |
| dev_pooled | severe_miss_count | le 1 | 0 | YES |
| dev_pooled | false_alarm_rate | le 0.15 | 0.0 | YES |
| dev_subset:orig | decision_match_rate | ge 0.85 | 1.0 | YES |
| dev_subset:orig | cohen_kappa | ge 0.75 | 1.0 | YES |
| v3 | reject_rate | lt 0.1 | 0.0 | YES |
| v3 | severe_miss_count | le 1 | 0 | YES |
| v3 | false_alarm_rate | le 0.15 | 0.0 | YES |
| v3 | decision_match_rate | ge 0.8 | 1.0 | YES |
| v3 | pass_recall | ge 0.8 | 1.0 | YES |

局限：单一标注者；一致率≠准确率；v3 一次性；FAIL 不重测。
