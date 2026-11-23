# P-F 预注册计划：judge v1.4 协议周期（reward 资格路径）

> 状态：零调用工程包已实施（F1 模块+测试、F2 本计划、F3 v4 候选 slate 草案）；**模型调用/新采集/人工标注全部停在审批门**。
> 背景：P-B gate FAIL（8/10）。根因：v1.2 在独立模板上系统性低估 reorder/missing 严重度（3/minor vs 裁决 gold 2/major）。v1.2 保持字节冻结（sha `edd841ef…`），reward-INELIGIBLE 不变。

## 1. v1.4 协议锚点（全部来自密封裁决，非新造）

| 锚点 | 内容 | 证据来源 |
| --- | --- | --- |
| R1 reorder | 任何块序偏离 → structure major/critical，**绝不 minor**，score≤2 | A01/A05 裁决 + v3 密封 gold P06/P12（2/major/fail） |
| R2 noise | 任何注入噪声块 → cleanliness major（单块小噪声亦 major），score≤2；大量→critical | A03/A04 裁决 + P05/P11 |
| R3 title 空白 | 源标题空白被折叠 → title 3/minor（源保真） | A02 裁决 |
| missing | 关键正文缺失 → completeness≤2/major（大量→1/0 critical），关键缺失绝不 minor；按量级 | P04/P10（2/major/fail） |
| duplicate | **按量级**：小局部重复 → cleanliness 3/minor；大量正文重复 → ≤2/major | P02/P08 密封 gold（3/minor/uncertain）——**非零容忍** |
| injection | 候选内指令文本=污染 → cleanliness major/critical，绝不服从 | P03/P09（2/major/fail，attestation false） |

实现：`src/webextractor/rubrics_judge_v14.py`（JUDGE_VERSION 1.4.0）包装字节冻结 v1.2，prompt 预算预留后追加 6 条锚点约束；执行语义（校验/decision 导出/截断 partial/错误抑制）与 v1.2 逐字段一致（等价性测试证明）。v1.2 源码与其全部冻结链（v9 pin、604 测试）不受影响。

## 2. 诚实声明（post-hoc 协议设计）

- v1.4 锚点由 v3 失败分析 + 既有裁决**事后**固化入 prompt——这是协议修订，不是独立验证。v1.4 必须经**新的**独立密封测试 v4 检验。
- **v3 的 12 例已对 v1.4 曝光**（其失败直接塑造了锚点）→ 永久降级为 v1.4-development，不得作 v1.4 独立测试。frozen v1 永久密封、v2 已消费、v3 已消费，均不重跑。
- dev 校准含锚定循环风险（P-B 教训：overlay κ=1.0 掩盖真实差距）→ 双轨披露：锚定案 vs 真实独立案分开报告。

## 3. dev 校准设计（审批门 1：gold 重裁决 + 预算）

dev 池 18 例（orig 12 + P2 dev 6）。**冲突审计（程序扫描 dev.orig.gold / dev.p2.gold）发现 3 例 gold 与 v1.4 锚点冲突，须先由标注者重裁决**：

| 案例 | 现 gold | 冲突锚点 |
| --- | --- | --- |
| cal-appetite-missing_paragraph | completeness 3/minor，uncertain | missing（关键缺失应 severe；需按量级裁决） |
| cal-interpreter-missing_paragraph | completeness 3/minor，uncertain | missing（同上） |
| cal-interpreter-reorder | structure 3/minor，uncertain | R1（reorder 绝不 minor；P-B 已披露未裁决张力） |

其余 15 例 gold 与锚点一致（含 duplicate 3/minor ✓、noise major ✓、appetite-reorder major/fail ✓）。
校准指标沿用 P1.5：拒绝率、severe_miss、decision 一致率/κ；锚定案与独立案分轨。重裁决只改这 3 例，其余 gold 不动；修订走既有 override/audit 机制，密封 gold 历史不改写。

