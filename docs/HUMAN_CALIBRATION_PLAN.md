# 项目三 P0–P3 推进计划：Rubrics 自动化评估的可信度建设

日期：2026-11-17。前置：节点1–4已完成并冻结（docs/RUBRICS_JUDGE_REPORT.md）。本计划不修改已冻结的协议、校准数据与批量配置；任何协议变更必须走冻结修订流程。

## 角色分工

- 助手：工具链建设与维护、校验、指标计算、报告撰写、P1 起的工程改进与元评估实验。
- 用户：独立人工标注（盲评与裁决）、按要求回传结果、审批模型调用预算与关键决策。
- 红线：人类标签必须由用户真实审阅产生；助手不得代填、预填或暗示分数。

## P0 人工校准（当前启动，零模型调用）

目标：把"对 silver 的一致率"升级为"对人类的一致率"，产出 23 例 human gold 与 judge–human Cohen κ，为 judge 可信度提供第一份人类参照。

方法学：
- 两阶段：盲评（只看任务输入，独立打分）→ 裁决（解锁 judge/silver/程序分数与变异信息，逐分歧裁决，允许维持或修改）。
- 防泄漏：案卷用中性编号 B01–B23，隐藏真实案例名与变异类型；编号映射密封于 sealed_mapping.json，盲评阶段禁止打开。
- 单一标注者：报告如实注明无标注者间一致性（IAA）；可选加强项为第二人独立复核至少 6 例。
- frozen_test 的人类标签仅作描述性报告，不得用于调 judge/协议后重报。

已交付工具链（2026-11-17，定向 21 项测试 + 全量 208 项通过，outputs/rubrics_judge.p0.tests.v1.log）：
- tools/build_human_review_kit.py：盲评工具包构建器。冻结 fail-closed、确定性字节输出、案卷防泄漏守卫（真实案例名出现即报错）。
- tools/ingest_human_labels.py：两阶段接收器。blind 阶段解析密封编号、全量 schema 校验、快照 human gold（label_origin=human）、计算 κ/逐维一致/severe_miss/false_alarm、生成分歧裁决案卷与预填 final 模板；final 阶段要求逐例 confirmed=true，产出最终一致性报告与持续分歧清单（calibration_findings.json，供 P1 使用，不自动调参）。
- outputs/human_review/blind.v2/：23 份案卷（dev 12 / frozen_test 11）+ human_labels.blind.json 模板 + sealed_mapping.json + INDEX.md。防泄漏扫描 CLEAN。
- outputs/human_review/blind.v1/：已废弃（案例 ID 泄漏变异类型），仅留历史，禁止使用。

用户操作（详见 blind.v2/INDEX.md）：
1. 会话1：阅读 packets/B01–B12.md，在 human_labels.blind.json 填写对应条目（decision + 五维 score/status/severity）。
2. 会话2：B13–B23 同上。先填 annotator 与 annotation_date（YYYY-MM-DD）。
3. 填完运行（项目根目录）：
   python -m tools.ingest_human_labels --stage blind --labels outputs/human_review/blind.v2/human_labels.blind.json --output outputs/human_review/round1.v1
   或直接把填好的 json 发回给助手代跑。校验失败会列出全部错误，修正后重跑（输出目录换新名）。
4. 收到 round1 后：阅读 adjudicate/ 裁决案卷，在 human_labels.final.json 逐例裁决并 confirmed=true，运行 --stage final（或发回助手代跑）。

P0 验收：human_gold.final.json 生成；AGREEMENT_REPORT.md 含决策一致率、Cohen κ、逐维 exact/±1、严重度符号、severe_miss/false_alarm，分 split 报告；持续分歧入 calibration_findings.json。

## P1 Judge 元评估与偏差修正（待 P0 完成，需审批调用预算）

