# 节点 5 · 质量修复闭环实验报告（2026-11-23）

> **判据结论：NO_BENEFIT_SIGNAL**（预注册改善率 ≥1/3 未满足：0/1）。如实负结果；按计划交付后停止，不追加调参刷分、不重测。judge 分数仍禁止作训练奖励（P3 gate FAIL，reward-INELIGIBLE）。

## 1. 摘要

- **问题**：Rubrics Critic 反馈驱动的限定修复（≤1 次）是否改善提取质量？
- **设计**：6 个 dev 模板的真实 extractor 输出；对照臂 = 基线 Critic（source_only，无 gold）评估；修复臂 = Critic 反馈 → rule_agent ≤1 次修复（XPath 配置输出，可信执行器）→ 同冻结协议再评估；配对分类 + bootstrap CI + 程序化侧核（post-hoc，不回传）。
- **结果**：3 案零缺陷不修复；1 案修复（blurb）→ **no_effect**；2 案 Critic 协议证据校验拒绝（mdn/github）。paired_n=1，改善率 0.0，回归率 0.0，无效率 1.0。
- **预算**：9 次调用 / **124,399 tokens**（硬顶 220,000 / ≤25 次，选项 A），无跳过。
- **结论**：本受控范围内未观察到修复收益信号。主因是 dev 基线质量已高、可修复空间极小（4/5 有参考案例 recall=1.0），**不等于"修复机制普遍无效"**——修复能力本身未被充分测试。

## 2. 预注册与批准

- 计划：docs/NODE5_REPAIR_LOOP_PLAN.md。批准：2026-11-22 hqli631 原话 "批准节点5计划与预算"；调用数上限：2026-11-23 hqli631 选项 A（原话 "A"，220k token 硬顶不变、≤25 次调用）。工程细化（触发语义/分类桶/预算口径/执行器契约）于**冻结前**记录于计划 §9，非事后调参。
- 冻结：outputs/node5.freeze.v1.json，sha256 **f38ff536427ca3647e93368dd042c71adba263dbd8ebd53a81416f8d5ae3cd97**（调用前创建，commit 0ca35b5；触发规则/分类/判据原文冻结于 trigger_rule / classification / success_criteria）。
- 协议冻结：judge **v1.2.0** sha edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891（与 freeze v4/v8 一致）；rubrics v2.0.0 sha 4fa60e024758e67d8c831b7a34e267bf2ce9a143dd6ae70cdbc94da036560364；rule_agent sha e60ec3094f442f9a20de89f46a93e2d163ae60a84361001c77bd475d9bf64a20；模型锁定 qwen3.8-27b。
- 关键语义：source_only 模式 decision 永不为 pass（协议规定）；触发条件 = decision==fail 或缺陷非空（severity∈{minor,major,critical} 或已评分 score<4）；零缺陷 uncertain 记 no_repair_needed。

## 3. 复现命令

环境：Windows PowerShell；QWEN_API_KEY 置于环境变量/env.local（不入库）；PYTHONIOENCODING=utf-8；Python 经 .\run.cmd 或运行时路径。输出文件拒绝覆盖（exit 3），复现须用新文件名；runner/scorer 自动执行 freeze 校验（协议/源漂移即拒绝）。

~~~
.\run.cmd test                                            # 526 tests OK -> outputs/node5.suite.v2.log
python -m tools.node5_loop --freeze                       # 已冻结；重跑拒绝覆盖 (exit 3)
python -m tools.node5_loop --run --max-cases 1 --output outputs/node5.smoke.v1.json
python -m tools.node5_loop --run --output outputs/node5.run.v1.json --token-cap 207522
python -m tools.score_node5 --run outputs/node5.run.v1.json --output outputs/node5.score.v1.json
~~~

累计预算：冒烟用 12,478 → 正式 --token-cap = 220,000 − 12,478 = 207,522。

## 4. 产物哈希（sha256）

