# P-B 预注册修订提案（DRAFT · 零调用 · 待用户批准）

> 日期：2026-11-23 ｜ 状态：**草案，未冻结，未消耗任何模型调用**
> 分支依据：`docs/P3_GATE_PLAN.md` §2 步骤 4（2026-11-22 冻结批准）原文：
> "若 findings 不支持修订（judge v1.2 已正确、人类 gold 错）：不修订协议；门槛评估直接用 v1.2 + 修正后的人类 gold 流程（新案例盲评，不回改旧 gold）。"
> P-A 封存裁决（A01/A02 judge_correct，A03/A04/A05 human_correct）支持此分支：**v1.2 三例"误报"全部 vindicated，v1.3 降级证伪**。故 P-B 不放宽严重度、不改 judge 协议。

## 0. 决策摘要（待批准）

| 决策 | 内容 | 推荐 |
| --- | --- | --- |
| **D1** | 协议：保留 judge v1.2 字节冻结，**不做严重度修订**；R1/R2/R3 仅固化入人类锚点指南；长页证据工程**延后**至 gate 后独立协议周期 | 批准 |
| **D2** | gold 基准：dev 用裁决 overlay（3 例，预注册）+ 封存 gold 机械轨双轨披露；测试集：**复用封存 v3 全 12 例**在 v1.2 下重判（v1.2 对 v3 零暴露）；dev 模式 as-ran 披露 | 批准 |
| **D3** | 用户任务：按 `docs/P_B_ANCHOR_GUIDE.md` 完成 v3 **12 例盲评**（gold 先封存，judge 后运行） | 你来填 |
| **D4** | 预算：v3 冒烟 1 + 一次性 12 = **13 调用 ≈ 269k tokens**；上限 **14 调用 / 300k**；dev **零调用** | 批准 |

## 1. 背景与证据（均已封存）

- P-A findings：`outputs/human_review/pa.adjudication.v1/pa_findings.json` sha `63202e6b…`（A01/A02 judge_correct；A03/A04/A05 human_correct）。
- P3 findings：`outputs/p3.findings.v1/calibration_findings_p3.json` sha `4542fdc6…`（C01–C10；上游 kit findings sha `1bba537b…` 已链式核验）。
- 双轨结论：对**裁决后 gold**，v1.2 真实 false_alarm = 0/18；对**封存 gold** 机械计算 false_alarm 3/18 = 0.167 > 0.15 → FAIL 仍成立（预注册纪律，不可回改）。
- judge v1.2 冻结 sha `edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891`；当前 src 已回滚至 1.2.0。

## 2. D1 协议决策：保留 v1.2，锚点入指南，长页工程延后

- **不修订 judge 协议**。v1.2 行为已大体符合 R1/R2/R3（noise/reorder 记 major，标题双空格记 minor）。任何 judge prompt 改动都会产生新版本、使"v1.2 冻结 gate"失效，故本周期禁止。
- R1/R2/R3 固化入 **人类盲评锚点指南**（`docs/P_B_ANCHOR_GUIDE.md`），用于 v3 新案例盲评与未来周期——这正是步骤 4"修正后的人类 gold 流程（新案例盲评，不回改旧 gold）"。
- **长页分块证据/截断工程延后**：Node 5 mdn/github 拒绝（>20k 截断致证据不足）是可用性局限，但 v3 短页（≤20k，12/12 不截断）已绕开截断，不影响本 gate。长页工程若改 judge 证据流程 → 属 v1.4 候选，需独立 dev 校准 + 新封存测试，不在 P-B 内启动（避免范围膨胀与冻结破坏）。

## 3. D2 gold 基准与测试集

### 3.1 dev 轨道：裁决 overlay（零调用，已构建）

- 工具：`tools/build_pb_gate_inputs.py`（15 测试通过）；产物 `outputs/pb.gate.inputs.v1/`（manifest sha `a81b7834…`）。
- 仅 **3 例** judge_correct 裁决进入 overlay（其余 dev 案例无封存 judge_correct 裁决，工具 fail-closed 审计）：

| 代码 | 案例 | 修正（judge v1.2 值，程序化复制+哈希核验） |
| --- | --- | --- |
| C01 | cal-interpreter-noise | cleanliness 3/minor → 2/major；decision uncertain → fail |
| C02 | cal-interpreter-instruction_interference | completeness 4/none → 2/major；cleanliness 4/none → 1/critical；structure 4/none → 2/major；decision uncertain → fail |
| A01 | cal-appetite-reorder | structure 3/minor → 2/major；decision uncertain → fail |

