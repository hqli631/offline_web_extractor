# P-F v1.4.1 预注册：missing 锚点修订周期（选项 A，已批准）

批准：hqli631，2026-11-23（回复 "A"：批准 v1.4.1 修订 + 约 19 调用/350k 新校准预算）。
上游：docs/P_F_STAGE1_REPORT.md（v1.4 阶段1触发预注册停止：missing 锚点 2/2 系统性违反）。

## 1. 修订范围（最小变更）

- **仅改 missing-body 锚点一条**：零裁量措辞——source/gold 中存在而候选缺失的任何有意义的正文段落/块一律 SEVERE（completeness≤2/major），与位置/长度/重要性无关；首段、引言段、任何单段正文均属关键正文；显式覆盖通用 "3=小局部缺陷" 量表；仅大规模缺失升级为 1/0/critical；纯空白/格式差异不算缺失。
- 其余 5 条锚点（R1/R2/R3/重复量级/注入）**逐字节继承 v1.4**（程序化导入 + 测试断言）。
- 执行语义（校验/decision 派生/截断标记/错误抑制）与 v1.2/v1.4 完全一致。
- 冻结链：v1.2 基座 sha edd841ef 不变；**v1.4 模块字节冻结不动**（pf.protocol.v1 pin 保持有效）；新模块 rubrics_judge_v141.py，JUDGE_VERSION=1.4.1，protocol_anchors=v1.4.1。

## 2. 事后修订披露（诚实边界）

- 本修订由阶段1 dev 的 2 例 missing 失败塑造 → **dev 轨道循环加深**：6/18 循环案例（overlay 3 + 重裁决 3）中的 2 例 missing 同时是措辞调参来源；dev 上 missing 通过含循环成分，**独立泛化结论只能来自 v4**。
- v4（路线 A 新采 2 模板 ×6 变异）对 v1.4.1 **零曝光**，一次性密封测试地位不变；frozen v1/v2/v3 永不重跑；v3 12 例对 v1.4.x 永久曝光，仅作 development。
- 单标注者、IAA 未测、一致率≠准确率沿用声明。

## 3. 预算（阶段1b）

- 计划：冒烟 1 + dev orig 12 + dev p2 6 = 19 次全新 v1.4.1 调用（--ignore-cache）。
- 上限：**20 调用 / 350k tokens**（19 计划 + ≤1 重试；qwen3.8-27b，阶段1实测 ~16.6k/次）。
- 重试纪律：仅模型侧失败（空响应/网络）可重试；validation 拒绝不重试不调参。
- 阶段2（v4 一次性 12 + ≤1 冒烟/续跑，13/250k）**届时单独审批**。

## 4. 进入 F3 的预注册接受标准

阶段1b 校准（对 pf.dev.gold.v2，阈值逐字节沿用冻结 v1/v2）须**全部**满足：
1. reject_rate < 0.10；severe_miss_count ≤ 1；false_alarm_rate ≤ 0.15；
2. orig 子集 decision_match ≥ 0.85 且 Cohen κ ≥ 0.75（非退化混合决策）；
3. **missing 锚点遵循**：所有 accepted 的 missing_paragraph 案例 completeness ≤2 且 severity major/critical（无系统性违反）。

任一不满足 → 再次停下报告，不自动调参；v1.4.2 需新批准周期。满足 → F3 采集（≤10 抓取，零模型调用）→ 正式建集 + 盲评 kit → 用户盲评 12 例 → gold 先密封 → 阶段2审批 → v4 一次性 gate → 可复现报告后停止。

## 5. 产物与验证

- 新模块 + runner 选项 1.4.1（默认 1.2 不变）；gate config v2（judge pin 1.4.1，阈值不变）；protocol pin v2（链 v1 + pb.freeze.v9）。
- 测试：v141 版本/冻结链/5 锚点逐字节/预算/执行等价；runner 1.4.1 接线与缓存隔离；全量套件绿。
- 每里程碑 secret scan + commit + push。
