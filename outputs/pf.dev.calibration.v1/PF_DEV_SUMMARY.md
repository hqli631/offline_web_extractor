# P-F 阶段1 dev 校准摘要（v1.4，非 gate）

- judge 期望版本：1.4.0；n=18；reject=0.05555555555555555 severe_miss=2 false_alarm=0.0
- Anchoring circularity on dev track: 6/18 cases (overlay + re-adjudicated); v4 is the independent test.

| 标签 | n | decision_match | kappa |
| --- | --- | --- | --- |
| orig | 12 | 0.9091 | 0.8429 |
| p2 | 6 | 0.8333 | 0.6667 |

双轨：mechanical_track 为密封原始 gold 的机械披露轨，非 gate 依据。
局限：单标注者；一致率≠准确率；dev 锚定循环已披露；v4 才是独立测试。
