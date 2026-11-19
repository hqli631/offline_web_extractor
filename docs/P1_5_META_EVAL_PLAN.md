# P1.5 Judge 一致率恢复 · 预注册方案（调用前冻结）

日期：2026-11-19（Asia/Shanghai）。状态：**预注册 drafted，模型调用尚未发生，等待用户批准预算**。
上游：P1 交付（docs/P1_DELIVERY_REPORT.md）——目标硬指标达标（dev 拒绝 8.3%、severe_miss 1），但预注册一致率护栏破（接受例决策分歧 3）。用户选择路径 (c) P1.5 迭代。本方案在任何 P1.5 调用前固定。

## 0. 诚实边界（继承）

silver ≠ human gold；一致率 ≠ 准确率；**dev 是调参集（允许迭代），dev ≠ 泛化**；frozen_test 永久封存、P1.5 不重跑不调参（泛化检验留 P2 新预注册测试集）；单一标注者无 IAA；judge 分数在 P3 门槛前不作训练奖励。**改进必须一般性（适用于所有案例的 prompt/协议原则），严禁逐例拟合人类标签**（不得针对特定案例的 human gold 定制 prompt 分支）。

## 1. 根因诊断（零调用，outputs/p1_drift_diagnostic.v1.json）

对比 v1.0（node4 缓存）与 v1.1 在 3 个 dev 分歧案例的逐维评分，发现**一般性菜单锚定效应**：
- appetite-missing_paragraph：completeness 3/minor→2/major、structure 4/none→3/minor（轻缺陷被抬高 → false_alarm，decision uncertain→fail）。
- appetite-duplicate：cleanliness 3/minor→2/major、structure 4/none→3/minor（同上；v1.0 此例被拒，v1.1 接受但过度严重）。
- blurb-reorder：structure 人类 1/critical、v1.0 2/major、v1.1 3/minor（重缺陷被压低 → severe_miss，decision fail→uncertain）。

机制：v1.1 把证据菜单（含 quote 前缀）与评分任务并列呈现，模型把"被建议的证据"误读为缺陷严重度线索，将严重度拉向中间档（2/major、3/minor）。这是菜单 prominence 的一般性副作用，非逐例噪声。

## 2. 假设（预注册）

- **H1（主）**：将证据菜单与评分任务**解耦**——菜单降级为评分之后的"引文附录"，并显式声明"菜单仅为引文便利，绝不作为评分/严重度依据；严重度严格依锚点按实际缺陷幅度判定"——可消除菜单锚定，恢复 dev 决策一致率，同时保留菜单对拒绝率的修复。
- **H2（描述性）**：解耦后 dev 拒绝率仍 <10%（菜单仍在，引文合规修复保留）。
- **H3（描述性）**：temp=0 稳定性保持。

## 3. 设计规格（judge v1.2.0，仅改 src/webextractor/rubrics_judge.py）

1. **菜单解耦**：evidence_menus 保留（维持拒绝率修复），但在 prompt 中明确定位为"citation appendix"，并新增/强化约束：
   - "Score and severity MUST be determined solely from the actual defect magnitude observed by comparing candidate against source/gold, strictly per the severity anchors. evidence_menus is a citation convenience ONLY; the presence, absence, or content of suggested evidence MUST NOT raise or lower any score or severity."
   - 严重度锚点强化（一般性）：critical=空/根本错误或严重顺序丢失；major=明确中度损失/污染；minor=小局部缺陷；none=无实质缺陷。
2. 其余（空白折叠匹配、schema、s:/g: 引用规则、探针参数）不变。JUDGE_VERSION 1.1.0→**1.2.0**。
3. 协议文档 docs/RUBRICS_V2_PROTOCOL.md 评分语义不变（锚点/决策规则未改，仅 judge 层 prompt 措辞）；freeze 走 v4 amendment（代码仅 rubrics_judge.py；silver 标签 prompt_chars 诊断刷新，评分内容证明不变，同 R1 机制）。
4. **一般性保证**：改动是全局 prompt 原则，不含任何案例名/盲码/人类标签分支；测试断言 prompt 不含案例特异性内容。

## 4. 验收阈值（预注册，dev-only，对照 P0 最终人类标签）

同时满足（恢复 P1 护栏）：
1. 接受例决策分歧 ≤1；
2. 拒绝率 <10%（≤1/12）；
3. severe_miss ≤1。
描述性：决策一致率/κ、逐维 exact/±1、严重度符号、false_alarm、稳定性。

**判定**：三条全过 → v1.2.0 接受为 P1.5 基线，P1 护栏恢复。任一不过 → 触发回退：
- **F1（仅当拒绝率 ≥10%）**：菜单解耦可能削弱引文合规 → 预注册两阶段"先评分后补证据"（v1.3.0，评分 call 不含菜单，证据 call 补引文；调用数翻倍）。实现仅在触发时进行。
- **F2（仅当分歧 >1 或 severe_miss >1）**：单纯指令解耦不足以消除锚定 → 预注册更强结构解耦（评分阶段完全移除菜单，证据阶段单独提供；即两阶段 v1.3.0）。不针对人类标签逐例调 prompt；若仍不达，P1.5 记未达标，如实交付，留 P2。

## 5. 运行计划与预算（待批准；批准前零调用）

| 工作包 | 调用 | 估算 tokens（~15k/次） |
| --- | --- | --- |
| 冒烟（2 dev with_gold） | 2 | ~30k |
| W1 dev 重评（v1.2.0，12 例，prompt 变→缓存失效全新） | 12 | ~180k |
| W2 稳定性（2 例 ignore_cache） | 2 | ~30k |
| **基础合计** | **16** | **~240k** |
| 回退 F1/F2 两阶段 contingency（dev 评分+证据双 call） | ≤24 | ≤~360k |
| **上限** | **≤40** | **≤~600k** |

- 模型 qwen3.8-27b（同 P1）；第二模型 cross-judge 已在 P1 完成，P1.5 不重复（聚焦一致率恢复）。
- 硬约束调用数（--max-calls）；实际 usage 逐次计量。密钥经 env.local 加载，不打印。
- 探针（位置/改写）P1 已描述性完成，P1.5 不重复（除非解耦改变 prompt 结构需复测，届时另报）。

## 6. 可复现交付物（P1.5 完成时）

freeze v4 amendment；命令链（amend_freeze_v4 → run_rubrics_judge --split development v1.2.0 → 稳定性 → score_p1_results）；哈希；定向+全量测试日志；docs/P1_5_DELIVERY_REPORT.md（验收判定+指标+如实局限+预算台账）。

## 7. 批准记录

- 用户批准预算：**已批准**。用户 2026-11-19 聊天回复「批准 P1.5 预算」，批准基础 16 次（上限 ≤40，含回退 F1/F2 两阶段 contingency ≤24）；模型 qwen3.8-27b。批准前零调用；批准后按 §5 执行。
- 预注册固定时间：2026-11-19；变更须修订记录。
