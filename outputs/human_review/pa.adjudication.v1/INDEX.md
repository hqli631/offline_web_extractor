# P-A 裁决索引（5 例开放分歧）

事后解封裁决（非盲评）：真实案例名 + judge 证据 + 人类 gold + 程序侧核 + 受控变异。

## 背景
P3 gate FAIL 的 3 例 v1.2 false_alarm 中，2 例（C01/C02）已由 P3 裁决为 judge_correct（人类 gold 漏检）。
本 kit 覆盖**剩余开放分歧**：A01 是唯一未解释的 v1.2 误报；A02 是 Node 5 新发现的 judge–程序标题分歧；
A03–A05 是 v1.3 severe_miss 护栏 FAIL 的 3 例，暴露 **gold 代际校准冲突**（同型变异人类严重度不一致）。

## 案卷
| 代码 | 案例 | 分歧 | 裁决问题 |
| --- | --- | --- | --- |
| A01 | cal-appetite-reorder | v12_false_alarm | 块乱序（reorder）在 structure 维应记 major（judge v1.2）还是 minor（人类 gold）？严重度是否应按乱序量级区分？ |
| A02 | n5-blurb-title | judge_vs_program_title | 标题中连续双空格被折叠为单空格，应记 title minor 缺陷（judge，源保真）还是可接受归一化（程序+人类=4）？ |
| A03 | cal-appetite-noise | v13_severe_miss_anchor | 单个噪声块/相邻段落乱序在 cleanliness 维：人类 gold 记 major，v1.3 记 minor（severe_miss）。哪个符合缺陷量级？v1.2 曾与人类一致——v1.3 粒度原则是否过宽？ |
| A04 | cal-blurb-noise | v13_severe_miss_anchor | 单个噪声块/相邻段落乱序在 cleanliness 维：人类 gold 记 major，v1.3 记 minor（severe_miss）。哪个符合缺陷量级？v1.2 曾与人类一致——v1.3 粒度原则是否过宽？ |
| A05 | cal-blurb-reorder | v13_severe_miss_anchor | 单个噪声块/相邻段落乱序在 structure 维：人类 gold 记 critical，v1.3 记 minor（severe_miss）。哪个符合缺陷量级？v1.2 曾与人类一致——v1.3 粒度原则是否过宽？ |

## 填写
在 pa_findings.json 填 reviewer/review_date/discipline_ack=true，逐案 verdict + anchor_revision_suggestion + note。
verdicts：('judge_correct', 'human_correct', 'anchor_ambiguous', 'both_partially_correct')

## 纪律
不回改 P0/P2 封存 gold；不重评 frozen_test v1/v2/v3；裁决仅产生 findings；协议修订须 P-B 预注册；单标注者（IAA 缺失已声明）。

## 复现
python -m tools.build_pa_adjudication_kit --output outputs/human_review/pa.adjudication.v1（拒绝覆盖；零调用）