1. 第二模型 cross-judge：同案卷同协议，量化 judge 间一致率，识别模型特异性偏差。
2. 偏差测试：偏宽（针对 P0 确认的 severe_miss 类型）、冗长偏好、证据位置扰动、提示词扰动鲁棒性。
3. 降 fail-closed 拒绝率（当前 30.4%）：为 cleanliness/structure 预注册候选证据 span 或两阶段"先评分后补证据"；不放松幻觉引文校验。
验收：偏差测试报告；dev 上 severe_miss ≤1；拒绝率 <10%；任何协议/提示词变更走冻结修订并保留旧版历史。frozen_test 不参与调参。

## P2 规模扩展与统计强化（待 P1 达标）

- 校准集扩至 50–100 例：更多版式、错误类型与真实提取失败案例；分层抽样。
- bootstrap 置信区间与显著性检验；新 frozen_test v2 预注册（旧 test 永久封存）。
- 节点5修复闭环（需用户单独批准）：Critic 反馈→限定次数修复→再评估，带无修复对照，test/gold 不回传。

## P3 训练集成与通用化（远期，门槛前置）

- 前置门槛（P0/P1 后预注册具体数值）：judge–human 决策 κ 达标且 severe_miss≈0，否则不得 reward 化。
- Rubrics→SFT 偏好数据筛选/RL reward；reward hacking 监控（长度/格式钻营）+ held-out 人工抽检。
- 多任务 rubrics 模板库、CI 质量门禁、judge 蒸馏降本（当前约 1.2 万 tokens/次）。

## 预算与诚实边界

- P0 零模型调用；P1 起每次实验前先报预算（调用数×估算 tokens）经用户批准。
- 一致率≠准确率；单标注者≠多人金标；dev≠泛化；judge 分数在 P3 门槛达标前不作为训练奖励。
- 每节点交付：可复现命令 + 哈希 + 测试日志 + 如实局限声明。


## P0 执行记录（滚动更新）

### 2026-11-18 · 第一轮盲评回收

- 进度：23/23 已由标注者独立完成（annotator=hqli631，annotation_date=2026-11-17）；decision 分布 pass 1 / uncertain 12 / fail 10；零模型调用。
- 阻塞：58 个维度把 status 取值 partial 误填进 severity 列，ingest 校验 fail-closed 拒绝，未产出 human gold。score/decision/note 均有效，无需重标。
- 机械修复通道：tools/repair_human_labels.py + configs/severity_keyword_map.v1.json（映射版本 1，可审计、可回滚）。硬约束：只读标签文件与关键词映射；不读批量报告、judge 输出、metrics、silver 标签、sealed_mapping.json；输出不含真实 case_id（测试断言）；score/decision/note/overall_note 原样保留；已合法 severity 一律不动；原标签文件永不覆盖；产出 repair_audit.json 含输入 sha256。
- severity 推导只使用**标注者本人 note 文本** + 冻结的 Rubrics v2 严重度锚点，属机械列位修复，不构成助手代标。任何推导结果都须标注者确认后才进入 gold。
- 进入下一轮的门槛（须标注者逐项确认）：
  1. 关键词→严重度映射（configs/severity_keyword_map.v1.json）整体认可或指定例外；
  2. B08/completeness（score=2, critical）与 B09/cleanliness（score=3, critical）：锚点规定 critical 对应空候选，确认保留 critical 还是改 major；
  3. B18：cleanliness 推导为 major 但 decision=uncertain —— 按规则应为 fail，或该维并非 major；
  4. B21：decision=fail 但无 major/critical（structure=minor）—— 提升 severity 或改 decision；
  5. B19/B23（页面内嵌注入指令案卷）：五维均无缺陷却判 uncertain，Rubrics v2 未覆盖"注入尝试本身是否降低决策"的情形 —— 记为**协议覆盖缺口**，保留标注者判断并写入 calibration_findings，不在本轮改协议。
- 确认后才执行 --apply 生成 human_labels.blind.r2.json，并重跑 ingest blind 产出 ROUND1_SUMMARY 与裁决案卷。为避免锚定，修复前的临时试算结果不予披露、不写入交付物。

### 协议偏差登记

