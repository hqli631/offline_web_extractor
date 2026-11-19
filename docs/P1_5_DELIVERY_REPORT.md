# P1.5 Judge 一致率恢复 · 交付报告

日期：2026-11-19（Asia/Shanghai）。项目三 offline_web_extractor。
状态：**验收 ACCEPT —— 预注册护栏恢复，一般性解耦假设 H1 得证。**
预注册：docs/P1_5_META_EVAL_PLAN.md（调用前固定，用户 2026-11-19 批准「P1.5 预算」）。上游：P1 交付（docs/P1_DELIVERY_REPORT.md，硬指标达标但一致率护栏破，用户选路径 c）。

---

## 1. 执行摘要

- **三项预注册阈值全部达标 → verdict ACCEPT**：dev 拒绝率 **0%**（0/12，<10% ✓）、severe_miss **0**（≤1 ✓）、接受例决策分歧 **1**（≤1 ✓，护栏恢复）。
- **一般性解耦假设 H1 得证**：将证据菜单降级为引文附录 + SCORING INDEPENDENCE 约束（评分/严重度仅依实际缺陷幅度按锚点，菜单不得影响评分），消除了 v1.1 的菜单锚定漂移。无需回退 F1/F2。
- dev 决策一致率 **0.9167 / κ0.8554**（v1.1 0.7273/0.5286 → 大幅恢复）；逐维 exact 0.8333、±1 1.0、严重度符号 0.875。
- 拒绝率从 v1.1 8.3% 进一步降到 **0%**（blurb-missing_paragraph 从被拒变为接受且与人类一致）；severe_miss 从 1 降到 **0**。
- 残留 1 处分歧：cal-appetite-reorder（judge fail vs 人类 uncertain，false_alarm），在 ≤1 护栏内，如实披露。
- frozen_test 全程未重跑、未调参、永久封存至 P2；judge 分数仍不作训练奖励。

## 2. 工程（零调用阶段，已验证）

- judge **v1.2.0**（仅改 src/webextractor/rubrics_judge.py，sha256 edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891）：
  1. evidence_menus 移至 prompt **末位**（引文附录，在 source/candidate/gold 之后）；
  2. 新增 **SCORING INDEPENDENCE** 约束：score/severity SOLELY from actual defect magnitude per anchors；菜单 presence/absence/wording/quantity MUST NOT raise or lower any score or severity；
  3. 严重度锚点强化（none/minor/major/critical 依缺陷本身）。
  一般性原则，**无案例特异分支**（测试断言 prompt 不含 cal-/盲码）。菜单内容、空白折叠匹配、schema、s:/g: 引用规则、探针参数不变。
- freeze **v4**（outputs/rubrics_judge.node3.freeze.v4.json）：代码仅 rubrics_judge.py；23 silver 标签仅 prompt_chars 诊断刷新（逐字段证明评分内容不变）；候选/gold/manifest/源页/协议文档/rubrics_v2/构建器/batch_config 哈希不变。build_calibration_set --verify v4 = **MATCH**；check_freeze 历史 batch v6 对 v4 = **NONE**；协议文档哈希 ab0887b5… 不变。
- 工具 tools/amend_freeze_v4.py（幂等）；测试 P1.5 定向 10 项 + 全量 **361 项 OK**（outputs/rubrics_judge.p1_5.engineering.tests.v1.log，21.140s）；预检 12/12 dev prompt 预算内可构建。

## 3. 实际调用台账（批准后）

| 工作包 | 模型 | 新调用 | tokens |
| --- | --- | --- | --- |
| 冒烟（2 dev with_gold） | qwen3.8-27b | 2 | 30,022 |
| W1 dev 重评（v1.2.0，12 例，前 2 缓存） | qwen3.8-27b | 10 | 140,138 |
| W2 稳定性（2 例 ignore_cache） | qwen3.8-27b | 2 | 31,815 |
| **合计** | | **14** | **201,975** |

- 成功调用 **14 ≤ 批准基础 16**（上限 40）；tokens 201,975（input 192,930 / output 9,045），低于 ~240k 估算。回退 F1/F2 未触发（无 contingency 消耗）。
- 密钥经 env.local 的 QWEN_API_KEY 加载，全程未打印、未入库。

## 4. W1 development 验收（对照 P0 最终人类标签）

| 检查 | 结果 | 判定 |
| --- | --- | --- |
| 拒绝率 <10% | 0%（0/12） | ✓ |
| severe_miss ≤1 | 0 | ✓ |
| 接受例决策分歧 ≤1 | 1 | ✓ |
| **verdict** | | **ACCEPT** |

freeze_check NONE。dev 决策一致率 0.9167（11/12），κ 0.8554；逐维 exact 0.8333、±1 1.0、严重度符号 0.875；false_alarm 1（appetite-reorder）。

逐案（judge v1.2.0 vs 人类最终）：

| 案例 | judge | 人类 | 备注 |
| --- | --- | --- | --- |
| cal-appetite-clean | pass | pass | match |
| cal-appetite-missing_paragraph | uncertain | uncertain | match（v1.1 fail → 修复） |
| cal-appetite-noise | fail | fail | match |
| cal-appetite-duplicate | uncertain | uncertain | match（v1.1 fail → 修复） |
| cal-appetite-reorder | fail | uncertain | **MISMATCH + false_alarm**（唯一残留） |
| cal-appetite-title_number | uncertain | uncertain | match |
| cal-blurb-clean | uncertain | uncertain | match |
| cal-blurb-missing_paragraph | fail | fail | match（v1.1 被拒 → 接受且匹配） |
| cal-blurb-noise | fail | fail | match |
| cal-blurb-reorder | fail | fail | match（v1.1 uncertain/severe_miss → 修复） |
| cal-iana-clean | uncertain | uncertain | match |
| cal-iana-noise | fail | fail | match |

