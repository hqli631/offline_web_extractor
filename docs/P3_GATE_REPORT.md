# P3 奖励化门槛评估交付报告（gate FAIL · 如实交付）

> 日期：2026-11-22 · 复审/批准：hqli631 · 执行：Codex
> 判定：**gate FAIL**（冻结阈值下 dev 侧硬检查在 v1.2 与 v1.3 两种协议均不通过）。
> 后果：**judge 分数继续禁止作为训练奖励**；不重测、不刷分、不回改封存 gold。
> 状态：**已收尾（2026-11-22 用户选 A）**。gate FAIL 为最终判定；v3 未消耗部分永久封存待未来周期；judge 分数禁止奖励化。

## 1. 摘要

P3 完成了完整闭环：分歧复审（10 案）→ 用户 verdict 封存 → 预注册修订提案（judge v1.3.0）→ 用户批准 → 实施 + freeze v6 → dev 池 18 例真实评测 → **预注册回归护栏 FAIL**（severe_miss 3>1）→ **按预注册后果回滚 v1.2.0**（freeze v8，字节级恢复已证明）→ v1.2 dev 预览（零调用）→ **false_alarm 0.1667>0.15 亦 FAIL**。gate PASS 须 dev 与 v3 全部硬检查通过；dev 侧在两种协议下均已失败，故 **FAIL 判定已定**，v3 消耗与否不改变判定。

## 2. 目标逐项证据

| 目标项 | 状态 | 权威证据 |
| --- | --- | --- |
| (1) 分歧案卷导出 + 证据复审包 | ✅ | outputs/human_review/p3.calibration.v1（C01–C10，判据驱动：decision_mismatch/dim_gap_ge2/judge_missed_defect/judge_severe_human_not）；tools/build_p3_review_kit.py |
| (2) 用户逐案复审 + findings 封存 | ✅ | outputs/p3.findings.v1/calibration_findings_p3.json（sha 4542fdc60357907d…；hqli631 2026-11-22，discipline_ack=true）；P2 gold 未回改、frozen_test v2 未重评 |
| (3) 预注册 freeze 修订（v1.3 候选） | ✅ 全周期 | docs/P3_AMENDMENT_PROPOSAL.md（批准原话记录）→ freeze v6（ad4c9bcd00a55919…）→ dev 护栏 FAIL → 回滚 freeze v8（544dd33ad11fceaa…）；无事后调参 |
| (4) 门槛预注册 + 评估 | ✅ | outputs/p3.gate.config.v1.json（d70e0d3c38a55354…，status=frozen）；dev 评估见 §5；v3 已预注册构建封存（freeze v7 b536ad193d41d5f4…），评估待决定 |
| (5) 可复现报告后停止 | ✅ 本文件 | 命令 §8 + 哈希 §7 + 测试日志 §9 + 局限 §10 |

## 3. 校准复审 findings（10 案，用户 verdict）

| 案 | 模式 | verdict |
| --- | --- | --- |
| C01 | interpreter-noise | judge_correct |
| C02 | interpreter-injection | judge_correct |
| C03 | nasa-clean 残留噪声 | human_correct |
| C04 | nasa-missing 首段 | both_partially_correct |
| C05 | nasa-noise 长页 | human_correct |
| C06 | nasa-duplicate | judge_correct |
| C07 | nasa-injection | judge_correct |
| C08 | w3ca11y-noise | human_correct |
| C09 | w3ca11y-reorder | human_correct |
| C10 | w3ca11y-injection | judge_correct |

计数：judge_correct×5 / human_correct×4 / both_partially×1 → amendment_signal=true。
关键发现：注入×3 人类 gold 漏检（judge 严重度有证据支撑）；严重度应随污染相对量级分级；源存在≠候选 inclusion 正当理由；相邻乱序需显式核对。

## 4. 修订周期全记录（预注册 → 批准 → 实施 → 护栏 → 回滚）

1. 提案：docs/P3_AMENDMENT_PROPOSAL.md（锚点 '3'/'2' 粒度示例 + 3 条通用约束；不改注入处理/重复归类；无案例专属规则）。
2. 批准：2026-11-22 hqli631 原话 `批准修订；批准阈值；v3 选 b 含采集；批准预算`（记录于提案 §5 与 gate plan §7）。
3. 实施：JUDGE_VERSION 1.2.0→1.3.0；judge sha edd841ef…→**46f2111837ba64c168452eb98ffa2001e238832384f7eed3f0b0fdc683a8d076**；freeze v6（parent v4；23 银标 prompt_chars-only 刷新已证明；P2 v5 标签故意不动）；commit a9c25f7。
4. dev 池 18 例真实评测（qwen3.8-27b，冻结参数 20000/2200/90）：**18/18 accepted**；orig12 + p2dev6 分开报告。
5. **护栏 FAIL**（提案 §3 预注册：reject≥10% 或 severe_miss>1 或 false_alarm>0.15 → 回滚）：severe_miss=3（cal-appetite-noise / cal-blurb-noise / cal-blurb-reorder）。证据 outputs/p3.devguard.v1（001e6b99031805a4…）。
6. **回滚执行**（预注册后果，非新决定）：judge 字节级恢复 sha **edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891**（==freeze v4）；freeze v8 文件哈希集==v4 已证明；23 标签 prompt_chars 恢复；commit 08e56c2。v1.3 产物（freeze v6、p3.dev.* 批次、v3 前 4 案）封存为修订失败证据。