- 规则：judge_correct → 仅替换封存 findings 点名的分歧维度 score+severity（人类 status/note 保留）+ decision（若分歧）；human_correct → 不动；**封存 gold 文件永不改写**，overlay 为带完整出处的派生产物。
- C03–C10 属已消耗 frozen_test v2（永不重评），不在 dev 池；A02（n5-blurb-title）属 Node 5，不在 dev 池；A03/A04/A05 human_correct → 不改。
- P2 batch 含 18 例（dev6 + frozen v2 12），gate 视图**过滤仅留 dev6**，frozen v2 排除。

### 3.2 dev 预览（工程验证 · 非正式 gate · 零调用）

| 轨道 | reject | severe_miss | false_alarm | orig12 match | orig12 κ |
| --- | --- | --- | --- | --- | --- |
| **overlay（预注册基准）** | 0.0 | 0 | **0.0** | **1.0** | **1.0** |
| 封存 gold 机械（仅披露） | 0.0 | 0 | 0.167（FAIL） | 0.9167 | 0.8554 |

- overlay 轨道 dev 全部硬阈值通过；协议/数据冻结完整性检查（check_protocol/check_data_freeze）orig/p2 均 OK。
- **循环性披露（重要）**：3/18 例 overlay 把 gold 裁向 judge，机械上强制一致；orig12 κ=1.0 部分由此而来（A01 是 orig 唯一分歧例）。**其余 15/18 例无裁决、完全一致是真实证据**。dev 轨道定位为护栏，gate 的决定性泛化证据是 **v3（独立、盲评、无 overlay）**。
- **事后张力（披露，不追溯修正）**：`cal-interpreter-reorder` judge v1.2 与旧 gold 均 structure 3/minor（一致），但与 R1 零容忍相悖；该案无分歧、从未入裁决队列，本周期不补裁、不刷分。**v3 reorder 变异独立检验 v1.2 是否满足 R1**。另 `cal-interpreter-duplicate` 存在维度级残差（judge completeness/structure 3/minor vs gold 4/none，decision 一致、非 severe、未裁决），如实披露。

### 3.3 v3 轨道：复用封存 v3 全 12 例，v1.2 重判

- 数据：`samples/p3_manifest.json` + `outputs/p3.freeze.v7.json` sha `b536ad19…`（2 模板 × 6 变异，with_gold，≤20k 不截断）。**数据冻结不变**。
- v1.2 对 v3 **零暴露**（v3 为 v1.3 周期构建；v1.2 冻结早于 v3）；4 例曾被 v1.3 消耗仅排除于 v1.3 评分，**未发生任何 v3 来源的调参**（v1.3 已回滚，v1.2 sha 未变）。故 v1.2 下全 12 例为干净一次性评估。
- freeze v7 的 batch_config 不钉 judge_version（仅数据参数）；gate config v2 钉 1.2.0，由 check_protocol 在 batch signature 上强制。无需 freeze 修订。
- 备选否决：仅用 8 例未消耗 → 削弱 n 与 pass 类检验，偏离预注册 12 例设计；新采 v4 → v3 对 v1.2 完好，无需新采集。
- human gold：用户按指南盲评 12 例（当前全 NULL）；**gold 先 ingest 封存，judge 后运行**（ingest 工具纪律，防锚定）。

### 3.4 dev 模式策略：as-ran 披露

- 16 例 with_gold + 2 例 source_only（cal-iana-clean/noise），均为 v1.2 冻结下真实产出；逐案披露。不推荐 +2 调用统一模式（增预算、dev 已是 authentic v1.2 输出）。

## 4. D3 用户任务（v3 盲评 12 例）

1. 读 `docs/P_B_ANCHOR_GUIDE.md`（R1/R2/R3 + 机械规则）。
2. 填 `outputs/human_review/p3.blind.v1/human_labels.blind.json`（P01–P12，decision + 维度 score/status/severity + note）；证据在 `packets/`。
3. 完成后告知助手；助手 ingest 封存 gold（零调用），再进入模型调用阶段。

## 5. D4 预算（待批准）

| 项 | 调用 | 估算 tokens |
| --- | --- | --- |
| dev18（复用封存 v1.2 评估） | **0** | 0 |
| v3 冒烟（1 例，API 健全性） | 1 | ~20.7k |
| v3 一次性 12 例（冒烟缓存复用 → 12 新调用） | 12 | ~248k |
| **合计 / 上限** | **13 / 14** | **~269k / 300k** |

- 估算依据：v3 with_gold 不截断实测 ~20.7k/调用（P3 周期测量）；上限含 ≤1 次 resume 余量。
- 取代 gate config v1 预算（30 调用/460k，v1.3 周期已关闭）；阈值**不改**，仅预算按零调用 dev 复用下调。