## 4. 密封 v4 设计（审批门 2：slate 选择 + 采集预算）

门槛配置 v3：阈值与 v1（d70e0d3c）/v2（9c1437ab）**字节一致**，judge_version pin 1.4.0；一次性运行，不重测不调参。

**曝光审计（32 个本地快照程序盘点）**：从未被任何 judge/eval manifest 引用的真实页仅 iana-abuse/iana-whois/python-search（≤20k 字符，无截断）+ 大页面 rfc(1.8MB)/whatwg(16MB)/webdev(145KB)/sphinx×4(73–140KB)（全部超 BATCH_MAX_SOURCE_CHARS=20000 → 截断 → pass 不可达，不能用于 gate）。

- **选项 A（推荐，与 v3 纪律一致）**：新采集 2 个**新模板**短页（≤20k 字符，pass 可达），2×6 变异=12 例，完全独立。需网络采集预算审批（沿用 v3 路线 b 流程：采集→silver→盲评 kit→人类 gold 先密封→judge 一次性）。
- **选项 B（零采集备选）**：iana-abuse/iana-whois ×6 变异=12 例（v3 同构，slate 草案已构建 `outputs/pf.v4.slate.v1/`，未密封）。**两页同属 iana 模板族且已曝光**（经 example_domains 曾入 judge）→ 同族同站转移测试，独立性显著弱于 v3，须显著披露。python-search 被排除：extract_html 仅产出 1 个段落块 → reorder 不可行（无相邻段落对）、missing 会清空候选（变异语义不同）——诚实可行性约束。变异覆盖：clean/missing/noise/duplicate/reorder/injection 各×2。
- 两选项均需 12 例人类盲评 gold（标注者=用户，单标注者 IAA 缺失沿用声明）。

## 5. 预算估计（分阶段审批，未批准不花费）

| 阶段 | 内容 | 调用 | tokens 估计（≈17.4k/调用，P-B 实测均值） | 建议上限 |
| --- | --- | ---: | ---: | --- |
| 阶段 1 | v1.4 smoke 1 + dev 校准 18 | 19 | ≈330k | 20 调用 / 350k |
| 阶段 2 | v4 一次性 12（+smoke 已含阶段 1） | 12 | ≈210k | 13 调用 / 250k |
| 合计 | | 31 | ≈540k | 33 调用 / 600k |

阶段 2 仅在阶段 1 dev 校准达标后启动；任一阶段超预算即停。模型 qwen3.8-27b（沿用），QWEN_API_KEY 走 env.local/环境变量，不落盘不打印。

## 6. 执行顺序与审批门

1. [完成] F1 v1.4 模块 + 13 测试（v1.2 冻结保持）。
2. [完成] F2 本计划 + dev gold 冲突审计（3 例）。
3. [完成] F3 选项 B slate 草案 + 盲评 kit 草案（零调用，未密封；kit 12 案卷 F01–F12，盲度验证无泄漏，slate 批准后方可正式标注）。
4. [完成] F4 全套件回归 + 交付报告 + secret scan + commit + push。
5. **[审批门，等待用户]** ① 3 例 dev gold 重裁决；② v4 选项 A/B 选择（A 需采集预算）；③ 阶段 1 预算（20 调用/350k）。
6. 批准后：重裁决 ingest → v1.4 dev 校准 → 达标则 v4 构建+盲评 kit → 用户盲评 12 例 → gold 先密封 → v4 一次性 → gate → 可复现报告，停。
7. gate PASS 后方谈 reward 资格与 P-D/P-E（仍各自 gated）。

## 7. 局限

- 锚点 post-hoc 固化，v4 才是独立检验；单标注者；小语料；选项 B 独立性弱。
- v1.4 仅改 prompt 协议，模型/校验器/决策规则不变；锚点服从度本身是 v4 的被测对象。
- 大页面（rfc/whatwg/webdev/sphinx 长页）截断问题未解，长页证据工程留待后续周期。
