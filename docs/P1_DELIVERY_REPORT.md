# P1 Judge 元评估 · 交付报告

日期：2026-11-18（Asia/Shanghai）。项目三 offline_web_extractor。
状态：**实验全部完成；验收为「有条件达标」——目标硬指标达标，但预注册一致率护栏破，F2 处置待用户决策。**
预注册：docs/P1_META_EVAL_PLAN.md（含修订 R1，调用前固定，用户批准「全部 41 次」）。

---

## 1. 执行摘要（诚实结论）

- **目标 item4 硬指标达标**：development severe_miss = 1（≤1 ✓）；fail-closed 拒绝率 = 8.3%（1/12，<10% ✓）。拒绝率修复有效（P0 时 dev 16.7% → 8.3%）。
- **但预注册护栏破**：接受例决策分歧 = 3（护栏 ≤1 ✗）。dev 决策一致率从 P0 最终（judge v1.0）的 **1.0 / κ1.0 回归到 0.7273 / κ0.5286**；severe_miss 0→1，false_alarm 0→2。
- **归因**：证据菜单 + 空白折叠修复了引文合规（拒绝率下降），但同时扰动了部分接受例的评分行为，使 3 例决策偏离 P0 最终人类标签。这是「拒绝率↓」与「决策一致率↓」的真实权衡，**不静默丢弃护栏**。
- **F2 决策点**：预注册 F2 规定护栏破→回滚 v1.0；但回滚会使拒绝率回到 16.7%（>10%，目标硬指标反而不达）。两者冲突，须用户定夺（§9）：接受 v1.1 带告警 / F2 回滚 / P1.5 迭代恢复一致率。
- cross-judge（qwen-plus）与偏差/稳定性探针均描述性完成；frozen_test 全程未重跑、未调参、永久封存至 P2。

## 2. 工程交付（零调用阶段，已验证）

- judge **v1.1.0**（仅改 src/webextractor/rubrics_judge.py）：① 各维度证据菜单（精确 registry 前缀 {ref,quote}，确定性、无标签、预算自适应 quote 前缀 {120,60,30}）；② 引文空白折叠匹配（折叠所有空白 run 后精确子串，非空白字符逐字有序，**幻觉防护不放松**）；③ 探针扰动参数 source_order_seed/dimension_phrasing（默认 None 生产 prompt 逐字节不变）。
- freeze **v3**（outputs/rubrics_judge.node3.freeze.v3.json）：代码仅 rubrics_judge.py 变更；23 silver 标签仅刷新 prompt_chars 诊断（逐字段证明评分内容不变）；候选/gold/manifest/源页/协议文档/rubrics_v2/构建器/batch_config 哈希不变。build_calibration_set --verify v3 = **MATCH**；check_freeze 历史 batch v6 对 v3 = **NONE**。
- 新工具：tools/amend_freeze_v3.py、tools/run_p1_probes.py、tools/score_p1_results.py；运行器 --split dev-only 过滤 + probe 透传。
- 测试：定向 45 项 + 全量回归 **351 项 OK**（outputs/rubrics_judge.p1.engineering.tests.v2.log，27.574s）；验收管线端到端验证。
- 离线归因（outputs/p1_offline_attribution.v1.json，零调用）：v1.1 校验器重放 v1.0 缓存拒绝响应，cal-blurb-missing_paragraph（模式2 空白转录）被接受 → **H2 得证**；6 例模式1 需菜单 prompt 变更（ live 重评验证）。

## 3. 实际调用台账（批准后执行）

| 工作包 | 模型 | 新调用 | tokens |
| --- | --- | --- | --- |
| 冒烟 | qwen3.8-27b | 2 | 29,659 |
| W1 dev 重评 | qwen3.8-27b | 10（前 2 命中冒烟缓存） | 138,076 |
| W2 cross-judge | qwen-plus | 12 | 173,118 |
| W3 位置扰动 | qwen3.8-27b | 6 | 84,484 |
| W3 中性改写 | qwen3.8-27b | 6 | 84,406 |
| W4 稳定性 | qwen3.8-27b | 2 | 31,560 |
| **报告小计** | | **38** | **541,303** |

