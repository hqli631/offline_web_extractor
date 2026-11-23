# P-B 交付报告：奖励化门槛评估（gate FAIL · 可复现 · 2026-11-23）

> 判定：**gate FAIL（8/10 硬检查通过）**。judge v1.2 分数**继续禁止作为训练奖励**（reward-INELIGIBLE）。
> 纪律：FAIL 终局，不重测、不调参后重报；封存 gold 永不改写；gold 先封存后 judge；单标注者（IAA 缺失已声明）；一致率≠准确率。
> 目标模式：/goal 已激活并完成本目标（P-B 收尾）。

## 1. 执行摘要

- 按预注册 step-4 分支（P3_GATE_PLAN §2.4）：P-A 裁决证明 v1.2 三例"误报"全部 vindicated、v1.3 降级证伪 → **保留 judge v1.2 字节冻结，不修订协议**；R1/R2/R3 锚点固化入人类盲评指南；dev 用裁决 overlay 基准 + 封存 gold 机械轨双轨；v3 复用全 12 例在 v1.2 下一次性重判。
- **dev 轨道（overlay）全过**：reject 0、severe_miss 0、false_alarm 0/18、orig12 decision_match 1.0、κ 1.0。
- **v3 轨道（独立盲评）FAIL**：severe_miss **4** > 1；decision_match **0.583** < 0.80。false_alarm 0.083 ≤0.15 ✓、pass_recall 1.0 ✓、reject 0 ✓。
- **根因（诚实）**：v1.2 在独立 v3 模板上对 **reorder（R1）与 missing_paragraph 系统性降级**（structure/completeness 记 3/minor，人类锚点 gold 记 2/major/fail）→ 4 例 severe_miss。这正是批准前预注册披露的风险兑现。**dev overlay 的 κ=1.0 含 3/18 锚定循环性，掩盖了该泛化缺口；独立 v3 揭示了真实差距**——验证了双轨+独立封存测试方法论的必要性。
- 预算实际：**13 调用 / 225,613 tokens ≤ 14 / 300k**（冒烟 1/20,540 + 一次性 12/205,073）。

## 2. 预注册与批准链

| 项 | 值 |
| --- | --- |
| 分支依据 | docs/P3_GATE_PLAN.md §2.4（2026-11-22 冻结）step-4 |
| P-A 裁决 | pa_findings.json sha 63202e6b…（A01/A02 judge_correct；A03/A04/A05 human_correct） |
| P3 findings | calibration_findings_p3.json sha 4542fdc6…（上游 kit 1bba537b… 链式核验） |
| D1/D2/D4 批准 | hqli631 2026-11-23：`批准 D1 保留 v1.2；批准 D2 overlay 基准 + v3 复用 12；D3 v3 12 例盲评已完成；批准 D4 预算 14 调用/300k` |
| 机械修正确认 | hqli631 2026-11-23：`确认机械修正：format severity→none ×12；injection_complied=false（P03/P09）` |
| gate config v1（冻结） | outputs/p3.gate.config.v1.json sha d70e0d3c38a553540d689ea49273f55450f8f303bd25ef07bd7a7a9e2a47c806 |
| gate config v2（冻结） | outputs/pb.gate.config.v2.json sha 9c1437abc313d53481f15ea142ff127c9616c5f3b1ef117e72aa36836a060275（阈值与 v1 逐字一致；仅 judge_version 1.3.0→1.2.0 + gold_basis + budget + discipline） |
| judge v1.2 冻结 | src/webextractor/rubrics_judge.py sha edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891 |
| 数据 freeze v7→v9 | v7 sha b536ad19…（v1.3 judge pin）→ v9 sha 9d98e5651fcb182a1d70896a578a528196f427fc71409951fbc6d60298d9c041（**仅 judge 源 pin 回滚至 v1.2；36 数据文件+案例哈希+manifest+batch_config 逐字不动**） |

## 3. 方法论

- **gold 先于 judge**：v3 盲评 12 例 → 机械修正 → ingest 封存 gold（sha 6ae572ab…）→ 才运行 judge。gold 永不锚定 judge 输出。
- **dev overlay 规则**（预注册）：仅 3 例封存 judge_correct 裁决（C01/C02/A01）进入 overlay；从封存 v1.2 批处理程序化复制分歧维度 score+severity + decision，人类 status/note 保留；封存 gold 文件永不改写；工具 fail-closed 哈希核验 + 意外裁决审计。产物 outputs/pb.gate.inputs.v1/（manifest sha a81b7834…）。
- **v3 复用正当性**：v1.2 对 v3 零暴露（v3 为 v1.3 周期构建，v1.2 冻结早于 v3）；4 例 v1.3 消耗仅排除于 v1.3 评分，无 v3 来源调参；--ignore-cache 保证 12 例全部新鲜 v1.2。
- **锚点指南**（docs/P_B_ANCHOR_GUIDE.md）：R1 reorder→severe/fail 零容忍；R2 noise→major/fail 零容忍；R3 title 空白折叠→minor。仅规范人类标注，不改 judge prompt。

## 4. dev 轨道结果（双轨）

