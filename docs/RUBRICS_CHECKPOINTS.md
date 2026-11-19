# 项目三 Rubrics 改进节点

2026-11-17：目标已建立，按用户要求每个重要节点停止并检查。目标整体尚未完成；节点1之后不自动越过检查点。

| 节点 | 验收条件 | 状态 |
| --- | --- | --- |
| 1 Rubrics v2 | 协议/算法一致、错误证据可定位、未知不冒充满分、测试与真实输出复评 | 已通过，停在检查点 |
| 2 Qwen Judge | 独立评分schema、证据校验、gold/无gold分离、真实小预算调用与记录 | 已通过（工程验收），停在检查点 |
| 3 校准集 | 多模板案例、人类审阅标签、按来源/模板隔离并冻结test | 已通过（silver工程验收），停在检查点；独立人工审阅仍未完成 |
| 4 批量与稳定性 | 缓存/断点/成本、重复评分、逐维误差和误报漏报、复核清单 | 未开始 |
| 5 可选修复 | Judge先通过校准，仅reference/修复开发集反馈，不回传test/gold | 未进入 |

## 节点1验收

- 实现：src/webextractor/rubrics_v2.py；协议：docs/RUBRICS_V2_PROTOCOL.md；v1保留。
- 五维：完整性、纯净度、结构、标题、格式。结构按文本对齐后比较属性与顺序；代码空白独立评分；DOM id不再影响结构。
- 不能判断时null/unscored，低覆盖partial；没有综合平均分。严重错误fail、局部差异或不足uncertain，附证据进入复核。
- 13项v2定向测试通过；全量142项通过（outputs/rubrics_v2.checkpoint1.tests.v2.log）。
- 已保存Qwen输出离线复评：outputs/rubrics_v2.qwen38.checkpoint1.v1.json。无新增API调用。

| 案例 | 完整性 | 纯净度 | 结构 | 标题 | 格式 | 决策 |
| --- | --- | --- | --- | --- | --- | --- |
| 同模板课前甜点 | 4 | 4 | 4 | 3 | 不适用 | uncertain，编号丢失复核 |
| 跨模板Python介绍 | 0 | 0 | 未评分 | 0 | 不适用 | fail，空候选 |
| 跨模板IANA | 0 | 0 | 未评分 | 0 | 不适用 | fail，空候选 |

冻结文件哈希见outputs/rubrics_v2.checkpoint1.freeze.json。此处“通过”指工程节点验收，不代表模型Judge可靠或人类一致性已测。

## 检查结论及后续约束

目前比例阈值、噪声扣分和严重度是开发规则，未人工校准；结构对齐不支持语义改写和拆合块，重复相同文本存在配对歧义；格式仅检查代码，不覆盖Markdown渲染、复杂表格和链接；来源归属未评分。这些均已写入协议，不作为本节点隐含能力。

下一节点仅实现Judge及其严格输出、证据校验与小预算接入，不扩展训练。人工校准留在节点3，不能以助手或模型自行标注替代独立人工标签。整体goal保持未完成，等待检查点后继续。

## 节点2验收（2026-11-17）

- 实现：src/webextractor/rubrics_judge.py（JUDGE_VERSION 1.0.0，提示词迭代v1→v4）；tools/run_rubrics_judge.py（批量、缓存、断点续跑、预算上限、签名绑定版本/模型/设置/prompt_sha）；定向测试14项+工具测试10项。
- 严格JSON schema：五维×(score/status/severity/reason/evidence)。证据必须是注册参考（p:/g:/s:）内的精确非空子串；每个scored/partial维度至少引用一条s:或g:；越界索引、幻觉引用、篡改引文均拒绝，fail-closed。
- gold/source_only分离：无gold时程序侧unscored，judge仅provisional，decision至多uncertain且强制人工复核；source截断时所有scored维度降为partial，不允许pass。
- 提示词迭代（如实记录）：v1真实3调用全部拒绝（候选-only证据等）；v2真实4调用全部拒绝（not_applicable误用severity=unknown、幻觉g:23越界、NBSP引文被归一化）；v3真实4调用3接受，iana仍因NBSP拒绝；v4零新增调用，缓存重放加窄幅NBSP等价折叠后4/4接受。
- NBSP决定（有记录的语义放宽）：U+00A0与U+0020为视觉等同空白，仅在证据子串校验时对引文与注册文本双向折叠（_nbsp_fold）；其余字符保持严格，空白-only引文仍拒绝。专用测试覆盖双向等价与非空白篡改拒绝。提示词仍要求逐字符抄写。
- 冒烟结果（outputs/rubrics_judge.node2.smoke.v4.json，模型qwen3.8-27b，temperature=0，enable_thinking=false）：

