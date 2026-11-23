# P-A 裁决 findings 摘要（封存）

- 复审者：hqli631（2026-11-23）｜ 案卷：5 ｜ discipline_ack：true
- pa_findings.json sha256：63202e6bee148ef8f63a3f079b2a52e3918a5e06e8344d0b619f53f523292d3d
- verdict 分布：judge_correct×2（A01/A02）· human_correct×3（A03/A04/A05）
- 纪律：不回改 P0/P2 封存 gold；裁决仅产生 findings；修订须 P-B 预注册。

| 案卷 | 案例 | verdict | 锚点建议（verbatim） |
| --- | --- | --- | --- |
| A01 | cal-appetite-reorder | judge_correct | 出现 reorder 即记为重要严重事故（structure major/fail），避免正文歧义 |
| A02 | n5-blurb-title | judge_correct | 双空格折叠应记 minor 缺陷（源保真） |
| A03 | cal-appetite-noise | human_correct | 噪声容忍度极低，出现任何噪声即判严重事故 |
| A04 | cal-blurb-noise | human_correct | 同 A03 |
| A05 | cal-blurb-reorder | human_correct | 和 A01 一样，出现 reorder 即记为重要严重事故 |

## 推导出的锚点规则（供 P-B 预注册修订）

- **R1 reorder（A01/A05）**：任何块序偏离 → structure severity ∈ {major, critical}（severe），decision **fail**。零容忍，绝不 minor。（A01=major，A05=critical，均属 severe/fail；统一原则"reorder 非 minor"。）
- **R2 noise（A03/A04）**：任何噪声污染 → cleanliness severity **major**（severe），decision **fail**。零容忍，否决 v1.3"单个小噪声→minor"粒度原则。
- **R3 title 空白保真（A02）**：源空白折叠（如双空格→单空格）→ title **minor** 缺陷（源保真）；程序侧 whitespace 归一化不作权威。

## 重大一致性结论（双轨解读）

1. **v1.2 的 3 例"误报"全部 vindicated**：A01 judge_correct + 已裁决 C01 judge_correct + C02 judge_correct → 对**裁决后 gold**，v1.2 真实 false_alarm = **0/18**。封存 gold 机械指标 3/18 FAIL 仍成立（预注册纪律，不可回改），但 FAIL 主因是 gold 错误而非 judge 错误。
2. **v1.3 降级修订被证伪**：A03/A04/A05 human_correct → v1.3 把真实 severe 降为 minor 错误 → P3 回滚正确；P-B 修订**不得**重新引入噪声/reorder 降级。
3. **v1.2 行为已大体符合裁决锚点**：v1.2 对 noise/reorder 记 major（满足 R1/R2），Node 5 对标题双空格记 minor（满足 R3）。故 P-B 修订重点 = **显式固化锚点 + 长页证据工程 + gate 方法论预注册**，而非放宽严重度。

## 待 P-B 预注册决策

- gate 的 gold 基准：封存 gold（机械 FAIL）vs 裁决后 gold（双轨）须预注册明确；不可事后改基准宣称 PASS。
- 长页分块证据/截断处理（Node 5 mdn/github 拒绝）工程方案。
- 标题空白保真锚点文本（R3）与 reorder/noise 零容忍锚点文本（R1/R2）固化。