| 产物 | sha256 |
| --- | --- |
| outputs/node5.freeze.v1.json | f38ff536427ca3647e93368dd042c71adba263dbd8ebd53a81416f8d5ae3cd97 |
| outputs/node5.smoke.v1.json | 70428d658ab0245073c34e6fd435b824a57ff6f8a155e910f06c745979e00bce |
| outputs/node5.run.v1.json | 58d4f76e798c7008ca3297b19e809a3133c87e2f812fbe63e6fd6508794e52a8 |
| outputs/node5.score.v1.json | 7b48728d293ecde36884011f5417d4575f551edb0300974f9ed465f8e032bb89 |
| outputs/node5.suite.v1.log（520 OK） | 77c398d74c398f971ff33887d1a6b5b3902a30337d6ab2c053ec2a972495a51e |
| outputs/node5.suite.v2.log（526 OK） | 97b422be4b0a51aece0cb8ff9ba164306637034ed14fb06a7cc1eac412e3afd6 |

案例源页哈希（前 16 位；全值见 freeze）：appetite faa9db0798aeec25 / blurb 7499dcd325be2bf0 / iana 3b8669627aee51b9 / mdn a4d929c09eb50f44 / github c0cb2ed0cf8a6c40 / w3clink 455f237d8b95ab05。

## 5. 双臂结果（正式运行）

| 案例 | 状态 | Critic 决策/缺陷 | 修复 | 再评估 | 分类 | 调用/tokens |
| --- | --- | --- | --- | --- | --- | --- |
| n5-appetite | no_repair_needed | uncertain；0 缺陷 | — | — | — | 1 / 12,477 |
| n5-blurb | repaired | uncertain；title 3/minor（源截断→partial） | 1 次生成尝试，审计通过 | uncertain；title 3/minor | **no_effect**（15→15，Δ0） | 3 / 37,727 |
| n5-iana | no_repair_needed | uncertain；0 缺陷 | — | — | — | 1 / 6,443 |
| n5-mdn | critic_rejected | 校验拒绝："Evidence quote is not supported"（finish=stop） | — | — | 排除 | 1 / 25,527 |
| n5-github | critic_rejected | 校验拒绝："Scoring needs source/reference evidence"（finish=stop） | — | — | 排除 | 1 / 21,914 |
| n5-w3clink | no_repair_needed | uncertain；0 缺陷 | — | — | — | 1 / 7,833 |

配对细节（blurb）：decision uncertain→uncertain；总分 15→15（title 3 + 3×4，format 不适用）；已评分维度集合相同（可比）；无新 severe；Δ=0。bootstrap CI：point 0.0，ci95 [0.0, 0.0]，n=1，B=10000，seed=20261119（**退化区间，无推断力**）。

程序化侧核（post-hoc；确定性参考诊断，未校准；仅报告，不回传）：

| 案例 | before（decision / recall / precision / title） | after |
| --- | --- | --- |
| n5-appetite | pass / 1.0 / 1.0 / 4 | —（未修复） |
| n5-blurb | pass / 1.0 / 1.0 / 4 | pass / 1.0 / 1.0 / 4（完全相同） |
| n5-mdn | uncertain / 1.0 / 1.0 / 4 | —（Critic 拒绝，仅基线） |
| n5-github | uncertain / 1.0 / 0.989 / 4 | —（Critic 拒绝，仅基线） |

**关键观察**：blurb 被 judge 标记的 title 缺陷（3/minor）**不获程序侧佐证**（标题精确匹配=4）；修复前后程序指标完全相同 → 该修复产出等价候选（no-op）。judge 的 title 判断可能是误报，或涉及程序未覆盖的语义细微差别——无 human gold 可裁决，本实验不进一步追究（不重测、不调参）。

## 6. 预注册判据核对

