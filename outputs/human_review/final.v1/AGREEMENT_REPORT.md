# P0 人工校准 · 最终一致性报告

- 标注者：hqli631（单一标注者）
- 案例：23；judge 接受 16 / 拒绝 7
- 决策一致率（接受例）：0.9375；Cohen kappa：0.872
- 逐维 exact：0.8281；±1：0.9688；严重度符号：0.8281
- severe_miss：[]；false_alarm：['cal-mdn-instruction_interference']
- 盲评→裁决修改的案例：['cal-appetite-noise', 'cal-blurb-noise', 'cal-iana-noise', 'cal-github-clean', 'cal-mdn-code_indent']
- 持续分歧（校准发现）：16 例，见 calibration_findings.json

## 分 split

- development：接受 10，决策一致 1.0，kappa 1.0
- frozen_test：接受 6，决策一致 0.8333，kappa 0.0

## 局限

- 单一标注者，未测标注者间一致性（IAA）；如需更强证据，可请第二人独立复核至少6例。
- 一致率不是准确率：人类标签也只是参考之一，judge 与人类分歧属于校准发现。
- frozen_test 仅作描述性报告；不得据此调 judge/协议后重报为干净验收。
- source_only 案例为 provisional 判断，无 gold 佐证的维度不可视为已验证。
- Judge 分数仍不作为训练奖励。
