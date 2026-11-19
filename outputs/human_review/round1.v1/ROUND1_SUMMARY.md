# P0 第一轮（盲评）结果摘要

- 案例：23；judge 接受 16 / 拒绝 7
- 决策一致率（接受例）：0.75；Cohen kappa：0.5077
- 逐维 exact：0.75；±1：0.9688；严重度符号：0.8125（可比维度对 64）
- severe_miss（人类严重而 judge 不严重）：['cal-mdn-code_indent', 'cal-github-clean']
- false_alarm：['cal-appetite-noise', 'cal-mdn-instruction_interference']
- 需裁决案卷：17 份（adjudicate/ 目录）

## 下一步
1. 阅读 adjudicate/ 下案卷，在 human_labels.final.json 裁决并全部 confirmed=true。
2. 运行：python -m tools.ingest_human_labels --stage final --labels outputs\human_review\round1.v1\human_labels.final.json --round1 outputs\human_review\round1.v1 --output outputs/human_review/final.v1

## 局限

- 单一标注者，未测标注者间一致性（IAA）；如需更强证据，可请第二人独立复核至少6例。
- 一致率不是准确率：人类标签也只是参考之一，judge 与人类分歧属于校准发现。
- frozen_test 仅作描述性报告；不得据此调 judge/协议后重报为干净验收。
- source_only 案例为 provisional 判断，无 gold 佐证的维度不可视为已验证。
- Judge 分数仍不作为训练奖励。