- 另有模型可用性 ping：qwen-plus 200、qwen3.8-flash 200（2 次成功，tokens 极小）；qwen-max 403（免费额度耗尽）×2、qwen-turbo 429（限流）×1 共 3 次失败（不计费）。
- **成功生成调用合计 40 次 ≤ 批准 41；总尝试 43 次 ≤ 上限 53。** 报告计量 tokens 541,303（input 515,913 / output 25,390）。
- 第二模型选定 **qwen-plus**（预注册回退选项；qwen-max 免费额度耗尽 403 不可用）。同 DashScope 家族不同模型线，自偏好覆盖有限（如实声明）。
- 密钥经 env.local 的 QWEN_API_KEY 加载到进程环境，全程未打印、未入库。早期阻塞为该 key 无效（401），用户更新后 200 生效。

## 4. W1 development 验收（对照 P0 最终人类标签 human_gold.final.json）

验收阈值（预注册）：拒绝率 <10%、severe_miss ≤1、接受例决策分歧 ≤1。

| 检查 | 结果 | 判定 |
| --- | --- | --- |
| 拒绝率 <10% | 8.3%（1/12） | ✓ |
| severe_miss ≤1 | 1（cal-blurb-reorder） | ✓ |
| 接受例决策分歧 ≤1 | 3 | ✗ |
| **综合 verdict** | | **REJECT（护栏破）** |

freeze_check = NONE。dev 决策一致率 0.7273（8/11），κ 0.5286；false_alarm 2（appetite-missing_paragraph、appetite-duplicate）。

逐案（judge v1.1 vs 人类最终）：

| 案例 | judge | 人类 | 备注 |
| --- | --- | --- | --- |
| cal-appetite-clean | pass | pass | match |
| cal-appetite-missing_paragraph | fail | uncertain | **MISMATCH + false_alarm** |
| cal-appetite-noise | fail | fail | match |
| cal-appetite-duplicate | fail | uncertain | **MISMATCH + false_alarm**（v1.0 时此例被拒，v1.1 新接受却分歧） |
| cal-appetite-reorder | uncertain | uncertain | match |
| cal-appetite-title_number | uncertain | uncertain | match |
| cal-blurb-clean | uncertain | uncertain | match |
| cal-blurb-missing_paragraph | REJECTED | fail | 模式1（缺 s:/g: 引用；node4 时为模式2 空白转录） |
| cal-blurb-noise | fail | fail | match |
| cal-blurb-reorder | uncertain | fail | **MISMATCH + severe_miss** |
| cal-iana-clean | uncertain | uncertain | match |
| cal-iana-noise | fail | fail | match |

相对 P0 最终 dev（judge v1.0）的回归：

| 指标 | P0 最终 dev (v1.0) | P1 dev (v1.1) |
| --- | --- | --- |
| 接受 / 拒绝 | 10 / 2（16.7%） | 11 / 1（8.3%） |
| 决策一致率 | 1.0 | 0.7273 |
| Cohen κ | 1.0 | 0.5286 |
| severe_miss | 0 | 1 |
| false_alarm | 0 | 2 |

**解读**：拒绝率改善真实（H1 菜单 + H2 折叠使引文合规提升）；但 dev 决策一致率回归亦真实。注意 P0 最终 dev 1.0 是裁决后一致率（标注者看过 judge 证据），本身偏乐观；v1.1 的 0.7273 是同一人类标签下的新 judge 行为。两者均非独立泛化准确率。blurb 拒绝原因从模式2 转模式1，说明菜单未完全消除该例的 s:/g: 引用缺失。

## 5. W2 cross-judge（描述性，无验收阈值）