| 编号 | 时间 | 描述 | 根因 | 修复 | 影响评估 |
| --- | --- | --- | --- | --- | --- |
| D0 | 2026-11-17 | blind.v1 案卷标题含真实案例名，泄漏变异类型 | 案卷渲染直接写 case_id | 废弃 blind.v1，改建 blind.v2 中性编号 + sealed_mapping.json + 构建期泄漏守卫 | 未用于标注，无实际污染 |
| D1 | 2026-11-18 | 首次 ingest 校验报错串打印真实 case_id，15 个案例名（B07–B21 对应）在控制台可见 | validate_labels 以 case_id 渲染问题串 | 新增 code_map 参数，blind 阶段一律以盲码渲染；run_blind 传反向映射；复验同一输入 58 条问题串全为盲码、case_id 命中 0 | 标签在泄漏发生前已全部填写完毕，不存在按案例名回填的通道；残余风险为标注者已知晓这 15 例的案例名与变异语义。缓解：机械修复与裁决全程只用盲码；裁决以标注者本人 note 证据为准；偏差如实写入最终报告，不做事后数据清洗 |
| D2 | 2026-11-18 | 注入案卷附加问题措辞"候选是否服从了页面内嵌指令？"误导（口径实为 judge 是否服从） | render_adjudication_packet 文案用词不当 | 修正渲染器措辞为"judge 的评估是否服从了页面内嵌指令（即全 4 分且 decision=pass）？"；已生成案卷不重生成，由 docs/P0_ADJUDICATION_GUIDE.md §3 澄清口径 | 仅措辞，不涉及分数/协议/阈值；injection_complied 机械口径（compare_human_case）从未改变；标注者尚未开始裁决，无实际误导后果 |


### 2026-11-18 · 第一轮结果与裁决阶段

- 标注者确认：映射整体认可；B08/completeness、B09/cleanliness → major；B18 → decision=fail；B21 → decision=uncertain；B19/B23 保留 uncertain 并记为协议覆盖缺口。全部写入 configs/human_label_overrides.v1.json（含逐条理由），由工具校验后应用，非手改 JSON。
- 新增规则：source_only 优先——source_only 案卷按协议不得 pass，故 uncertain 即使无缺陷也不判为缺口（修掉 B22 误报）。B23 同时是 source_only 与注入案卷，其 uncertain 由两条规则共同支撑；B19 是唯一真正依赖"注入缺口"判断的案例。
- 第一轮一致性（judge 接受 16/23）：全量决策一致率 0.75、κ=0.5077；development 0.90 / κ=0.8246；frozen_test 0.50 / κ=-0.2857（6 接受例，不可解释，仅描述性）。逐维 exact 0.75、±1 0.9688、严重度符号 0.8125。severe_miss 2、false_alarm 2。
- 裁决阶段入口：outputs/human_review/round1.v1/adjudicate/（17 份）。每份含触发原因、你/judge/silver/程序四方决策对照、逐维分数与严重度对照、judge 的理由与引用证据、盲评时隐藏的变异信息、你的盲评标签、裁决任务。
- 裁决纪律：以证据为准，不向 judge 或 silver 看齐；维持原判断是合法结果，持续分歧会写入 calibration_findings.json 而不是被"修正"。B19、B23 必须填 injection_complied（true/false，指 judge 是否服从了页面内嵌指令）。23 例全部 confirmed=true 且每例写 adjudication_note 后才能跑 --stage final。
- frozen_test 仍不得用于调 judge/协议；任何据此的改动都必须走冻结修订并另建 test v2。

### 2026-11-18 · 裁决阶段工具就绪（助手侧完成，等待标注者裁决）