| 检查 | 阈值 | 实际 | 通过 |
| --- | --- | --- | --- |
| improvement_rate_ge | ≥1/3 | 0.0（0/1） | ✗ |
| regression_rate_le | ≤0.10 | 0.0（0/1） | ✓ |
| leakage_audit_all_passed | 全部通过 | 1/1（评分时独立复审） | ✓ |
| unnecessary_repair_zero | =0 | 0 | ✓ |
| candidate_integrity | 无哈希不符 | 无 | ✓ |

→ **NO_BENEFIT_SIGNAL**（描述性信号，非奖励门槛；n 极小，结论强度如实降级）。

## 7. 预算 accounting（选项 A：220k 硬顶 / ≤25 次）

| 阶段 | 调用 | tokens |
| --- | --- | --- |
| 冒烟（appetite） | 1 | 12,478 |
| 正式（6 critic + 1 生成 + 1 再评估） | 8 | 111,921 |
| **合计** | **9** | **124,399** |

无跳过案例；守卫未触发。其中 2 次拒绝调用消耗 47,441 tokens 而未产出评估（如实成本）。远低于硬顶与调用上限。

## 8. 纪律与审计核验

- **封存集未碰**：仅 6 个 dev 样本源页（CASES 白名单 + freeze 源哈希）；frozen_test v1 永久封存 / v2 已消耗 / v3 封存未消耗，均未进入本实验。
- **协议未改**：judge sha 运行前后一致（runner check_freeze + scorer 双重校验）；锚点/阈值未动。
- **test/gold 不回传**：Critic 强制 source_only（gold=None）；修复 prompt 白名单 + 禁词递归审计 1/1 通过；基线预览来自 extract_html 而非 expected.json；侧核 post-hoc 仅报告。
- **修复 ≤1**：rule_agent max_attempts=2；blurb 实际 1 次尝试即 runtime_accepted。
- **不追加调参刷分**：冻结后单次正式运行；2 次拒绝未重跑；负结果如实交付。
- **全轨迹落盘**：prompts/哈希/usage/attempts/审计日志均在 run json；拒绝覆盖。
- **测试**：新增 47 项节点 5 测试（单元/编排/真实执行器冒烟/CLI/全链路集成），全量 526 tests OK（两轮日志见 §4）。

## 9. 如实局限

1. n=6、paired n=1：无统计推断力；CI [0,0] 为退化区间。
2. dev 基线质量已高（4/5 有参考案例 recall=1.0，precision≥0.989）：可修复空间极小。**NO_BENEFIT_SIGNAL ≠ 修复机制普遍无效**；修复能力检验需要退化候选（超出本预注册范围，未做）。
3. 2/6 Critic 拒绝（大页/截断下严格证据校验）：对照臂缺失，且消耗 47k tokens 无产出——judge 长页可用性问题（与 P1.5/P3 观察一致）。
4. blurb 源截断（>20,000 字符）→ partial 评估；judge title 3/minor 与程序侧分歧无 human gold 裁决；单一标注者背景局限延续。
5. judge 判改善 ≠ 真实改善；一致率 ≠ 准确率；程序侧核亦为未校准确定性诊断（来源归属/链接/Markdown 渲染未评估）。
6. 同 dev 模板族：不构成泛化证据。
7. judge 分数仍 reward-INELIGIBLE（P3 gate FAIL）；本实验不是 reward 接线，不产生训练奖励。

## 10. 结论与停止

预注册受控范围内**未观察到 Critic 引导修复的收益信号**（改善率 0/1，唯一修复为 no-op 等价候选）。按计划交付后**停止**：不追加调参刷分、不重测、不扩大范围。

可选后续方向（**仅建议，未执行**，需单独批准）：
- 退化候选上的修复能力检验（受控注入噪声/删块，另立预注册与预算）；
- judge 长页证据校验可用性改进（走协议修订流程，非本实验范围）；
- blurb title 分歧的人工裁决（如需 human gold，另行安排）。

GitHub 同步：github.com/hqli631/offline_web_extractor main（本报告与全部产物入库；提交哈希见 git log）。