| 案例 | 模式 | 决策 | 说明 |
| --- | --- | --- | --- |
| smoke-appetite-zh | with_gold | pass | 四维4分，format不适用，干净候选 |
| smoke-nasa | with_gold | uncertain | 源截断→全部partial，强制复核 |
| smoke-w3c-zh | with_gold | uncertain | 源截断→全部partial，强制复核 |
| smoke-iana | source_only | uncertain | 无gold provisional，强制复核 |

- 真实预算：累计11次调用/234,105 tokens（v1:3次/58,553；v2:4次/87,329；v3:4次/88,223；v4:0次）。gnu因提示词超预算在构造期拒绝，未产生调用；whatwg超10MiB上限、webdev为封存验证页，均排除。
- 全量回归166项通过：outputs/rubrics_judge.node2.tests.v2.log。缓存重放对已存响应按当前验证器重新校验，语义变更不会沿用旧接受结论。
- 边界：Judge未经校准，分数不得作为训练奖励；冒烟仅4页，不代表泛化；人类一致性未测；校准集与批量评测留在节点3/4。

## 节点3验收（2026-11-17）

- 实现：tools/build_calibration_set.py（确定性构建+--verify复算）；samples/calibration/（23候选+23标签）；samples/calibration_manifest.json；冻结outputs/rubrics_judge.node3.freeze.json（61文件哈希+23例元数据）。定向测试11项。
- 规模与隔离：dev 12例（T1 python_appetite_zh 6变体、T2 python_blurb 4变体、T3 iana_example_domains source_only 2变体）；frozen_test 11例（T4 mdn.candidate 5变体、T5 github-copilot-blog.candidate 4变体、T6 w3c-link-text.candidate source_only 2变体）。同一基础页只出现在一个split，check_manifest_isolation强制。
- 覆盖全部7类受控错误：漏段、混噪、重复、乱序、标题编号、代码缩进、网页指令干扰（注入块要求judge不得服从）。clean指无注入变异，不代表提取完美。
- 标签性质：label_origin=assistant_silver、human_reviewed=false。有gold例的期望分数/严重度由冻结rubrics_v2程序对受控变异确定性推导；无gold例为助手provisional期望（decision不得为pass）。silver不是人类gold，分歧进入复核清单而非自动调阈值。
- 排除与原因（如实）：rfc.candidate候选JSON自身449,798字符，任何源限制下均超110,000提示词预算（实测2000/500字符源限制仍超）；gnu gold超预算；whatwg源15.6MiB超10MiB上限；webdev为封存验证页。T6由rfc改为w3c-link-text.candidate（真实W3C页，source_only，26块）。
- 构建过程发现并修复两处确定性缺陷：冻结files条目须按磁盘序列化字节哈希（非规范化JSON哈希）；write_text须newline=''避免CRLF漂移。v1/v2失败日志保留（outputs/rubrics_judge.node3.build.v1/v2.log、verify.v1/v2.log），v3构建+verify MATCH（23例/61文件）。
- 期望决策分布：pass 1（appetite-clean）、uncertain 11、fail 11。批量配置max_source_chars=20000下blurb/mdn/github源截断→partial；appetite/iana/w3clink未截断。mdn提示词约105k字符，接近110k上限但未超。
- 已知灵敏度限制：大页（mdn 145块）单段删除recall仍≥.98，程序完整性留在4分桶（minor）；±1容差与复核清单处理该粒度问题。结构乱序程序严重度固定major，judge可能更宽——分歧属校准发现，不自动改协议。
- 全量回归177项通过：outputs/rubrics_judge.node3.tests.v1.log。
- 边界：frozen_test只评一次、不调阈值；独立人工审阅未完成，不能以silver替代；Judge分数仍不作为训练奖励。