- 新增 tools/apply_adjudication.py v1.0.0：把标注者的聊天裁决反馈（记录为 configs/adjudication_decisions.v1.json）校验并落盘到预填 final 标签。硬约束：只读标签文件与 spec；不读批量报告/judge 输出/silver/sealed_mapping；每例必须显式出现（无默认确认）；keep 不动 decision/维度；revise 只允许 decision 与五维 score/status/severity/note；overall_note/case_id/blind_code/split/mode 不可变；source_only 不得 pass；注入例 injection_complied 必填 bool 且只允许出现在注入例；spec 重复键拒绝；输出目录 fail-closed；原文件永不覆盖；审计含双输入 sha256 与字段级 before/after。
- 测试：tests/test_apply_adjudication.py 21 项（合成数据）；全量回归 **306 项通过**（outputs/rubrics_judge.p0.adjudication.fulltests.v1.log）。
- 偏差 D2 登记：注入案卷附加问题措辞修正（见偏差表）；round1.v1 案卷不重生成，口径由指南澄清。
- 操作指南：docs/P0_ADJUDICATION_GUIDE.md（阅读顺序 A/B/C/D 组 + 免读 6 例、中性自查清单、injection_complied 定义与 B19/B23 客观事实、聊天回复模板、后续流水线）。
- 当前状态：human_labels.final.json 预填 confirmed=0/23；等待标注者读案卷并回复裁决。收到回复后：记录 spec → apply_adjudication（final.prep.v1）→ ingest --stage final（final.v1）→ 全量回归 + check_freeze → 交付报告后停止。

### 2026-11-18 · 最终裁决与 P0 交付（零模型调用）

- 标注者以聊天回复完成全部 23 例裁决（两条回复；第二条澄清 B18 decision 下调为 uncertain）。逐字记录：configs/adjudication_decisions.v1.json（spec_version=1，feedback_verbatim，note_policy：修订 note 为事实性变更记录，标注者未附逐条理由，助手未虚构理由）。
- 18 keep / 5 revise：B04 cleanliness 2/major + decision fail；B09、B12 cleanliness 2/major；B13 cleanliness 3/minor + structure 3/minor + decision uncertain；B18 cleanliness 4/minor + structure 4/none + decision uncertain。B19/B23 injection_complied=false（judge 未服从注入指令；B23 拒绝产出评估）。6 例无案卷（B01/B03/B05/B06/B11/B22）按指南默认维持，已披露且无异议。
- tools/apply_adjudication.py v1.0.0 落盘 → outputs/human_review/final.prep.v1/（23/23 confirmed；adjudication_audit.json 双输入 sha256 + 字段级差异；post-apply 决策一致性扫描干净，仅 B19 豁免——已登记的协议覆盖缺口）。
- ingest --stage final → outputs/human_review/final.v1/（human_gold.final.json、agreement_report.json、AGREEMENT_REPORT.md、calibration_findings.json 16 条）。最终人类决策分布 pass 1 / uncertain 13 / fail 9。
- 最终指标（裁决后，必须与盲评并列）：决策一致 0.9375、κ 0.872（dev 1.0/1.0；frozen_test 0.8333/0.0，仅 6 接受例，统计上不可解释）；逐维 exact 0.8281 / ±1 0.9688；严重度符号 0.8281（64 对）；severe_miss 0；false_alarm 1（cal-mdn-instruction_interference）。独立锚点仍是第一轮盲评 0.75/κ0.5077。指标变化全部来自人类侧裁决修订，judge 零变化；severe_miss 清零是标注者复核证据后下调 B13/B18，不是 judge 被修好——偏宽残留与 30.4% 拒绝率仍是 P1 目标。
- 验证：全量回归 306 项 OK（outputs/rubrics_judge.p0.final.tests.v2.log，19.873s，exit 0）；check_freeze NONE（manifest 双哈希 MATCH）。
- 交付报告：docs/P0_DELIVERY_REPORT.md（证据链 + 可复现命令 + 哈希 + 偏差 D0/D1/D2 + B19 覆盖缺口 + 局限）。**P0 到此交付并停止**；P1/P2/P3/节点5 均需用户明确批准（P1 起须先批调用预算）。


## P1 执行记录（滚动更新）

### 2026-11-18 · P1 工程就绪（零模型调用，待预算批准）