三版对比（dev）：

| 指标 | P0 最终 (v1.0) | P1 (v1.1) | **P1.5 (v1.2)** |
| --- | --- | --- | --- |
| 接受 / 拒绝 | 10 / 2（16.7%） | 11 / 1（8.3%） | **12 / 0（0%）** |
| 决策一致率 | 1.0 | 0.7273 | **0.9167** |
| Cohen κ | 1.0 | 0.5286 | **0.8554** |
| severe_miss | 0 | 1 | **0** |
| false_alarm | 0 | 2 | **1** |
| 接受例分歧 | 0 | 3 | **1** |
| 护栏 verdict | （P0 通过） | REJECT | **ACCEPT** |

**解读（诚实）**：v1.2 用 1 处分歧（appetite-reorder）换取 0 拒绝 + 0 severe_miss，护栏（分歧≤1）恢复。决策一致率 0.9167 略低于 P0 最终的 1.0，但 P0 的 1.0 建立在仅 10 接受例（2 例被拒排除）且为裁决后一致率（偏乐观）；v1.2 接受全部 12 例（含此前被拒的 appetite-duplicate、blurb-missing_paragraph，均与人类一致）。appetite-reorder 在 v1.0 匹配（uncertain）、v1.2 判 fail，是解耦后新引入的单一 false_alarm，留待 P2 扩规模检验是否系统性。所有数字均非独立泛化准确率。

## 5. W2 稳定性（描述性）

temp=0 复跑 2 例（appetite-clean、blurb-noise）：决策翻转 0、逐维 exact 1.0、严重度符号 1.0 → 完全稳定，采样随机性非不稳定来源。

## 6. 哈希与可复现命令

| 项 | sha256 |
| --- | --- |
| freeze v4 judge（rubrics_judge.py） | edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891 |
| 协议文档（不变） | ab0887b53098c37b1cf56176fe99975ab934fb7e1915ae90d174ed77b366322a |
| manifest（不变） | a3ef652c55ef9a015f12a83b18befef9076ae352f005985fa2682823b15b5d28 |
| 人类标签 human_gold.final.json | 23f5f491cdfecd4d2a14d1454dcd8e897a2f0f02c092552326baaa908968f70c |

dev 签名：model=qwen3.8-27b，judge_version=1.2.0，rubrics_version=2.0.0，max_source_chars=20000，max_output_tokens=2200，timeout_seconds=90。

```powershell
$env:PYTHONIOENCODING='utf-8'
$py = 'C:\Users\35516\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$line = Get-Content env.local -Encoding UTF8 | Where-Object { $_ -match '^QWEN_API_KEY=' } | Select-Object -First 1
$env:QWEN_API_KEY = ($line -split '=',2)[1].Trim()
& $py -m tools.amend_freeze_v4                 # freeze v3 -> v4（已执行；重跑拒绝覆盖）
.\run.cmd test                                # 361 OK
& $py -m tools.run_rubrics_judge samples\calibration_manifest.json --split development --max-source-chars 20000 --max-calls 12 --output outputs\p1_5.dev.v1.json
& $py -m tools.run_p1_probes samples\calibration_manifest.json --probe stability --max-calls 2 --output outputs\p1_5.probe.stability.v1.json
& $py -m tools.score_p1_results --batch outputs\p1_5.dev.v1.json --probe-stability outputs\p1_5.probe.stability.v1.json --freeze outputs\rubrics_judge.node3.freeze.v4.json --output outputs\p1_5.scored.v1.json --md outputs\P1_5_SCORED.md
```

产物：outputs/p1_5.smoke.v1.json、p1_5.dev.v1.json、p1_5.probe.stability.v1.json、p1_5.scored.v1.json、P1_5_SCORED.md、rubrics_judge.node3.freeze.v4.json、p1_drift_diagnostic.v1.json。

## 7. 局限（如实声明）

- 单一标注者，无 IAA；一致率 ≠ 准确率；dev 是调参集，dev ≠ 泛化。P0 最终人类标签为裁决后（偏乐观），独立锚点仍是 P0 盲评 0.75/κ0.5077。
- 残留 1 处 false_alarm（appetite-reorder）；是否系统性须 P2 扩规模 + 新 frozen_test v2 检验。
- frozen_test 永久封存、P1.5 未重跑未调参；泛化结论留 P2。
- 解耦为一般性 prompt 原则（非逐例拟合），但在 dev 上迭代验证；存在 dev 过拟合风险，须 P2 独立测试集确认。
- judge 分数在 P3 门槛达标前不作训练奖励。

## 8. 结论与后续

P1.5 以一般性解耦恢复预注册护栏（ACCEPT），拒绝率 0%、severe_miss 0、分歧 1。P1 系列（P1+P1.5）完成：judge 从 v1.0（拒绝 16.7%）经 v1.1（拒绝 8.3% 但护栏破）到 v1.2（拒绝 0%、护栏恢复）。
后续（均需用户批准）：**P2** 扩 50–100 例、分层、bootstrap CI、第二标注者 IAA、跨家族 cross-judge、新 frozen_test v2 预注册（旧永久封存）检验泛化与 appetite-reorder 残留；**P3** reward 化（门槛预注册前置）；节点5 修复闭环单独批准。

—— P1.5 验收 ACCEPT，报告交付完毕，停止。