## 节点4验收（2026-11-17）

- 批量工具链：tools/run_rubrics_judge.py（缓存先于调用、断点续跑、预算上限、签名绑定版本/模型/设置/prompt_sha）；tools/score_judge_results.py（冻结完整性fail-closed、逐维误差、severe_miss/false_alarm、注入服从、稳定性、复核清单）。定向测试：judge 15、runner 12、calibration 11、metrics 7。
- 最终批量 outputs/rubrics_judge.node4.batch.v6.json（v1–v5为迭代历史，均保留）：23例，16接受/7拒绝。7例拒绝全部为验证阶段fail-closed（6例cleanliness/structure仅p:证据、1例引文不支持），属模型不合规，确定性重放仍拒绝，入复核清单。failure_rate 0.3043。
- 指标（仅接受例，对silver）：overall逐维exact 0.800、±1 0.9375、严重度符号0.8125、决策一致0.8125；dev决策一致0.900（9/10），frozen_test 0.6667（4/6）；judge vs 程序逐维exact 0.7692（13有gold接受例）。severe_miss 3例（appetite-reorder、mdn-code_indent、mdn-reorder）：分数与程序一致但严重度major→minor，judge偏宽；false_alarm 0。协议未自动修改。
- 稳定性（预注册samples/calibration_stability_manifest.json，6例--ignore-cache真实重跑）：5/6逐维分数/严重度/决策完全一致；github-noise两次均被同一规则拒绝，保守计missing_or_error。identity_rate 0.8333。
- 注入：mdn-instruction_interference未服从（injection_complied=false），fail与silver一致；w3clink-instruction_interference被拒绝，服从性不可评，入复核。
- 工程决定（详见docs/RUBRICS_JUDGE_REPORT.md第4–5节）：NA/unscored空reason窄幅放宽→冻结修订v2（唯一变化文件rubrics_judge.py，数据哈希与v1逐一相同，verify MATCH）；provider瞬时故障经原始探针诊断（键脱敏），未改配置；runner超时钳制bug修复（构造默认30s钳制声明90s）；90s超时两例经稳定性证明为延迟波动后重试接受，未改冻结批量配置；gold投影与metrics manifest双哈希约定对齐冻结，batch v6零调用重放。
- 预算：节点4共54次调用（batch 45+stability 6+诊断3），已计量542,105 tokens；11次失败/超时usage未上报。全goal累计65次调用、已计量776,210 tokens、12次usage未知。缓存重放v2–v6共93例次免付费。
- 全量回归187项通过：outputs/rubrics_judge.node4.tests.v1.log。冻结v2 verify MATCH（23例/61文件）。
- 边界：silver非人类gold，一致率非准确率；frozen_test只评一次未调阈值；Judge未校准、分数不作训练奖励；复核清单22/23；节点5未进入。本轮goal交付docs/RUBRICS_JUDGE_REPORT.md后停止。

| 节点 | 状态 | 关键证据 |
| --- | --- | --- |
| 1 协议冻结 | 完成 | rubrics_v2.py + RUBRICS_V2_PROTOCOL.md，哈希MATCH |
| 2 Qwen Judge | 完成 | smoke v4 4/4接受，11调用/234,105 tokens |
| 3 校准集 | 完成 | 23例冻结v2 verify MATCH，silver标签 |
| 4 批量+稳定性 | 完成 | batch v6 16/23接受，稳定性5/6，187测试，报告交付 |
| 5 修复闭环 | 未进入 | 按用户指令停止 |

## P0 人工校准工具链（2026-11-17，节点4之后）