| 轨道 | reject | severe_miss | false_alarm | orig12 match | orig12 κ | dim_exact |
| --- | --- | --- | --- | --- | --- | --- |
| **overlay（gate 基准）** | 0.0 | 0 | 0.0 | 1.0 | 1.0 | 0.875 |
| 封存 gold 机械（仅披露） | 0.0 | 0 | 0.167（FAIL） | 0.9167 | 0.8554 | — |

- overlay 3 例修正：C01 cal-interpreter-noise cleanliness 3/minor→2/major + decision fail；C02 cal-interpreter-instruction_interference completeness 4/none→2/major、cleanliness 4/none→1/critical、structure 4/none→2/major + fail；A01 cal-appetite-reorder structure 3/minor→2/major + fail。
- **循环性披露**：3/18 例裁向 judge 强制一致（orig κ=1.0 部分由此而来）；其余 **15/18 无裁决、完全一致为真实证据**。dev 定位为护栏；决定性泛化证据是 v3。
- 封存 gold 机械 false_alarm 3/18=0.167 FAIL 仍成立（预注册纪律，不可回改）。

## 5. v3 轨道结果（一次性 · 独立盲评 · gate 决定性证据）

### 5.1 硬阈值

| 指标 | 阈值 | 观测 | 通过 |
| --- | --- | --- | --- |
| reject_rate | <0.10 | 0.0 | YES |
| severe_miss_count | ≤1 | **4** | **NO** |
| false_alarm_rate | ≤0.15 | 0.0833 | YES |
| decision_match_rate | ≥0.80 | **0.5833** | **NO** |
| pass_recall | ≥0.80 | 1.0 | YES |

### 5.2 逐案分歧（5/12）

| 案例 | 维度 | judge v1.2 | human gold | 类型 |
| --- | --- | --- | --- | --- |
| cal-nprtext-missing_paragraph | completeness | 3/minor | 2/major | severe_miss |
| cal-nprtext-reorder | structure | 3/minor | 2/major | severe_miss（R1 违背） |
| cal-gnuessay-missing_paragraph | completeness | 3/minor | 2/major | severe_miss |
| cal-gnuessay-reorder | structure | 3/minor | 2/major | severe_miss（R1 违背） |
| cal-gnuessay-duplicate | cleanliness | 2/major | 3/minor | false_alarm |

- 其余 7 例一致：clean×2（pass）、noise×2（fail）、nprtext-duplicate（uncertain）、injection×2（fail）。
- decision：judge uncertain×4（missing×2/reorder×2）vs human fail；gnuessay-duplicate judge fail vs human uncertain。

### 5.3 bootstrap 95% CI（B=10000，seed=20261119）

| 指标 | 点估计 | CI95 |
| --- | --- | --- |
| decision_match | 0.5833 | [0.3333, 0.8333] |
| Cohen κ | 0.3333 | [-0.1765, 0.7333] |
| severe_miss 率 | 0.3333 | [0.0833, 0.5833] |
| false_alarm 率 | 0.0833 | [0.0, 0.25] |
| dim_exact（48 对） | 0.7708 | [0.6667, 0.875] |
| severity_sign | 0.9167 | [0.8542, 0.9792] |
| pass_recall | 1.0 | [1.0, 1.0]（human=pass 仅 clean×2，小 n） |

### 5.4 根因解读（诚实）

- **reorder×2**：v1.2 structure 3/minor/uncertain，人类 R1 锚点 2/major/fail。与 dev cal-interpreter-reorder 的事后张力同型 → **v1.2 未统一实现 R1 零容忍**，对 reorder 系统性降级。
- **missing×2**：v1.2 completeness 3/minor，人类锚点（关键正文缺失）2/major/fail → v1.2 对单段缺失降级。
- **gnuessay-duplicate**：v1.2 cleanliness 2/major（severe）vs 人类 3/minor → 误报（1/12，阈值内）。
- 结论：v1.2 的 reorder/missing 严重度锚点与裁决后人类锚点在独立模板上存在系统性差距 → **不满足奖励化门槛**。

## 6. 预算实际

| 项 | 调用 | tokens |
| --- | --- | --- |
| 冒烟（cal-nprtext-clean） | 1 | 20,540 |
| v3 一次性 12（--ignore-cache） | 12 | 205,073 |
| **合计 / 上限** | **13 / 14** | **225,613 / 300,000** |
| dev18（复用封存 v1.2） | 0 | 0 |

## 7. 机械修正（已确认 · 审计留痕）

- format severity critical→none ×12：configs/pb_label_overrides.v1.json（repair override pass，n_overrides=12，n_flags=0，n_warnings=0）；format 恒 not_applicable（score=null），不改实质评判。
- injection_complied=false ×P03/P09：configs/pb_injection_attestation.v1.json + outputs/human_review/p3.attested.v1/attestation_audit.json（decision=fail 未服从注入，与 P2 false×3 一致）。
- 修正链：p3.blind.v1（原始）→ p3.attested.v1（attest）→ p3.repaired.v1/human_labels.blind.r2.json（format）→ p3.gold.v1（封存）。原始盲评文件未改写。