qwen3.8-27b（judge1）vs qwen-plus（judge2），同 v1.1 协议，12 dev 例：
- judge2（qwen-plus）拒绝 **6/12 = 50%**（远高于 judge1 的 8.3%）→ 模型特异性合规差异显著。
- 双方均接受 6 例：决策一致 0.8333（5/6），κ 0.6667；逐维 exact 0.8333、±1 0.9583；严重度符号 0.8333。
- 分歧例：cal-appetite-duplicate（judge1 fail vs judge2 pass，false_alarm）。
- 结论：judge 间存在实质分歧与模型特异性偏宽/偏严；单 judge 分数不可视为模型无关真值。同家族限制见 §8。

## 6. W3/W4 偏差与稳定性探针（描述性，无验收阈值）

| 探针 | 可比案例 | 决策翻转率 | 逐维 exact | 严重度符号 |
| --- | --- | --- | --- | --- |
| 位置扰动（seed=20261118） | 6 | 0.1667（1/6，appetite-duplicate fail→uncertain） | 0.875 | 0.9167 |
| 中性改写（neutral_v1） | 4（2 例被拒） | 0.0 | 1.0 | 1.0 |
| 稳定性（temp=0 复跑） | 2 | 0.0 | 1.0 | 1.0 |

- 位置扰动引起 1 例决策翻转 + 逐维漂移 → judge 对证据呈现顺序有一定敏感。
- 中性改写使 appetite-noise、iana-noise 新被拒（接受例内决策/维度稳定）→ 提示词措辞影响合规率。
- temp=0 复跑完全稳定（决策与逐维一致）→ 采样随机性非不稳定来源；不稳定来自 prompt 敏感而非温度。

## 7. 哈希与可复现命令

| 项 | sha256 |
| --- | --- |
| freeze v3 judge（src/webextractor/rubrics_judge.py） | cc649504b82832001c2f9a8c41f79e53a4006cec60914a22a5adc1cfb23a240e |
| 协议文档 docs/RUBRICS_V2_PROTOCOL.md（不变） | ab0887b53098c37b1cf56176fe99975ab934fb7e1915ae90d174ed77b366322a |
| src/webextractor/rubrics_v2.py（不变） | 4fa60e024758e67d8c831b7a34e267bf2ce9a143dd6ae70cdbc94da036560364 |
| samples/calibration_manifest.json（不变） | a3ef652c55ef9a015f12a83b18befef9076ae352f005985fa2682823b15b5d28 |
| 人类标签 human_gold.final.json | 23f5f491cdfecd4d2a14d1454dcd8e897a2f0f02c092552326baaa908968f70c |

dev 批量签名：model=qwen3.8-27b，judge_version=1.1.0，rubrics_version=2.0.0，max_source_chars=20000，max_output_tokens=2200，timeout_seconds=90。

命令链（密钥经 env.local 加载到 $env:QWEN_API_KEY；输出拒绝重名，复现换新名）：

```powershell
$env:PYTHONIOENCODING='utf-8'
$py = 'C:\Users\35516\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$line = Get-Content env.local -Encoding UTF8 | Where-Object { $_ -match '^QWEN_API_KEY=' } | Select-Object -First 1
$env:QWEN_API_KEY = ($line -split '=',2)[1].Trim()
# 工程（零调用）
& $py -m tools.amend_freeze_v3                 # freeze v2 -> v3（已执行；重跑拒绝覆盖）
.\run.cmd test                                # 351 OK
# W1 dev 重评
& $py -m tools.run_rubrics_judge samples\calibration_manifest.json --split development --max-source-chars 20000 --max-calls 12 --output outputs\p1.dev.v1.json
# W2 cross-judge
& $py -m tools.run_rubrics_judge samples\calibration_manifest.json --split development --model qwen-plus --max-source-chars 20000 --max-calls 12 --output outputs\p1.cross.v1.json
# W3/W4 探针
& $py -m tools.run_p1_probes samples\calibration_manifest.json --probe position --max-calls 6 --output outputs\p1.probe.position.v1.json
& $py -m tools.run_p1_probes samples\calibration_manifest.json --probe phrasing --max-calls 6 --output outputs\p1.probe.phrasing.v1.json
& $py -m tools.run_p1_probes samples\calibration_manifest.json --probe stability --max-calls 2 --output outputs\p1.probe.stability.v1.json
# 汇总验收
& $py -m tools.score_p1_results --batch outputs\p1.dev.v1.json --cross outputs\p1.cross.v1.json --probe-position outputs\p1.probe.position.v1.json --probe-phrasing outputs\p1.probe.phrasing.v1.json --probe-stability outputs\p1.probe.stability.v1.json --output outputs\p1.scored.v1.json --md outputs\P1_SCORED.md
```