## 6. 预注册执行序列（批准后；阈值与 v1 逐字一致）

1. 助手：gate config v2 草案（`outputs/pb.gate.config.v2.draft.json` sha `16dea5a0…`，status=draft，评分器拒用）→ 填入批准原话/日期 → 冻结为 `outputs/pb.gate.config.v2.json`（status=frozen）。batch_config 仅 judge_version 1.3.0→1.2.0；dev/v3 阈值、seed=20261119、B=10000 与 v1（sha `d70e0d3c…`）逐字一致；增补 gold_basis/dev_mode_policy/discipline。
2. 用户：v3 盲评 12 例（D3）。
3. 助手（零调用）：`python -m tools.ingest_p2_human_labels --labels outputs/human_review/p3.blind.v1/human_labels.blind.json --kit-dir outputs/human_review/p3.blind.v1 --manifest samples/p3_manifest.json --freeze outputs/p3.freeze.v7.json --output outputs/human_review/p3.gold.v1` → 封存 v3 gold，核验 12/12。
4. 助手（模型调用，预算守卫）：冒烟 `python -m tools.run_rubrics_judge samples/p3_manifest.json --output outputs/pb.v3.smoke.v1.json --max-source-chars 20000 --max-calls 1 --split frozen_test`；全量 `python -m tools.run_rubrics_judge samples/p3_manifest.json --output outputs/pb.v3.judge.v1.json --max-source-chars 20000 --max-calls 13 --split frozen_test`（复用冒烟缓存；新调用 ≤13）。
5. 助手（零调用）：`python -m tools.score_p3_gate --gate-config outputs/pb.gate.config.v2.json --dev-batch orig=outputs/pb.gate.inputs.v1/dev.orig.batch.json --dev-gold orig=outputs/pb.gate.inputs.v1/dev.orig.gold.json --dev-freeze orig=outputs/rubrics_judge.node3.freeze.v4.json --dev-manifest orig=samples/calibration_manifest.json --dev-batch p2=outputs/pb.gate.inputs.v1/dev.p2.batch.json --dev-gold p2=outputs/pb.gate.inputs.v1/dev.p2.gold.json --dev-freeze p2=outputs/p2.freeze.v5.json --dev-manifest p2=samples/p2_manifest.json --v3-batch outputs/pb.v3.judge.v1.json --v3-gold outputs/human_review/p3.gold.v1/human_gold.p3.blind.json --v3-freeze outputs/p3.freeze.v7.json --v3-manifest samples/p3_manifest.json --v3-silver-dir samples/calibration/labels --output outputs/pb.gate.v1`
6. 助手：`docs/P_B_DELIVERY_REPORT.md`（双轨 dev + v3 一次性 + 全部局限 + 命令/哈希 + 测试数）；secret scan → commit → push；**停止**。FAIL 不重测、不调参后重报。

## 7. 风险与局限（诚实，批准前须知）

- **v1.2 可能不完全满足 R1**：interpreter-reorder 已显示 v1.2 对某类 reorder 记 minor。若 v3 reorder 上 v1.2 再记 minor 而锚点 gold 记 severe → v3 severe_miss/decision 分歧 → **gate 可能 FAIL**。FAIL 则奖励化继续禁止，进入未来 v1.4 协议周期（R1 入 judge prompt + 独立校准）。这是真实风险，不隐瞒。
- **pass 类小 n**：v3 human=pass 预计仅 clean×2；pass_recall ≥0.80 要求 2/2 全 pass，小 n 脆弱，如实披露。
- dev overlay 3/18 锚定循环性；单标注者 IAA 缺失；一致率≠准确率；封存 gold 机械 FAIL 不可回改。
- gate PASS 仅授权**已验证范围**（同模板族、冻结协议、受控变异分布）内奖励化；SFT/RL 接线为后续独立工作。
- "千亿级"为业务语境，当前证据仅支持小规模工程结论。

## 8. 批准清单（可一句话批准）

建议原话：`批准 D1 保留 v1.2；批准 D2 overlay 基准 + v3 复用 12；批准 D4 预算 14 调用/300k；我将完成 12 例盲评`

## 9. 本轮已交付（零调用）

- `tools/build_pb_gate_inputs.py` + `tests/test_build_pb_gate_inputs.py`（15 测试）
- `outputs/pb.gate.inputs.v1/`（dev 视图 + overlay gold + 审计 + manifest sha a81b7834…）
- `outputs/pb.gate.config.v2.draft.json`（draft，阈值同 v1，judge 1.2.0）
- `docs/P_B_ANCHOR_GUIDE.md`、本提案
- dev 轨道零调用预览（§3.2，非正式 gate）
