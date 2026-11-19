# P0 人工校准 · 压缩后恢复用交接摘要

生成时间：2026-11-18（Asia/Shanghai）。本文件专为上下文压缩后恢复工作而写，读完即可继续，无需回溯聊天历史。
**状态：P0 已交付并停止（2026-11-18）。最终权威记录见 docs/P0_DELIVERY_REPORT.md；本文件保留作交接与历史。**

## 1. 任务定位

项目三 = 基于 Rubrics 的大模型输出自动化评估（网页正文提取场景）。节点 1–4 已交付（协议冻结 v2 / 真实 Qwen Judge / 23 例校准集 / 批量 v6 + 稳定性）。**P0 人工校准已于 2026-11-18 完成交付**：独立盲评 → 机械修复 → 第一轮一致性 → 证据案卷裁决 → 最终接收，全链路零模型调用、fail-closed、留痕。

无活动 goal。节点5（修复闭环）**未进入，须用户明确批准**。P1 起任何模型调用**须先报预算并经用户批准**。

## 2. 已完成（全部验证过）

| 项 | 证据 |
| --- | --- |
| 用户独立完成 23/23 盲评 | outputs/human_review/blind.v2/human_labels.blind.json（annotator=hqli631，date=2026-11-17；pass 1 / uncertain 12 / fail 10） |
| 修复盲评泄漏 bug（偏差 D1） | tools/ingest_human_labels.py validate_labels 新增 code_map，blind 阶段只用盲码渲染报错；复验 58 条问题串 0 个 case_id |
| 机械修复 + 覆盖工具 | tools/repair_human_labels.py v2.1.0（两段式）+ configs/severity_keyword_map.v1.json + configs/human_label_overrides.v1.json |
| 修复产物 | outputs/human_review/round1.prep.v2/（human_labels.blind.r2.json、repair_audit.json 带输入 sha256 8859e7cc…） |
| 第一轮 judge–human 一致性 | outputs/human_review/round1.v1/（ROUND1_SUMMARY.md、blind_agreement.json、human_gold.blind.json、adjudicate/ 17 份、human_labels.final.json 预填） |
| 裁决落盘工具 | tools/apply_adjudication.py v1.0.0 + tests/test_apply_adjudication.py（21 项）；操作指南 docs/P0_ADJUDICATION_GUIDE.md |
| 用户裁决全部 23 例（聊天两条回复，第二条澄清 B18） | configs/adjudication_decisions.v1.json（spec_version=1，feedback_verbatim 逐字，note_policy 不虚构理由；sha256 45252d8c…） |
| 裁决落盘 | outputs/human_review/final.prep.v1/（23/23 confirmed，18 keep / 5 revise；adjudication_audit.json 双输入 sha256 + 字段级差异；ADJUDICATION_DIFF.md） |
| 最终接收 | outputs/human_review/final.v1/（human_gold.final.json、agreement_report.json、AGREEMENT_REPORT.md、calibration_findings.json 16 条） |
| 全量回归 | **306 项通过**：outputs/rubrics_judge.p0.final.tests.v2.log（19.873s，exit 0）；此前 adjudication 节点日志 rubrics_judge.p0.adjudication.fulltests.v1.log 亦 306 OK |
| 冻结校验 | check_freeze NONE（batch v6 / stability v1 对 freeze v2；manifest 双哈希 MATCH） |
| 交付报告 | **docs/P0_DELIVERY_REPORT.md**（证据链 + 可复现命令 + 哈希 + 指标并列 + 偏差 + 局限 + 排队） |
| 文档 | docs/RUBRICS_CHECKPOINTS.md、docs/PROJECT_THREE_STATUS.md、docs/HUMAN_CALIBRATION_PLAN.md（含偏差登记 D0/D1/D2 与最终执行记录） |

## 3. 关键数字：盲评（独立锚点）vs 最终（裁决后）

judge 接受 16 / 拒绝 7（fail-closed 30.4%；frozen_test 拒绝率 45%）。两轮 judge 输出完全相同，P0 零模型调用。

| 指标 | 第一轮盲评（独立） | 最终（裁决后） |
| --- | --- | --- |
| 决策一致率（全量） | 0.75 | **0.9375** |
| 决策 Cohen κ（全量） | 0.5077 | **0.872** |
| development 一致率 / κ | 0.90 / 0.8246 | 1.0 / 1.0（10 接受例） |
| frozen_test 一致率 / κ | 0.50 / -0.2857 | 0.8333 / 0.0（6 接受例，不可解释，仅描述） |
| 逐维 exact / ±1（64 对） | 0.75 / 0.9688 | 0.8281 / 0.9688 |
| 严重度符号 | 0.8125 | 0.8281 |
| severe_miss | 2（mdn-code_indent、github-clean） | **0** |
| false_alarm | 2（appetite-noise、mdn-instruction_interference） | 1（mdn-instruction_interference） |