- 交付：tools/build_human_review_kit.py（盲评案卷构建，冻结fail-closed、确定性字节、防泄漏守卫）+ tools/ingest_human_labels.py（blind/final两阶段：密封编号解析、schema校验、human gold快照、Cohen κ与逐维一致率、裁决案卷、持续分歧清单）。推进计划见docs/HUMAN_CALIBRATION_PLAN.md。
- 防泄漏修复：blind.v1案卷标题含真实案例名（泄漏变异类型），废弃；blind.v2改用中性编号B01–B23，sealed_mapping.json密封映射，案卷泄漏扫描CLEAN，构建器对真实案例名出现即抛错。
- 验证：定向21项测试通过；全量回归208项通过（outputs/rubrics_judge.p0.tests.v1.log）。工具包对真实冻结数据构建成功（23例，dev12/frozen_test11），check_freeze无漂移。
- 状态：等待用户独立盲评（会话1 B01–B12，会话2 B13–B23）。助手不代填标签；本阶段零模型调用。人类标签产生前，judge–human一致率不存在，现有0.8125仍只是对silver的一致率。


## P0 第一轮回收（2026-11-18）

- 用户独立完成 23/23 盲评（annotator=hqli631，annotation_date=2026-11-17），decision 分布 pass 1 / uncertain 12 / fail 10。标签文件：outputs/human_review/blind.v2/human_labels.blind.json（22,173 bytes，mtime 2026-11-18T13:33）。
- 阻塞问题：58 个维度把 status 取值 partial 误填进 severity 列（合法值为 none/minor/major/critical/unknown），ingest 校验 fail-closed 拒绝，未产出任何 gold。score/decision/note 全部有效。
- **协议偏差 D1（已修复）**：首次 ingest 校验的报错串使用真实 case_id，导致 15 个案例名（含变异类型语义，如 -clean/-noise/-reorder）在控制台可见。根因：validate_labels 直接格式化 case_id。修复：新增 code_map 参数，blind 阶段一律以盲码渲染问题串；run_blind 传入反向映射。复验：同一输入重跑，58 条问题串全部为 B##/dim 形式，case_id 命中数 0；校验失败不创建输出目录。影响评估：标签在泄漏发生前已全部填写完毕，不存在按案例名回填的通道；残余风险为标注者已知晓 B07–B21 对应案例名，后续裁决阶段须以其本人 note 证据为准，本偏差记入最终报告，不做事后清洗。
- 修复工具：tools/repair_human_labels.py + configs/severity_keyword_map.v1.json。只做机械列位修复，severity 仅从标注者本人 note 文本经冻结的 Rubrics v2 严重度锚点推导；工具只读标签文件与关键词映射，不读批量报告/judge 输出/metrics/silver 标签/sealed_mapping.json，输出中不出现真实 case_id（有测试断言）；score、decision、note、overall_note 一律原样保留；已合法 severity 一律不动，仅列可疑项待确认；原文件永不覆盖，产出带 sha256 审计。
- dry-run 结果（outputs/human_review/round1.prep.v1）：修复 58 条（partial→none 46 / partial→major 11 / partial→minor 1）；保持不动 57 条合法值；提示 17 条；一致性待确认 2 条（B18 存在 major 却判 uncertain；B21 判 fail 却无 major/critical）；另 B08 completeness(score=2)、B09 cleanliness(score=3) 的 critical 与"空候选"锚点不符，需标注者确认。
- 验证：新增 42 项定向测试（tests/test_repair_human_labels.py 38 项 + 盲码报错 4 项）；全量回归 250 项通过（outputs/rubrics_judge.p0.repair.tests.v3.log，run.cmd test，19.6s）。
- 状态：等待标注者确认关键词映射与上述 4 项待确认点，然后 --apply 生成 human_labels.blind.r2.json 并重跑 ingest blind。仍为零模型调用；judge–human 一致率尚未产生，现有 0.8125 仍只是对 silver 的一致率。


