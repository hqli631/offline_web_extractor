# 节点 5 · 质量修复闭环实验计划（已批准 · 2026-11-22）

> 预注册定义（docs/HUMAN_CALIBRATION_PLAN.md）：**Critic 反馈 → 限定次数修复 → 再评估，带无修复对照，test/gold 不回传。**
> 状态：**已批准**（2026-11-22 hqli631 原话：`批准节点5计划与预算`）。实施按本计划执行，指标/判据/预算调用前冻结。P3 已收尾（gate FAIL）；本实验**不是 reward 化**，judge 分数仍禁止作训练奖励。
> 依据：P3 发现（judge v1.2 dev severe_miss=0、false_alarm 0.1667 其中 2/3 为已裁决 gold 漏检）→ Critic 可用但须实证检验修复收益，无修复对照为必备臂。

## 1. 目标与假设

- 目标：实证回答"Rubrics Critic 反馈驱动的限定修复是否改善提取质量"，交付可复现报告（无论正负结果）。
- 假设（待检验，非预设）：对 judge 判定非 pass 的真实提取输出，≤1 次 Critic 引导修复可改善决策/分数，且回归率可控。
- 明确不做：SFT/RL 奖励接线、协议修改、封存集触碰、无限修复循环。

## 2. 纪律边界（硬约束）

1. **仅 dev 模板族**（appetite/blurb/iana/mdn/github/w3clink 6 个原 dev 模板源页）；frozen_test v1 永久封存、v2 已消耗、v3 封存未消耗——**均不进入本实验**。
2. **test/gold 不回传**：Critic judge 用 **source_only 模式**（无 gold 输入）；修复器输入仅含候选 + 源 + Critic 反馈文本/证据引用（s:N），不含任何 gold 块、expected.json、split 标签。泄漏审计工具断言修复器输入哈希与 gold 无交集。
3. judge 协议冻结 v1.2.0（sha edd841ef…，freeze v8）；实验期间**不改协议/锚点/阈值**；实验配置先冻结（node5.freeze.v1）后调用。
4. 修复引擎 = 既有 rule_agent 状态机（XPath 配置输出，无可执行 Python；max_attempts=2 即**修复 ≤1 次**；轮次/时限/token 上限显式失败）。
5. 一致率≠准确率：judge 判"改善"≠真实质量改善；用程序化参考侧核（post-hoc，不回传）+ 可选人工抽检佐证。
6. 模型调用先批预算；输出拒绝覆盖；全审计轨迹（prompts/哈希/轮次/反馈）。

## 3. 实验设计

- **案例**：6 个 dev 模板源页 × 真实 extractor 输出（非合成变异）= 6 案。Critic 判 pass 的案例不修复（记 no-op）；非 pass 进入修复臂。
- **双臂**：
  - 对照臂（无修复）：原始候选的 Critic 评估（即首次 judge 调用）。
  - 修复臂：Critic 反馈 → rule_agent ≤1 次修复 → 修复后候选**同协议再评估**。
- **配对比较**：同案原始 vs 修复后 judge 决策/维度分数/严重度；bootstrap 95% CI（B=10000，seed=20261119）。
- **程序化侧核**（post-hoc）：修复前后候选 vs dev expected.json 的块级 precision/recall/顺序变化；仅报告，不回传修复器。
- **预注册指标**（调用前冻结）：
  | 指标 | 定义 |
  | --- | --- |
  | 修复触发率 | 非 pass 案 / 总案 |
  | 改善率 | 修复案中决策/分数改善比例（改善定义：决策向 pass 方向移动或维度总分上升且无新 severe） |
  | 回归率 | 修复案中出现新 severe 缺陷或决策恶化的比例 |
  | 无效修复率 | 修复后 judge 评估无变化的比例 |
  |  unnecessary-repair | 原始 pass 案被尝试修复的次数（设计须=0） |
- **成功判据（提案，待批）**：改善率 ≥1/3 且回归率 ≤10% 且泄漏审计通过 → "修复收益信号存在"（描述性结论，非奖励门槛）；否则如实报告负/无结果。n=6 极小，CI 宽，结论强度如实降级。

## 4. 工程步骤（零调用，批准后实施）

1. Critic 反馈适配器：judge assessment（dimensions/severity/reason/evidence s:N）→ rule_agent 反馈契约（结构化文本 + 引用）；只读 source_only 评估。
2. 闭环 runner：extractor → Critic（source_only）→ 条件修复（≤1）→ 再评估；全轨迹落盘；拒绝覆盖。
3. 泄漏审计工具：修复器输入不含 gold/expected/test 标识（哈希与字段断言）。
4. 配对评分器 + bootstrap CI + 程序化侧核。
5. 单元测试（预计 ~25–30 新增）+ 全量回归。
6. node5.freeze.v1（实验配置/案例/协议 sha/指标/判据/预算）→ 冒烟 1 次 → 正式运行 → docs/NODE5_REPAIR_REPORT.md。

## 5. 预算估算（已批准；调用数口径细化见 §9）