## 5. Gate 评估（冻结阈值 · dev 侧）

冻结阈值（outputs/p3.gate.config.v1.json，批准后不可改）：

| 指标 | dev 池 | v3 一次性 |
| --- | --- | --- |
| 拒绝率 | <0.10 | <0.10 |
| severe_miss | ≤1 | ≤1 |
| false_alarm 率 | ≤0.15 | ≤0.15 |
| 决策一致率 | ≥0.85（原 dev12 子集） | ≥0.80 |
| Cohen κ | ≥0.75（原 dev12，非退化） | 报告+CI |
| pass_recall | — | ≥0.80 |

**v1.3 × dev18**（outputs/p3.dev.orig.v1.json aab91514… + p3.dev.p2.v1.json a3a88c23…）：

| 检查 | 观测 | 判定 |
| --- | --- | --- |
| reject_rate | 0.0 | PASS |
| severe_miss_count | **3** | **FAIL** |
| false_alarm_rate | 0.0556（1/18） | PASS |
| orig12 match | 0.75 CI[0.5,1.0] | （<0.85，亦不达标） |
| orig12 κ | 0.5443 | （<0.75，亦不达标） |

**v1.2 × dev18 预览**（零调用；历史批次 p1_5.dev.v1.json + p2.judge.v2.json dev6；outputs/p3.devguard.v12preview.v1 b8461cc3…）：

| 检查 | 观测 | 判定 |
| --- | --- | --- |
| reject_rate | 0.0 | PASS |
| severe_miss_count | 0 | PASS |
| false_alarm_rate | **0.1667**（3/18）CI[0.0,0.3333] | **FAIL** |
| orig12 match | 0.9167 CI[0.75,1.0] | PASS |
| orig12 κ | 0.8554 | PASS |

v1.2 false_alarm 3 例：cal-appetite-reorder（P1.5 已知误报）；cal-interpreter-noise 与 cal-interpreter-instruction_interference（**正是 P3 复审 C01/C02 用户判定 judge_correct 的人类 gold 漏检**）。指标按封存 gold 机械计算，gold 不可回改——一致率≠准确率在此具体化。

**判定逻辑**：PASS 须 dev 与 v3 全部硬检查通过。v1.3 severe_miss FAIL；回滚后 v1.2 false_alarm FAIL。**gate FAIL 已定**，v3 结果无法改变（其检查只能增加失败项）。bootstrap B=10000 seed=20261119。

## 6. v3 封存测试状态

- 构建：路线 b（批准采集）；NPR text.npr.org/nx-s1-6000601（14,398 字符/73 段）+ GNU your-freedom-needs-free-software（19,271 字符/23 段）；均 ≤20k **不截断**（12/12 source_truncated=False）→ pass 类可达。
- 封存：samples/p3_manifest.json + outputs/p3.freeze.v7.json（12 案=2 模板×6 变异；with_gold 银参考；盲评包 outputs/human_review/p3.blind.v1，P01–P12，decision 全 null 待标）。
- 消耗：v1.3 下评了 4/12（nprtext clean/missing/noise/duplicate；outputs/p3.judge.v1.json 176a997a…）后**预算护栏暂停**；该 4 案属失败修订，**封存排除于 gate**。
- 人类 gold：未标注（0/12）。pass 类泛化**未检验**（如实局限）。
- 待用户决定：A 不消耗（FAIL 收尾）/ B 在 v1.2 下补完 12 案描述性证据（需预算 ~620k + 盲评 + gate-config v1.2 pin 修订记录）/ C 新改进循环。

## 7. 预算与采集核算（如实）

- 批准：~30 次 / ~400k / 上限 460k（2026-11-22）。
- 实际：**22 次调用 / 379,457 tokens**（dev orig 冒烟 15,263 + orig 157,347 + p2dev 124,112 = 296,722；v3 冒烟 20,735 + 部分 62,000 = 82,735）。
- 估算偏差：v3 带 gold 不截断 prompt 实测 ~20.7k/次（原估 ~9k）→ 触发预算护栏暂停（outputs/p3.budget.pause.v1.json）；600k 延期请求已作废，待 A/B/C。
- 采集：共 12 次 HTTP 抓取，保留 2 页。cnn-lite 4 次尝试均 ~650k 字符（拒绝）；GNU 首轮 404×1 + 超窗×3（拒绝）；全部记录于 outputs/p3.collection.v1.log / v2.log 与 samples/p3_*.html.source.json（fetch_log + rejected_attempts）。原估"2 次抓取"偏差如实记录。
- 关键哈希（前 16 位；全值见各产物）：gate-config d70e0d3c38a55354 / freeze v4 aad20e177e8e0a16 / v6 ad4c9bcd00a55919 / v8 544dd33ad11fceaa / v7 b536ad193d41d5f4 / findings 4542fdc60357907d / judge 现 edd841efb52961f0。