## P0 第一轮（盲评）一致性结果（2026-11-18）

- 标注者确认项已全部落盘为可审计规格 configs/human_label_overrides.v1.json（approved_by=hqli631，approved_at=2026-11-18）：关键词映射整体认可；B08/completeness 与 B09/cleanliness 由 critical 改 major（锚点规定 critical 仅对应空候选）；B18 decision uncertain→fail（cleanliness=major）；B21 decision fail→uncertain（维持 structure=minor，无 major/critical）；B19/B23 注入案卷保留 uncertain 并记为**协议覆盖缺口**（Rubrics v2 未规定"注入尝试本身是否降低决策"），本轮不修订冻结协议。
- tools/repair_human_labels.py 升至 v2.1.0：两段式（机械修复 + 标注者确认覆盖），overrides 校验拒绝 score/note 覆盖、缺理由、未知盲码、非法取值；新增 source_only 优先规则（source_only 不得 pass，故 uncertain 即使无缺陷也不算缺口，修掉 B22 误报）。
- 修复产物：outputs/human_review/round1.prep.v2/（REPAIR_DIFF.md / CONSISTENCY_WARNINGS.md / severity_repairs.json / repair_audit.json / human_labels.blind.r2.json）。机械修复 58 条（→none 46 / →major 11 / →minor 1），覆盖 4 条，保留合法值 57 条，待确认 0 条，已确认保留 1 条（B19）。原盲评文件未改动。
- 验证：新增 35 项测试（overrides 校验/应用/缺口确认/CLI/防泄漏 + source_only 优先），全量回归 **285 项通过**（outputs/rubrics_judge.p0.round1.tests.v1.log，19.1s）。ingest 前 check_freeze 无漂移。

### 首次真实 judge–human 一致性（此前 0.8125 只是对 silver 的一致率）

| 指标 | 全量 | development | frozen_test |
| --- | --- | --- | --- |
| 案例数 | 23 | 12 | 11 |
| judge 接受 / 拒绝 | 16 / 7 | 10 / 2 | 6 / 5 |
| 决策一致率（接受例） | 0.75 | **0.90** | 0.50 |
| 决策 Cohen κ | **0.5077** | **0.8246** | -0.2857 |
| 逐维 exact / ±1 | 0.75 / 0.9688 | 0.80 / 1.00 | 0.6667 / 0.9167 |
| 严重度符号一致 | 0.8125（64 对） | 0.90（40 对） | 0.6667（24 对） |
| severe_miss | 2 | 0 | 2 |
| false_alarm | 2 | 1 | 1 |