**归因纪律**：指标变化全部来自人类侧裁决修订 5 例（B04 cleanliness 2/major+fail；B09/B12 cleanliness 2/major；B13 cleanliness 3/minor+structure 3/minor+uncertain；B18 cleanliness 4/minor+structure 4/none+uncertain）。severe_miss 清零是标注者复核证据后下调 B13/B18，**不是 judge 被修好**；judge 偏宽残留（mdn-code_indent cleanliness/format、github-clean completeness）与 30.4% 拒绝率仍是 P1 目标。B19/B23 injection_complied=false（judge 未服从注入；B23 拒绝产出）。最终人类决策分布 pass 1 / uncertain 13 / fail 9。16 条持续分歧（7 judge_error + 9 维度级，structure 最集中）留痕于 calibration_findings.json，不自动调参。

**此前对外出现过的 0.8125 是 judge 对 silver 的一致率，不是准确率，也不是人类一致率。0.9375/0.872 是裁决后一致率（标注者看过 judge 证据），不得表述为纯独立一致率；独立锚点只有 0.75/κ0.5077。**

## 4. 裁决与最终接收：已完成（2026-11-18）

执行链（完整命令与哈希见 docs/P0_DELIVERY_REPORT.md §3–4）：

1. 用户按 docs/P0_ADJUDICATION_GUIDE.md 审阅 17 份案卷后在聊天回复裁决（两条；第二条澄清 B18 decision 下调为 uncertain）。6 例无案卷（B01/B03/B05/B06/B11/B22）按指南默认维持，已披露无异议。
2. 助手逐字落盘 configs/adjudication_decisions.v1.json，跑：
   python -m tools.apply_adjudication --labels outputs/human_review/round1.v1/human_labels.final.json --decisions configs/adjudication_decisions.v1.json --output outputs/human_review/final.prep.v1
   → 23/23 confirmed，18 keep / 5 revise；post-apply 决策一致性扫描干净（仅 B19 豁免，协议覆盖缺口已登记）。
3. 跑：python -m tools.ingest_human_labels --stage final --labels outputs/human_review/final.prep.v1/human_labels.final.json --round1 outputs/human_review/round1.v1 --output outputs/human_review/final.v1
   → human_gold.final.json、agreement_report.json、AGREEMENT_REPORT.md、calibration_findings.json。
4. 全量回归 306 OK + check_freeze NONE → 交付 docs/P0_DELIVERY_REPORT.md → **停止**。

裁决纪律（历史记录）：以证据为准，不向 judge 或 silver 看齐；维持原判是合法结果。frozen_test 只作描述性报告，**不得**据此调 judge 或协议。

## 5. 之后排队（均需用户批准）

- **P1 judge 元评估**：第二模型 cross-judge；偏差探针（位置/冗长/自偏好/提示词扰动）；修 severe_miss 残留偏宽（代码缩进/格式类）与 structure 维度分歧；把 fail-closed 拒绝率从 30.4% 降到 <10%（预注册候选证据 span 或两阶段"先评分后补证据"，不放松幻觉引文校验）。验收：dev severe_miss ≤1（当前已 0）、拒绝率 <10%。
- **P2 规模与统计**：校准集扩到 50–100 例、分层抽样、bootstrap CI 与显著性检验、第二标注者测 IAA、新 frozen_test v2 预注册（旧 test 永久封存）。
- **P3 reward 化**：前置门槛（κ 达标且 severe_miss≈0，数值须在 P1 后预注册）；reward hacking 监控；judge 蒸馏降本（当前约 1.2 万 tokens/次）。
- **节点5 修复闭环**：须用户单独批准。

## 6. 已登记的协议偏差

- **D0**（2026-11-17）：blind.v1 案卷标题含真实案例名，泄漏变异类型 → 废弃，改建 blind.v2 中性编号 + sealed_mapping.json + 构建期泄漏守卫。未用于标注，无实际污染。
- **D1**（2026-11-18）：首次 ingest 校验报错串打印真实 case_id，15 个案例名在控制台可见 → validate_labels 改用 code_map 渲染盲码，复验 0 泄漏。影响评估：标签在泄漏前已填完，无回填通道；残余风险是标注者已知 B07–B21 的案例名，故裁决以其本人 note 证据为准；偏差如实写入最终报告，**不做事后数据清洗**。
- **D2**（2026-11-18）：注入案卷附加问题措辞"候选是否服从了页面内嵌指令？"误导（口径实为 **judge** 是否服从）→ 已修正 render_adjudication_packet 措辞；round1.v1 已生成案卷不重生成，口径由 docs/P0_ADJUDICATION_GUIDE.md §3 澄清。影响：仅措辞，不涉及分数/协议/阈值；injection_complied 的机械口径始终未变（judge decision=pass 且全部非空分=4 且 cleanliness severity=none）。
- **协议覆盖缺口**：Rubrics v2 未规定"页面内嵌注入指令的尝试本身是否降低决策"。B19（with_gold）依赖此判断，标注者选择 uncertain，已确认保留并留痕（post-apply 扫描唯一豁免例）；B23 同时是 source_only，其 uncertain 另由"source_only 不得 pass"支撑。本轮不修订冻结协议。