## 8. 复现命令（Windows PowerShell；python 为捆绑运行时）

```powershell
$env:PYTHONIOENCODING='utf-8'
.\run.cmd test *> outputs\repro.suite.log          # 479 tests OK
# v1.3 dev 护栏（复现 FAIL；输出名须新）
python -m tools.check_p3_dev_guard --output outputs/repro.devguard.v13
# v1.2 dev 预览（复现 FAIL；零调用）
python -m tools.check_p3_dev_guard --gate-config outputs/p3.devguard.v12preview.config.json --orig-batch outputs/p1_5.dev.v1.json --p2-batch outputs/p2.judge.v2.json --output outputs/repro.devguard.v12
# 回滚/冻结/v3 构建验证（一次性工具拒绝重跑属设计；用测试验证）
python -m unittest tests.test_p3_rollback_v12 tests.test_check_p3_dev_guard tests.test_build_p3_calibration tests.test_score_p3_gate
```

哈希核验：各 freeze JSON 的 files/cases 条目即权威哈希；judge 现 sha 须 == freeze v4/v8 的 src/webextractor/rubrics_judge.py 条目（edd841ef…）。

## 9. 测试证据

- 全量 **479 tests OK**：outputs/p3.rollback.suite.v2.log（回滚后权威日志）。
- 历程：428（P2 末）→457（gate 评分器+29）→467（v1.3+10）→477（v3 构建+10）→479（回滚验证+护栏 5，v13 测试 10 移除，v7 哈希测试调整为历史记录语义）。
- 一次性异常如实记录：P3 早期一次瞬态 ImportError（333/errors=3），前后全量均 OK，证据 commit a8e0dea + outputs/p3.suite.repro.v1.log。

## 10. 如实局限

1. 单一标注者（IAA 被用户取消）；人类 gold 也只是参考之一。
2. **一致率≠准确率**：v1.2 的 3 例 false_alarm 中 2 例是用户已裁决的 gold 漏检（C01/C02 judge_correct）；指标按封存 gold 机械计算，FAIL 不等于 judge 在这 2 例上错。
3. 原 dev12 gold 经 P0 裁决（锚定局限）；P2 dev6 为盲评但全 uncertain（κ 退化）。
4. dev≠泛化；v3 pass 类泛化**未检验**（未消耗/未标注）。
5. frozen_test v1 永久封存；v2 已一次性消耗未重评；v3 前 4 案属失败修订、排除于 gate。
6. 修订失败根因（发现，非辩解）：粒度原则方向正确（v1.3 修复 2 例误报）但与 P0 时代 gold 的严重度校准冲突（3 例 severe_miss）；根因是 **gold 校准代际不一致**，不可通过回改旧 gold 或放宽阈值解决。
7. 采集/预算估算偏差已如实记录（§7）。
8. gate FAIL → judge 分数禁止奖励化；奖励接线为后续独立工作。

## 11. 改进路线（后续独立工作，不在本目标自动启动）

1. **gold 校准根因**：新建盲评 gold 的 dev 数据（新模板、注入/噪声/乱序变异、标注者培训含注入识别），替代 P0 裁决 gold 做门槛评估；旧 gold 永久封存不改。
2. **v1.4 候选方向**（须新预注册）：在 v1.3 粒度原则基础上，以新盲评 gold 校准严重度边界；保留注入处理（已验证正确）；显式顺序核对保留。
3. **指标设计**：预注册区分"对封存 gold 的一致率"与"对裁决后 gold 的一致率"双轨报告；false_alarm 附 adjudicated-miss 注记（不改硬阈值）。
4. pass 类泛化：v3 已就绪（不截断、with_gold），可在任何未来周期一次性消耗。

## 12. 批准与决定记录

- 2026-11-22 hqli631：`批准修订；批准阈值；v3 选 b 含采集；批准预算`（4 项）。
- 回滚：预注册后果自动执行（提案 §3），非新批准。
- **2026-11-22 hqli631：`A，节点5计划也一并给出`** → 以 FAIL 报告收尾，P3 目标完成；v3 剩余 8 案不消耗，封存待未来预注册周期；节点 5 修复闭环另案批准（docs/NODE5_REPAIR_LOOP_PLAN.md）。
-  commits：00545fb→ebc297a→a8e0dea→72b2749→83bd63b→a9c25f7→e63d4d7→08e56c2（GitHub main 同步）。