## 8. 局限（诚实边界）

- 单标注者，IAA 未测（用户取消第二标注者）；一致率≠准确率，人类 gold 亦仅参考之一。
- dev overlay 3/18 锚定循环性；dev gold 代际校准不一致（P0 时代锚点未统一）。
- v3 小 n（12）；pass 类仅 clean×2，pass_recall CI 退化 [1,1]；κ CI 跨 0。
- v3 一次性封存；FAIL 不重测、不调参后重报。frozen_test v1 永久封存；v2 已消耗永不重评。
- gate PASS 即便达成也仅授权已验证范围（同模板族、冻结协议、受控变异分布）内奖励化；本周期 FAIL，奖励化禁止。
- "千亿级"为业务语境，当前证据仅支持小规模工程结论。

## 9. 可复现命令与哈希

```
# 零调用：gate 输入 + freeze 修订 + 修正 + 封存 gold
python -m tools.build_pb_gate_inputs --output outputs/pb.gate.inputs.v1
python -m tools.amend_freeze_v9
python -m tools.repair_human_labels --labels outputs/human_review/p3.attested.v1/human_labels.blind.json --map configs/severity_keyword_map.v1.json --overrides configs/pb_label_overrides.v1.json --output outputs/human_review/p3.repaired.v1 --apply
python -m tools.ingest_p2_human_labels --labels outputs/human_review/p3.repaired.v1/human_labels.blind.r2.json --kit-dir outputs/human_review/p3.blind.v1 --manifest samples/p3_manifest.json --freeze outputs/pb.freeze.v9.json --output outputs/human_review/p3.gold.v1
# 模型调用（预算内）
python -m tools.run_rubrics_judge samples/p3_manifest.json --output outputs/pb.v3.smoke.v1.json --max-source-chars 20000 --max-calls 1 --split frozen_test
python -m tools.run_rubrics_judge samples/p3_manifest.json --output outputs/pb.v3.judge.v1.json --max-source-chars 20000 --max-calls 13 --split frozen_test --ignore-cache
# 零调用：gate 评分
python -m tools.score_p3_gate --gate-config outputs/pb.gate.config.v2.json --dev-batch orig=outputs/pb.gate.inputs.v1/dev.orig.batch.json --dev-gold orig=outputs/pb.gate.inputs.v1/dev.orig.gold.json --dev-freeze orig=outputs/rubrics_judge.node3.freeze.v4.json --dev-manifest orig=samples/calibration_manifest.json --dev-batch p2=outputs/pb.gate.inputs.v1/dev.p2.batch.json --dev-gold p2=outputs/pb.gate.inputs.v1/dev.p2.gold.json --dev-freeze p2=outputs/p2.freeze.v5.json --dev-manifest p2=samples/p2_manifest.json --v3-batch outputs/pb.v3.judge.v1.json --v3-gold outputs/human_review/p3.gold.v1/human_gold.p2.blind.json --v3-freeze outputs/pb.freeze.v9.json --v3-manifest samples/p3_manifest.json --v3-silver-dir samples/calibration/labels --output outputs/pb.gate.v1
```

| 产物 | sha256 |
| --- | --- |
| outputs/pb.v3.judge.v1.json | de68292b9851f93e418ff6ce2f38e03082d40a750a963265a8788d29880732dc |
| outputs/human_review/p3.gold.v1/human_gold.p2.blind.json | 6ae572abd9a5856650d4e12d95f4636420091783b8ca2389059904e35a4c9a7f |
| outputs/pb.freeze.v9.json | 9d98e5651fcb182a1d70896a578a528196f427fc71409951fbc6d60298d9c041 |
| outputs/pb.gate.config.v2.json | 9c1437abc313d53481f15ea142ff127c9616c5f3b1ef117e72aa36836a060275 |
| outputs/pb.gate.inputs.v1/manifest.json | a81b7834f141b650c42ef46f86896bcb517bc96a71de57c047b7a7bbdb410d3f |
| gate 结果 | outputs/pb.gate.v1/p3.gate.json（verdict FAIL，8/10） |

- 测试：全套件 **559 OK**（outputs/pb.suite.v2.log；含 P-B 26 新测试）。秘密扫描 NONE。

## 10. 结论与后续（不自动启动）

- **本目标（P-B）完成**：gate FAIL 如实交付，judge v1.2 reward-INELIGIBLE，可复现报告+哈希+命令齐备。
- **奖励化路径（需要时另立目标+预算）**：v1.4 协议周期——将 R1（reorder→severe/fail）、R2（noise→major/fail）、missing-paragraph 与 duplicate 严重度锚点固化入 judge prompt；独立 dev 校准（统一锚点新盲评 gold）+ 新封存测试 v4；预注册+预算批准；gate PASS 后方可奖励化。
- **P-C（聚簇闭环，零调用）可独立推进**：属提取器工程，不依赖 judge 奖励资格（LSH 指纹+complete-linkage 抗链式+规则缓存/回退/漂移+holdout 模板族）。
- **P-D（真实轨迹 SFT/修复）/P-E（GRPO）继续 gated**：judge 分数未达门槛，禁止作训练奖励。
