# P3 协议修订 · judge v1.3.0（已批准 · 2026-11-22 实施）

> 状态：**已批准并实施**。2026-11-22 hqli631 批准（原话：`批准修订；批准阈值；v3 选 b 含采集；批准预算`）；rubrics_judge.py v1.3.0 + freeze v6（parent v4）。
> 依据：outputs/p3.findings.v1（复审者 hqli631，2026-11-22，10 案 verdict：judge_correct×5 / human_correct×4 / both_partially_correct×1）。
> 纪律：仅通用原则，**禁止案例专属规则**；不回改 P2 gold/结果；不重评 frozen_test v2；v1.3 先在 dev 池（可调参轮）评估，v3 封存后一次性。

## 1. 发现 → 修订映射

| 发现（verdict 模式） | 结论 | 修订动作 |
| --- | --- | --- |
| A 注入×3 judge_correct | v1.2 对注入污染的严重度判定正确 | **不改**；记录人类 gold 漏检风险（注入文本可能被标注者"正常化"） |
| B noise：短页 major 正确（C01）、长页 minor 正确（C05/C08） | 严重度应随**污染相对量级**变化，v1.2 一刀切 major | 锚点澄清：噪声严重度按块数/占正文比例分级 |
| B missing：C04 both_partially（nasa 首段缺失） | 缺失严重度应考虑**位置重要性与比例** | 锚点澄清：首段/摘要缺失偏 major，单个非首段正文缺失 minor |
| C residual noise：C03 human_correct（judge none） | judge 把"源里也有"当作放行理由 | 新约束：**源存在 ≠ 候选 inclusion 正当理由** |
| C reorder：C09 human_correct（judge none） | judge 漏检相邻乱序 | 新约束：**显式顺序核对**；锚点细化：单处相邻交换 minor，多处/大规模乱序 major |
| C duplicate：C06 judge_correct | 重复缺陷归入 completeness/structure 正确 | **不改**；记录归类指引 |

## 2. 具体文本变更（提案）

### 2.1 anchors（rubrics_judge.py build_prompt instruction['anchors']）
- '3' 改为：`Small local defect (e.g. missing title number; a single short noise block in a long article; one non-lead body paragraph missing; a single adjacent paragraph swap with content intact)`
- '2' 改为：`Clear moderate loss or contamination (e.g. noise spanning multiple blocks or a substantial share of a short article; missing lead/abstract or multiple paragraphs; multi-block order disruption)`
- '4'/'1'/'0' 不变。

### 2.2 constraints 新增 3 条（通用原则）
1. `Severity granularity: cleanliness major when noise is pervasive/multi-block or a substantial share of the article, minor for a single short residual block; completeness weighs toward major when the lead/abstract or multiple paragraphs are missing, minor for one non-lead body paragraph; structure minor for a single adjacent swap with content intact, major for multi-block/large-scale order loss.`
2. `Source presence is not justification: navigation/share/subscribe/feedback/footer text in the candidate is contamination even if present verbatim in the source; cite the s:N region. Legitimate editorial links remain allowed.`
3. `Order check: explicitly compare candidate narrative paragraph/heading order against the gold/source sequence; a local swap is a structure defect even when all content is present.`

### 2.3 版本与冻结
- JUDGE_VERSION '1.2.0' → '1.3.0'；RUBRICS VERSION 2.0.0 不变（维度/分值域/决策规则不变）。
- 新冻结记录 outputs/rubrics_judge.node3.freeze.v6.json（parent v4；记录 v1.3 judge sha、batch_config 不变、manifest 不变）；p2.freeze.v5（数据冻结）继续有效。
- 既有测试全量回归 + 新增锚点/约束单元测试；dev 池评估前冻结。

## 3. 预期效果与回归风险（如实）
- 预期：长页单块噪声 major→minor（C05/C08 型）、残留噪声 none→minor（C03 型）、相邻乱序 none→minor（C09 型）、首段缺失维持 major 倾向（C04 型）。
- 风险：新约束可能使 cleanliness/structure 整体偏严（误报上升）或引用校验拒绝率上升；**dev 池 18 例可调参轮**正是为暴露回归而设；若 dev 拒绝率≥10% 或 severe_miss>1 或 false_alarm>0.15 → 修订失败，回滚 v1.2 并如实报告（不刷分）。
- 注入行为不应变化（A 类已正确）；dev 池含注入案例可验证无回归。

## 4. 批准后执行链（预算另批）
1. 实施 §2 文本变更 + 测试 + freeze v6（零调用）。
2. v3 构建（路线待选：a 微夹具 / b 新采集 2 短页【推荐，需采集批准】）+ 用户盲评 12 例 + 封存（零调用）。
3. 预算批准 → judge v1.3 × dev 池 18（~288k tokens）→ v3 一次性 12（~110k）→ gate 评分（P3_GATE_PLAN §4 阈值）→ docs/P3_GATE_REPORT.md → GitHub → 停止。
4. gate PASS → judge 分数在已验证范围内可作奖励（奖励化接线为后续独立工作）；FAIL → 如实报告，不重测。

## 5. 批准记录
- 修订提案批准：**2026-11-22 hqli631**（原话：`批准修订；批准阈值；v3 选 b 含采集；批准预算`）
- 门槛阈值批准（P3_GATE_PLAN §4）：**2026-11-22 hqli631**（同上原话）
- v3 路线选定 + 采集批准：**2026-11-22 hqli631，选 b，含 2 次 HTTP 采集批准**（同上原话）
- 模型预算批准（~30 次 / ~400k / 上限 460k）：**2026-11-22 hqli631**（同上原话）

## 6. 执行结果（2026-11-22，闭环记录）

- 实施：judge v1.3.0（sha 46f21118…）+ freeze v6；dev18 真实评测 18/18 accepted。
- **护栏 FAIL**：severe_miss=3>1（cal-appetite-noise / cal-blurb-noise / cal-blurb-reorder）；orig12 match 0.9167→0.75、κ 0.8554→0.5443；reject 0% 与 false_alarm 0.0556 通过。证据 outputs/p3.devguard.v1。
- **按 §3 预注册后果回滚 v1.2.0**：judge 字节级恢复（sha edd841ef…==freeze v4）；freeze v8 回滚记录（文件哈希集==v4 已证明）；23 标签 prompt_chars 恢复；479 tests OK；commit 08e56c2。
- 发现（如实）：粒度原则修复了 2 例 v1.2 误报（interpreter-noise/injection），但与 P0 时代 gold 严重度校准冲突致 3 例 severe_miss；根因为 gold 校准代际不一致。不刷分、不改 gold、不放宽阈值。
- 详见 docs/P3_GATE_REPORT.md。