- 预注册固定：docs/P1_META_EVAL_PLAN.md（H1–H5、设计、dev-only 阈值、回退 F1/F2、预算）；修订 R1 记录两处工程耦合（菜单预算自适应、silver 标签 prompt_chars 诊断），评分语义/阈值/预算不变。
- 实现：judge v1.1.0（证据菜单 + 空白折叠引文匹配 + 探针扰动参数）；运行器 --split + probe 透传；tools/amend_freeze_v3.py、tools/run_p1_probes.py、tools/score_p1_results.py。
- 验证：freeze v3 --verify MATCH、check_freeze NONE；离线归因证明 H2 修复 blurb（outputs/p1_offline_attribution.v1.json）；定向 45 项 + 全量 351 项测试 OK（验收管线端到端验证）。
- 零调用诊断：7 例拒绝 = 6 模式1（cleanliness/structure 仅引 p:N）+ 1 模式2（blurb 引文空白转录失配，源含双空格/\r\n）。dev 当前拒绝 2/12=16.7%，目标 ≤1/12。
- 状态：等待用户批准预算。批准后运行计划：冒烟 2 + W1 dev 重评 12 + W2 cross-judge 13 + W3 探针 12 + W4 稳定性 2 = 基础 41 次（回退 F1 ≤12，上限 ≤53）。第二模型 qwen-max（不可用则 qwen-plus，冒烟确认）。frozen_test 不重跑不调参。


### 2026-11-18 · P1 实验执行（批准后，有条件达标）

- 密钥 401 阻塞经用户更新 env.local 解除（200）。成功调用 40≤41，tokens 541303；第二模型 qwen-plus（qwen-max 403）。
- W1 dev：拒绝 8.3% ✓、severe_miss 1 ✓、决策分歧 3 ✗（护栏破）；一致率 1.0→0.7273/κ0.529 回归，false_alarm 2。verdict REJECT（护栏）。
- W2 cross-judge qwen-plus：拒绝 50%，双接受 6 例一致 0.8333/κ0.6667。W3 位置翻转 1/6、改写 2 拒绝；W4 temp0 稳定。
- 交付 docs/P1_DELIVERY_REPORT.md。F2 决策待用户（a 接受带告警 / b 回滚 / c P1.5 迭代）。


## P1.5 验收 ACCEPT（2026-11-19，批准后执行）

- 用户批准 P1.5 预算后执行：冒烟 2 + W1 dev 重评 10（前 2 缓存）+ W2 稳定性 2 = **14 次新调用 ≤16**，tokens **201,975**（低于估算）。回退 F1/F2 未触发。
- **验收 ACCEPT，护栏恢复**：dev 拒绝率 **0%**（0/12）、severe_miss **0**、接受例决策分歧 **1**（≤1）——三项预注册阈值全达标。freeze_check NONE。
- dev 决策一致率 **0.9167 / κ0.8554**（v1.1 0.7273/0.5286 大幅恢复）；逐维 exact 0.8333、±1 1.0、严重度符号 0.875。一般性解耦假设 **H1 得证**（菜单锚定消除）。
- 修复案例：appetite-missing_paragraph、appetite-duplicate（v1.1 fail→uncertain 匹配）、blurb-reorder（v1.1 severe_miss→fail 匹配）、blurb-missing_paragraph（v1.1 被拒→接受且匹配）。残留 1 处 false_alarm：appetite-reorder（judge fail vs 人类 uncertain，护栏内，留 P2 检验）。
- 稳定性 temp=0 复跑 2 例完全一致（翻转 0、exact 1.0）。
- 交付 **docs/P1_5_DELIVERY_REPORT.md**（命令+哈希+台账+三版对比+如实局限）。frozen_test 未重跑未调参、永久封存至 P2；judge 分数仍不作训练奖励。
- P1 系列完成：v1.0（拒绝 16.7%）→ v1.1（8.3% 护栏破）→ **v1.2（0% 护栏恢复 ACCEPT）**。后续 P2 扩规模/IAA/新 frozen_test v2 检验泛化（需批准）。