| 项 | 调用 | 估算 tokens |
| --- | --- | --- |
| Critic source_only × 6（无 gold，prompt 较小） | 6 | ~60–80k |
| 修复后再评估 × ≤6 | ≤6 | ~60–80k |
| 冒烟（计入） | (1) | (计入) |
| **上限（+裕量）** | **~14** | **~220k** |

修复 ≤1 次为硬上限；本轮不允许第二次修复尝试。超预算即停并如实报告。

## 6. 交付物

适配器/runner/泄漏审计/配对评分器 + 测试；node5.freeze.v1；实验轨迹与哈希；docs/NODE5_REPAIR_REPORT.md（命令+哈希+测试日志+双臂统计+如实局限）；GitHub 同步后停止。

## 7. 如实局限（预先声明）

- judge 未完全校准：Critic 误报可能触发不必要修复、漏检可能放过缺陷——对照臂与回归率正是为此设。
- n=6、同模板族：不构成泛化证据；"修复收益信号"仅限本受控范围。
- judge 判改善≠真实改善；程序化侧核 + 可选人工抽检（后续单独安排）缓解。
- 单一标注者背景局限延续；本实验不产生新 human gold。
- 负结果同样交付：若修复无益，如实报告并停止，不追加调参刷分。

## 8. 批准记录

- 计划批准：**2026-11-22 hqli631**（原话：`批准节点5计划与预算`）
- 预算批准（~14 次 / ~220k 上限）：**2026-11-22 hqli631**（同上原话）
- 冻结时间：**2026-11-22T15:55:10+00:00**（node5.freeze.v1，sha256 `f38ff536427ca3647e93368dd042c71adba263dbd8ebd53a81416f8d5ae3cd97`；judge v1.2.0 sha `edd841ef…` 与 freeze v4/v8 一致；6 dev 案例；token 硬顶 220000；细化最坏 25 次调用）
- 调用数上限确认：**2026-11-23 hqli631 选项 A**（原话：`A`）——220k token 硬顶不变，允许最多 25 次调用；最坏情形守卫自动停在顶内、如实交付部分结果
- 执行记录（2026-11-23）：冒烟 1 案（appetite，no_repair_needed，12,478 tokens）→ 正式 6 案（--token-cap 207522）：3 no_repair_needed / 1 repaired（blurb，no_effect）/ 2 critic_rejected（mdn/github，证据校验）；9 次调用 / 124,399 tokens ≤ 220k；判据 **NO_BENEFIT_SIGNAL**（改善率 0/1 < 1/3）；交付 docs/NODE5_REPAIR_REPORT.md 后停止，不追加调参。

## 9. 工程细化记录（2026-11-22 · 冻结前 · 零调用）

以下为计划批准后、**任何模型调用与冻结之前**的工程细化，不构成事后调参：

1. **触发条件语义**：冻结 judge 协议规定 `source_only` 模式（gold=None）下 `decision` 只能为 `fail` 或 `uncertain`，**永不为 `pass`**（协议语义，非缺陷）。故"非 pass 即修复"细化为"**Critic 观察到缺陷才修复**"：`decision==fail` 或缺陷列表非空（缺陷 = severity∈{minor,major,critical} 或已评分维度 score<4）。零缺陷 `uncertain` 记 `no_repair_needed`（no-op 对照）。这使"unnecessary-repair 必须=0"保持实质意义，避免对干净候选做无谓修复。触发规则原文冻结于 node5.freeze.v1（`trigger_rule`）。
2. **分类桶**：improved / regressed / no_effect / **other_change**（如分数下降但无新 severe 且决策不变——如实报告，不计入三个比率）。judge assessment 无总分字段，总分 = 5 维非空分数之和；分数改善路径额外要求前后已评分维度集合相同（保守可比性门槛）；回归判定优先。全部冻结于 freeze（`classification`）。
3. **预算口径细化**：原 ~14 次调用**仅计 judge 调用**，未含修复生成调用（rule_agent max_attempts=2 × ≤6 案 = ≤12 次）。细化最坏情形 = 6 Critic + ≤12 生成 + ≤6 再评估 + 1 冒烟 = **25 次调用**；最坏 tokens 可能超 220k 上限 → 预算守卫（judge 预留 16k / rule 预留 8k）在**超限前停止**并跳过后续案例，如实报告部分结果。**220k token 上限仍为硬顶**；调用数上限待用户确认（§8）。runner 支持 `--token-cap`（≤ freeze 上限）用于冒烟+正式的累计预算；模型由 freeze 锁定 qwen3.8-27b，漂移即拒绝。
4. **执行器契约修正**：`execute_rule` 的 `execution['result']` 直接为 `extract_html.to_dict()`（无额外嵌套）；runner/scorer/tests 已修正，真实执行器冒烟测试覆盖。
5. **评分器失败关闭**：候选哈希不符、泄漏审计失败、unnecessary repair、协议漂移 → 判据 NO_BENEFIT_SIGNAL 或拒绝运行。