- severe_miss（人类判严重而 judge 不严重）：cal-mdn-code_indent、cal-github-clean → judge 在代码缩进/格式类缺陷与"干净"案卷上偏宽。false_alarm：cal-appetite-noise、cal-mdn-instruction_interference → judge 偏严。
- fail-closed 拒绝 7 例（30.4%）：6 例 "Scoring needs source/reference evidence"、1 例 "Evidence quote is not supported"；frozen_test 拒绝率 45%，直接把可比样本压到 6 例。
- **诚实边界**：frozen_test κ=-0.2857 建立在 6 个接受例上，置信区间极宽，统计上不可解释，仅作描述性记录，且**不得**据此调 judge 或协议；dev κ=0.8246 同样只有 10 个接受例。单一标注者，无 IAA。一致率≠准确率。judge 分数仍不作为训练奖励。
- 产出：outputs/human_review/round1.v1/（ROUND1_SUMMARY.md、blind_agreement.json、human_gold.blind.json、17 份 adjudicate/*.md、预填 human_labels.final.json）。无实质分歧的 6 例（B01/B03/B05/B06/B11/B22）不生成案卷，仍需 confirmed=true。
- 状态：等待标注者裁决 17 份案卷并填 injection_complied（B19、B23），随后 --stage final 产出 AGREEMENT_REPORT.md 与 calibration_findings.json。本阶段仍为零模型调用。


## P0 最终裁决与交付验收（2026-11-18）

- 裁决：23/23 显式覆盖（18 keep / 5 revise：B04/B09/B12/B13/B18），逐字规格 configs/adjudication_decisions.v1.json（sha256 45252d8c98e4a119fc0502a12333fcfb26463dfe1870d9dd31e30df656a944c1；feedback_verbatim 两条，第二条澄清 B18）。B19/B23 injection_complied=false（judge 未服从；B23 拒绝产出）。B18 decision=uncertain：降分后无 major/critical，按冻结决策规则⇒uncertain。6 例无案卷默认维持，已披露无异议。
- 落盘：tools/apply_adjudication.py v1.0.0 → outputs/human_review/final.prep.v1/；adjudication_audit.json 双输入 sha256（预填标签 ee9fe18ebbe3d113939372824fca63fdf6f653aef05b2894e76a2949461dbb63 / 规格 45252d8c…）+ 字段级差异；post-apply 决策一致性扫描干净（仅 B19 豁免，协议覆盖缺口已登记，本轮不修订冻结协议）。
- 接收：ingest --stage final → outputs/human_review/final.v1/（human_gold.final.json 23/23 confirmed；最终决策分布 pass 1 / uncertain 13 / fail 9；agreement_report.json、AGREEMENT_REPORT.md、calibration_findings.json）。
- 指标（裁决后，与盲评独立锚点 0.75/κ0.5077 并列）：决策 0.9375 / κ 0.872；dev 1.0/1.0（10 接受例）；frozen_test 0.8333/0.0（6 接受例，统计上不可解释，仅描述）；逐维 exact 0.8281 / ±1 0.9688；严重度符号 0.8281（64 对）；severe_miss 0；false_alarm 1（cal-mdn-instruction_interference，唯一接受例决策分歧）。source_only 3 例：决策 1.0、exact 0.9167（11/12）。指标变化全部来自人类侧修订，judge 零变化；severe_miss 清零源于标注者下调 B13/B18，偏宽残留仍在。
- 持续分歧 16 条：7 judge_error（6× Scoring needs source/reference evidence + 1× Evidence quote is not supported）+ 9 维度级（structure 6 例、cleanliness/completeness/title 各 2 例、format 1 例，同例可多维）。留痕不自动调参。
- 验证：全量回归 **Ran 306 tests in 19.873s / OK**（outputs/rubrics_judge.p0.final.tests.v2.log，exit 0；首次尝试日志因会话回收中断残缺，已删除）；check_freeze **NONE**（batch v6 / stability v1 对 freeze v2 无漂移，manifest 文件字节 a3ef652c… 与 canonical 7edaf004… 双哈希 MATCH）。
- 交付：docs/P0_DELIVERY_REPORT.md（证据链 + 可复现命令 + 哈希 + D0/D1/D2 + B19 缺口 + 局限 + 后续排队）。**P0 到此停止**；P1/P2/P3/节点5 均需用户明确批准，P1 起须先批调用预算；judge 分数仍不作训练奖励。


## P1 工程就绪验收（2026-11-18，零模型调用）

- 预注册 docs/P1_META_EVAL_PLAN.md（含修订 R1）在任何调用前固定：假设 H1–H5、设计、dev-only 验收阈值（拒绝率 <10%、severe_miss ≤1、接受例决策分歧 ≤1）、回退 F1/F2、运行计划与预算上限。frozen_test 全程不重跑、不调参、永久封存至 P2。
- judge v1.1.0（仅改 src/webextractor/rubrics_judge.py，新 sha256 cc649504b82832001c2f9a8c41f79e53a4006cec60914a22a5adc1cfb23a240e）：① 各维度证据菜单（精确 registry 前缀 {ref,quote}，确定性、无标签、预算自适应 quote 前缀 {120,60,30}）；② 引文空白折叠匹配（折叠所有空白 run 后精确子串，非空白字符逐字有序，幻觉防护不放松）；③ 探针扰动参数 source_order_seed/dimension_phrasing（默认 None 时生产 prompt 逐字节不变）。
- 运行器 run_rubrics_judge.py：新增 --split 过滤（dev-only 用冻结全量 manifest，文件字节不变 → manifest_sha256 与冻结一致）+ run_case probe 透传；config_signature 键集不变。
- 新工具：tools/amend_freeze_v3.py（幂等；证明 23 silver 标签仅 prompt_chars 诊断漂移、评分内容逐字段相同后刷新该诊断并同步 v3 cases 哈希）；tools/run_p1_probes.py（position/phrasing/stability，描述性专用，--dry-run）；tools/score_p1_results.py（dev-only 验收 + cross-judge + 探针稳定性 + check_freeze，复用 ingest 的 compare_human_case/aggregate_human 保证与 P0 指标语义一致）。
- freeze v3（outputs/rubrics_judge.node3.freeze.v3.json）：changed_code=[rubrics_judge.py]；23 silver 标签 prompt_chars 诊断刷新（评分内容证明不变）；候选/gold/manifest/源页/协议文档/rubrics_v2/构建器/batch_config 哈希不变。build_calibration_set --verify v3 = **MATCH**；check_freeze node4 batch v6 + stability v1 对 v3 = **NONE**。协议文档 docs/RUBRICS_V2_PROTOCOL.md 哈希 ab0887b5… 不变（评分语义真正冻结）。
- 离线归因 outputs/p1_offline_attribution.v1.json（零调用）：v1.1 校验器重放 v1.0 缓存的 7 例拒绝响应——cal-blurb-missing_paragraph（模式2 空白转录，dev）**被接受**（H2 得证）；其余 6 例（模式1 缺 s:/g: 引用）旧响应仍拒绝，需 H1 菜单 prompt 变更使模型产出合规引用，待批准后 dev 重评验证。
- 测试：定向 45 项 OK（tests/test_p1_judge_v11.py，含验收管线 happy-path/reject/cross+probes/防覆盖，outputs/p1.targeted.tests.v4.log）；全量回归 **Ran 351 tests in 27.574s / OK**（outputs/rubrics_judge.p1.engineering.tests.v2.log，exit 0）。
- 状态：**工程就绪，零模型调用，等待用户批准预算**。批准后执行：冒烟 2 → W1 dev 重评 12 → W2 cross-judge 13 → W3 探针 12 → W4 稳定性 2（基础 41 次，回退 F1 contingency ≤12，上限 ≤53 次）。judge 分数仍不作训练奖励。


## P1 实验执行与验收（2026-11-18，批准后）

- 密钥阻塞（QWEN_API_KEY 无效 401）经用户更新 env.local 解除（ping 200）；密钥全程未打印。
- 实际成功生成调用 **40 次 ≤ 批准 41**（总尝试 43 ≤ 上限 53）；报告计量 tokens **541,303**。第二模型 **qwen-plus**（qwen-max 免费额度耗尽 403，预注册回退）。
- **W1 dev 验收**：拒绝率 8.3%（1/12）✓、severe_miss 1（blurb-reorder）✓、接受例决策分歧 3 ✗（护栏 ≤1 破）→ verdict **REJECT（护栏）**。dev 决策一致率从 P0 最终 1.0/κ1.0 回归到 **0.7273/κ0.5286**；false_alarm 2（appetite-missing_paragraph、appetite-duplicate）。freeze_check NONE。blurb 拒绝原因模式2→模式1。
- **W2 cross-judge（qwen-plus，描述性）**：judge2 拒绝 6/12=50%；双接受 6 例决策一致 0.8333/κ0.6667、逐维 exact 0.8333；分歧例 appetite-duplicate（judge1 fail vs judge2 pass）。模型特异性合规/偏差显著。
- **W3/W4 探针（描述性）**：位置扰动决策翻转 1/6（appetite-duplicate）、逐维 exact 0.875；中性改写 2 例新拒绝（接受例内稳定）；temp=0 复跑完全稳定（翻转 0、exact 1.0）。
- 离线归因 H2 得证（blurb 模式2 在 v1.1 校验器下接受）。
- 交付 **docs/P1_DELIVERY_REPORT.md**（命令+哈希+台账+如实局限）。**验收为有条件达标：目标硬指标（severe_miss≤1、拒绝<10%）达标，预注册一致率护栏破。**
- **F2 决策点待用户**：(a) 接受 v1.1 带告警（豁免护栏）/ (b) 履行 F2 回滚 v1.0（拒绝率回 16.7% 反不达硬指标）/ (c) P1.5 预注册迭代同时恢复一致率（需新预算）。助手建议 (c)>(a)>(b)。frozen_test 未重跑未调参；judge 分数仍不作训练奖励。


## GitHub 同步 + P1.5 启动（2026-11-19）

- **GitHub 同步完成**：项目三首次推送至 https://github.com/hqli631/offline_web_extractor （main 分支，commit d2ad75c0be1da40b312bccdb64f5f100180eca19，687 文件）。git init→密钥扫描（687 文件零泄露，env.local 经 .gitignore 排除）→commit→push。schannel TLS 握手失败改用 **openssl SSL 后端**（已固化 git config http.sslBackend openssl）；GCM 认证通过；远程 refs/heads/main 与本地 HEAD 一致。
- **P1.5 启动（路径 c）**：零调用漂移诊断 outputs/p1_drift_diagnostic.v1.json 揭示一般性**菜单锚定效应**（v1.1 菜单把严重度拉向中间档：轻缺陷抬高→false_alarm，重缺陷压低→severe_miss）。预注册 docs/P1_5_META_EVAL_PLAN.md：judge v1.2.0 一般性解耦评分与证据菜单（菜单降级为引文附录+严重度锚点强化），目标恢复 dev 护栏（分歧≤1）同时保持拒绝<10%、severe_miss≤1；严禁逐例拟合人类标签；frozen_test 仍封存。预算基础 16 次/上限≤40，待批准。下一步：零调用工程实现+测试→freeze v4→报预算→批准→dev 重评→验收→报告。


## P1.5 工程就绪（2026-11-19，零调用，待预算批准）

- judge **v1.2.0**（仅改 rubrics_judge.py，新 sha256 edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891）：证据菜单移至 prompt 末位（引文附录）+ 新增 SCORING INDEPENDENCE 强约束（评分/严重度仅依实际缺陷幅度按锚点判定，菜单不得抬高/压低任何分数或严重度）+ 严重度锚点强化。一般性原则，无案例特异分支（测试断言 prompt 不含 cal-/盲码）。菜单内容/空白折叠/s:/g: 规则/探针参数不变。
- 新工具 tools/amend_freeze_v4.py（幂等，证明 silver 标签仅 prompt_chars 漂移）；freeze **v4** 修正完成：代码仅 rubrics_judge.py，23 标签诊断刷新（评分内容证明不变），候选/gold/manifest/源页/协议文档/rubrics_v2/构建器/batch_config 不变。build_calibration_set --verify v4 = **MATCH**；check_freeze 历史 batch v6 对 v4 = **NONE**；协议文档哈希 ab0887b5… 不变。
- 测试：P1.5 定向 10 项（tests/test_p1_5_judge_v12.py）+ P1/judge 定向共 82 项 OK；全量回归 **361 项 OK**（outputs/rubrics_judge.p1_5.engineering.tests.v1.log，21.140s）。
- 预注册 docs/P1_5_META_EVAL_PLAN.md（H1 解耦消除菜单锚定；验收 dev 分歧≤1 且拒绝<10% 且 severe_miss≤1；回退 F1/F2 两阶段）。
- 状态：**工程就绪，零调用，等待用户批准 P1.5 预算**（基础 16 次：冒烟 2+dev 重评 12+稳定性 2，~240k tokens；回退两阶段上限≤40 次/~600k）。批准后 dev 重评→验收（恢复护栏）→交付 P1.5 报告→同步 GitHub→停止。frozen_test 仍封存；judge 分数仍不作训练奖励。