产物：outputs/p1.smoke.v2.json、p1.dev.v1.json、p1.cross.v1.json、p1.probe.{position,phrasing,stability}.v1.json、p1.scored.v1.json、P1_SCORED.md、p1.acceptance.v1.json、p1_offline_attribution.v1.json、rubrics_judge.node3.freeze.v3.json。

## 8. 偏差与局限（如实声明）

- **核心：预注册一致率护栏破（3 分歧），dev 决策一致率回归 1.0→0.7273。** 拒绝率达标与一致率回归并存；F2 处置待用户决策（§9）。本报告不声称干净通过。
- 单一标注者，无 IAA；一致率 ≠ 准确率；dev ≠ 泛化。P0 最终 dev 1.0 为裁决后一致率（偏乐观），独立锚点仍是 P0 盲评 0.75/κ0.5077。
- frozen_test 全程未重跑、未调参、永久封存至 P2 新预注册测试集。
- cross-judge 为同 DashScope 家族（qwen3.8-27b vs qwen-plus），自偏好偏差覆盖有限；跨家族留 P2。qwen-plus 拒绝率 50% 表明合规率模型依赖强。
- 位置扰动致 1 例决策翻转、中性改写致 2 例新拒绝 → judge 对 prompt 呈现/措辞敏感；temp=0 复跑稳定。
- 菜单预算自适应使 mdn（frozen_test）quote 前缀修剪至 30；dev 全 120。silver 标签 prompt_chars 诊断刷新（评分内容证明不变）。
- judge 分数在 P3 门槛达标前**不作为训练奖励**。

## 9. F2 决策点（待用户定夺）

预注册 F2：护栏破→回滚 v1.0、P1 记未达标。但回滚使拒绝率回 16.7%（>10%），目标硬指标反不达。选项：

- **(a) 接受 v1.1 为 P1 基线（带告警）**：目标硬指标达标（severe_miss 1、拒绝 8.3%），但携一致率回归告警（0.7273/κ0.529，3 分歧）。适合「优先降拒绝率、一致率留 P1.5/P2 恢复」。需用户明确豁免预注册护栏。
- **(b) 履行 F2 回滚 v1.0**：恢复 P0 决策一致率（dev 1.0），但拒绝率回 16.7%（目标硬指标不达），P1 记未达标；探针证据仍描述性保留。
- **(c) P1.5 迭代**：在 v1.1 基础上预注册针对性改进（如菜单引用强约束/两阶段补证据修模式1、抑制 false_alarm 的严重度校准），目标同时满足拒绝率 <10% 与一致率护栏；需新预注册 + 新预算批准。

助手建议：(c) 最对齐「可信自动评估」终态（拒绝率与一致率都要），但需追加预算；若预算受限，(a) 带告警接受 + P2 恢复一致率次之；(b) 牺牲拒绝率修复，最不推荐。**请用户选择。**

## 10. 后续排队（均需用户批准）

- P1.5（若选 c）：预注册迭代恢复一致率。
- P2：扩 50–100 例、分层、bootstrap CI、第二标注者 IAA、跨家族 cross-judge、新 frozen_test v2 预注册（旧永久封存）。
- P3：reward 化（κ/severe_miss 门槛预注册前置）、reward hacking 监控、judge 蒸馏降本。
- 节点5 修复闭环：单独批准。

—— P1 实验与报告交付完毕；验收为有条件达标，F2 处置待用户决策后停止。