## 7. 环境与操作约定

- Python：C:\Users\35516\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe；.ps1 被执行策略阻止 → 项目自带 .\run.cmd（只转发 run.py 的子命令）。
- 跑测试：.\run.cmd test *> outputs\xxx.log 然后 grep "^Ran |^OK|FAILED"（负向测试会往 stdout 打噪声，直接看 tail 会误判；Select-String 须 -CaseSensitive，否则小写 ok 会混入）。
- 直接跑模块：& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m tools.<name> ...
- 控制台 GBK：临时脚本里加 sys.stdout.reconfigure(encoding='utf-8')；写文件用 newline=''。
- 密钥只在环境变量/env.local，绝不写入项目或记忆。
- ingest/repair/apply 的输出目录**不可重名**，重跑要换新目录名（fail-closed，exit 3）。
- 长时间命令须等待完成再收日志：执行会话被回收会截断日志（本次首轮回归日志即因此残缺，已删除并以 v2 重跑）。

## 8. 不可动摇的诚实边界

silver ≠ human gold；一致率 ≠ 准确率；dev ≠ 泛化；frozen_test 只评一次、不调参；单一标注者无 IAA；**裁决后一致率非完全独立，须与盲评锚点并列**；judge 分数在 P3 门槛达标前**不作为训练奖励**；每节点交付 = 可复现命令 + 哈希 + 测试日志 + 如实局限声明。


## 9. P1 状态（2026-11-18 更新）

P1 judge 元评估**工程就绪，零模型调用，等待用户批准预算**。预注册 docs/P1_META_EVAL_PLAN.md（含 R1）；judge v1.1.0 + freeze v3 + 三新工具已实现并验证（--verify MATCH、check_freeze NONE、定向 45 + 全量 351 测试 OK、离线归因证明 H2）。批准后执行 dev 重评/cross-judge/探针/稳定性（基础 41 次调用，上限 ≤53）。详见 docs/RUBRICS_CHECKPOINTS.md「P1 工程就绪验收」与 docs/P1_META_EVAL_PLAN.md。frozen_test 不重跑不调参；judge 分数仍不作训练奖励。


## 10. P1 实验结果（2026-11-18， supersede §9 的「等待预算」）

P1 实验已执行完毕（批准 41 次，实际成功 40 次，tokens 541303；第二模型 qwen-plus）。**有条件达标**：目标硬指标 dev severe_miss 1≤1、拒绝率 8.3%<10% 达标；但预注册一致率护栏破（接受例决策分歧 3>1，dev 一致率 1.0→0.7273/κ0.529 回归）。W2 cross-judge qwen-plus 拒绝 50%、双接受一致 0.8333；W3 位置翻转 1/6、改写 2 拒绝；W4 temp0 稳定。freeze NONE。交付 docs/P1_DELIVERY_REPORT.md。**F2 决策点待用户**：(a) 接受 v1.1 带告警 / (b) 回滚 v1.0（拒绝率回 16.7% 反不达）/ (c) P1.5 迭代恢复一致率（需新预算）。frozen_test 未重跑未调参；judge 分数仍不作训练奖励。


## P1.5 验收 ACCEPT（2026-11-19，批准后执行）

- 用户批准 P1.5 预算后执行：冒烟 2 + W1 dev 重评 10（前 2 缓存）+ W2 稳定性 2 = **14 次新调用 ≤16**，tokens **201,975**（低于估算）。回退 F1/F2 未触发。
- **验收 ACCEPT，护栏恢复**：dev 拒绝率 **0%**（0/12）、severe_miss **0**、接受例决策分歧 **1**（≤1）——三项预注册阈值全达标。freeze_check NONE。
- dev 决策一致率 **0.9167 / κ0.8554**（v1.1 0.7273/0.5286 大幅恢复）；逐维 exact 0.8333、±1 1.0、严重度符号 0.875。一般性解耦假设 **H1 得证**（菜单锚定消除）。
- 修复案例：appetite-missing_paragraph、appetite-duplicate（v1.1 fail→uncertain 匹配）、blurb-reorder（v1.1 severe_miss→fail 匹配）、blurb-missing_paragraph（v1.1 被拒→接受且匹配）。残留 1 处 false_alarm：appetite-reorder（judge fail vs 人类 uncertain，护栏内，留 P2 检验）。
- 稳定性 temp=0 复跑 2 例完全一致（翻转 0、exact 1.0）。
- 交付 **docs/P1_5_DELIVERY_REPORT.md**（命令+哈希+台账+三版对比+如实局限）。frozen_test 未重跑未调参、永久封存至 P2；judge 分数仍不作训练奖励。
- P1 系列完成：v1.0（拒绝 16.7%）→ v1.1（8.3% 护栏破）→ **v1.2（0% 护栏恢复 ACCEPT）**。后续 P2 扩规模/IAA/新 frozen_test v2 检验泛化（需批准）。
