# P0 人工校准 · 交付报告（最终）

日期：2026-11-18（Asia/Shanghai）。标注者：hqli631（单一标注者）。
范围：项目三"基于 Rubrics 的大模型输出自动化评估"的 P0 人工校准阶段——为冻结的 Rubrics v2 + Qwen Judge 建立独立人类锚点。
**P0 全程零模型调用**；judge 输出、协议、阈值、缓存自节点4交付后未发生任何变化。
状态：**已交付**。本报告为 P0 的最终可复现记录；后续 P1/P2/P3 与节点5 均须用户明确批准（P1 起须先批预算）。

---

## 1. 结论摘要

- 23/23 案例完成独立盲评 → 机械修复 → 第一轮一致性 → 证据案卷裁决 → 最终接收，全链路 fail-closed、留痕、可复现。
- **独立锚点（第一轮盲评）**：决策一致率 0.75，Cohen κ 0.5077，severe_miss 2 例。
- **裁决后（最终）**：决策一致率 0.9375，Cohen κ 0.872，severe_miss 0 例，false_alarm 1 例。
- 最终数字是**裁决后一致率**：标注者在裁决阶段看过 judge 证据，故 0.9375/0.872 **不得**表述为纯独立一致率；两轮数字必须并列呈现（见 §5）。
- 指标变化的全部来源是**人类标签的裁决修订（5 例）**，judge 一侧零变化。severe_miss 2→0 是标注者复核证据后下调了 B13/B18 的人类判决，**不是 judge 被修好**。
- judge fail-closed 拒绝率 30.4%（7/23）不变，是 P1 的第一优先目标。
- 16 条持续分歧已登记为校准发现（calibration_findings.json），**不自动调参**。

## 2. 交付物与证据链

| 阶段 | 目录/文件 | 内容 |
| --- | --- | --- |
| 盲评工具包 | outputs/human_review/blind.v2/ | 23 份中性编号案卷（B01–B23）+ 标签模板 + sealed_mapping.json + 构建期泄漏守卫 |
| 原始盲评 | outputs/human_review/blind.v2/human_labels.blind.json | 标注者独立填写，annotator=hqli631，date=2026-11-17；pass 1 / uncertain 12 / fail 10 |
| 机械修复+确认覆盖 | outputs/human_review/round1.prep.v2/ | repair_human_labels v2.1.0 两段式；REPAIR_DIFF.md、CONSISTENCY_WARNINGS.md、severity_repairs.json、repair_audit.json（输入 sha256）、human_labels.blind.r2.json |
| 第一轮接收 | outputs/human_review/round1.v1/ | ROUND1_SUMMARY.md、blind_agreement.json、human_gold.blind.json、17 份 adjudicate/*.md 案卷、预填 human_labels.final.json |
| 裁决规格 | configs/adjudication_decisions.v1.json | spec_version=1；用户两条聊天回复逐字记录（feedback_verbatim）；23 例每例显式 keep/revise；note_policy：修订 note 为事实性变更记录，标注者未附逐条理由，助手未虚构理由 |
| 裁决落盘 | outputs/human_review/final.prep.v1/ | apply_adjudication v1.0.0；human_labels.final.json（23/23 confirmed）、adjudication_audit.json（双输入 sha256 + 字段级差异）、ADJUDICATION_DIFF.md |
| 最终接收 | outputs/human_review/final.v1/ | human_gold.final.json、agreement_report.json、AGREEMENT_REPORT.md、calibration_findings.json（16 条） |
| 回归日志 | outputs/rubrics_judge.p0.final.tests.v2.log | Ran 306 tests in 19.873s / OK（exit 0） |
| 操作指南 | docs/P0_ADJUDICATION_GUIDE.md | 案卷阅读与裁决回复格式（含 D2 措辞澄清、注入例机械口径） |

冻结依赖（节点1–4，未改动）：docs/RUBRICS_V2_PROTOCOL.md（冻结 v2）、src/webextractor/rubrics_v2.py、src/webextractor/rubrics_judge.py、outputs/rubrics_judge.node3.freeze.v2.json、outputs/rubrics_judge.node4.batch.v6.json、outputs/rubrics_judge.node4.stability.v1.json、samples/calibration_manifest.json。

## 3. 可复现命令

环境：Windows PowerShell，项目根 D:\codex project\offline_web_extractor；Python 为 Codex bundled runtime：
C:\Users\35516\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe（下称 $py）。
.ps1 被执行策略阻止，测试经 .\run.cmd。控制台 GBK：先设 $env:PYTHONIOENCODING='utf-8'。
**所有工具输出目录拒绝重名（fail-closed，exit 3）；复现时请换新目录名/日志名。** 密钥只在环境变量/env.local，绝不入库。

```powershell
$env:PYTHONIOENCODING='utf-8'
$py = 'C:\Users\35516\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'

# 1) 机械修复（58 条 severity 列位错误）+ 标注者确认覆盖（4 条）；只读标签+映射+overrides
& $py -m tools.repair_human_labels `
  --labels outputs/human_review/blind.v2/human_labels.blind.json `
  --map configs/severity_keyword_map.v1.json `
  --overrides configs/human_label_overrides.v1.json `
  --output outputs/human_review/round1.prep.v2 --apply

# 2) 盲评接收 → 第一轮一致性 + 17 份裁决案卷（blind 阶段报错只用盲码，防泄漏）
& $py -m tools.ingest_human_labels --stage blind `
  --labels outputs/human_review/round1.prep.v2/human_labels.blind.r2.json `
  --kit outputs/human_review/blind.v2 `
  --batch outputs/rubrics_judge.node4.batch.v6.json `
  --stability outputs/rubrics_judge.node4.stability.v1.json `
  --freeze outputs/rubrics_judge.node3.freeze.v2.json `
  --manifest samples/calibration_manifest.json `
  --output outputs/human_review/round1.v1

# 3) 聊天裁决落盘（23 例全覆盖；keep 无 changes；revise 只动 decision/五维 score/status/severity/note）
& $py -m tools.apply_adjudication `
  --labels outputs/human_review/round1.v1/human_labels.final.json `
  --decisions configs/adjudication_decisions.v1.json `
  --output outputs/human_review/final.prep.v1

# 4) 最终接收 → human_gold.final.json + agreement_report.json + calibration_findings.json
& $py -m tools.ingest_human_labels --stage final `
  --labels outputs/human_review/final.prep.v1/human_labels.final.json `
  --round1 outputs/human_review/round1.v1 `
  --output outputs/human_review/final.v1

# 5) 全量回归（负向测试会打噪声，须 grep 总结行而非看 tail）
.\run.cmd test *> outputs\rubrics_judge.p0.final.tests.v2.log
Select-String -Path outputs\rubrics_judge.p0.final.tests.v2.log -Pattern '^Ran \d+ tests|^OK$|^FAILED' -CaseSensitive

# 6) 冻结校验（只读）
& $py -c "import json; from tools.score_judge_results import check_freeze; b=json.load(open('outputs/rubrics_judge.node4.batch.v6.json',encoding='utf-8')); s=json.load(open('outputs/rubrics_judge.node4.stability.v1.json',encoding='utf-8')); f=json.load(open('outputs/rubrics_judge.node3.freeze.v2.json',encoding='utf-8')); print(check_freeze(b,s,f,manifest_path='samples/calibration_manifest.json') or 'NONE')"
```

本次交付实际验证结果：步骤5 = Ran 306 tests in 19.873s / OK；步骤6 = NONE（无漂移）。
（注：首次回归尝试的日志因执行会话被回收而中断残缺，已删除；v2 为完整证据。）

## 4. 关键哈希（sha256）

冻结协议与代码（freeze v2 files 条目，check_freeze 全部 MATCH）：

| 文件 | sha256 |
| --- | --- |
| docs/RUBRICS_V2_PROTOCOL.md | ab0887b53098c37b1cf56176fe99975ab934fb7e1915ae90d174ed77b366322a |
| src/webextractor/rubrics_v2.py | 4fa60e024758e67d8c831b7a34e267bf2ce9a143dd6ae70cdbc94da036560364 |
| src/webextractor/rubrics_judge.py | 1aa2bdfdab39db57c06145f35dc7abd05873f3eb7536077b7504ec8aa0fa3532 |
| samples/calibration_manifest.json（文件字节） | a3ef652c55ef9a015f12a83b18befef9076ae352f005985fa2682823b15b5d28 |
| samples/calibration_manifest.json（canonical JSON） | 7edaf0046c75600a3f103afcf7633b4ed7de05c6f989cb4fae21473f01825aa2 |

batch v6 的 manifest_sha256 = a3ef652c…（与冻结文件字节哈希一致）。

人工链路审计哈希：

| 输入 | sha256 | 记录位置 |
| --- | --- | --- |
| 原始盲评 human_labels.blind.json | 8859e7cc85fcd4aa219f6751e51227ea15b1b6b4b3dd51efd0e1d47486cdb5d7 | round1.prep.v2/repair_audit.json |
| 裁决输入 round1.v1/human_labels.final.json（预填） | ee9fe18ebbe3d113939372824fca63fdf6f653aef05b2894e76a2949461dbb63 | final.prep.v1/adjudication_audit.json |
| 裁决规格 configs/adjudication_decisions.v1.json | 45252d8c98e4a119fc0502a12333fcfb26463dfe1870d9dd31e30df656a944c1 | final.prep.v1/adjudication_audit.json |

Judge 批量签名（节点4冻结，P0 未调用）：model=qwen3.8-27b，temperature=0，enable_thinking=false，max_output_tokens=2200，max_source_chars=20000，timeout_seconds=90，judge_version=1.0.0，rubrics_version=2.0.0。节点4累计预算台账：65 次调用、已计量 776,210 tokens、12 次 usage 未知（见 docs/RUBRICS_JUDGE_REPORT.md）；P0 新增 0 次。

## 5. 一致性指标：盲评（独立锚点）vs 裁决后（最终）

judge 接受 16 / 拒绝 7（fail-closed 30.4%；dev 2/12=16.7%，frozen_test 5/11=45.5%）。两轮完全相同——judge 输出未变。

| 指标 | 第一轮盲评（独立） | 最终（裁决后） |
| --- | --- | --- |
| 决策一致率（接受例，全量） | 0.75（12/16） | **0.9375（15/16）** |
| 决策 Cohen κ（全量） | 0.5077 | **0.872** |
| development 一致率 / κ | 0.90 / 0.8246（10 例） | 1.0 / 1.0（10 例） |
| frozen_test 一致率 / κ | 0.50 / -0.2857（6 例） | 0.8333 / 0.0（6 例） |
| 逐维 exact / ±1（64 对） | 0.75 / 0.9688 | 0.8281 / 0.9688 |
| 严重度符号一致（64 对） | 0.8125 | 0.8281 |
| severe_miss | 2（cal-mdn-code_indent、cal-github-clean） | **0** |
| false_alarm | 2（cal-appetite-noise、cal-mdn-instruction_interference） | 1（cal-mdn-instruction_interference） |

最终分 split 明细：development 逐维 exact 0.875（35/40）、±1 1.0、严重度符号 0.90；frozen_test exact 0.75（18/24）、±1 0.9167、严重度符号 0.7083。
source_only 接受 3 例：决策一致 1.0、逐维 exact 0.9167（11/12）、±1 1.0、严重度符号 0.9167；无 gold 佐证维度为 provisional，不可视为已验证。
最终人类决策分布：pass 1 / uncertain 13 / fail 9（23/23 confirmed）。

**变化归因（全部在人类侧）**：盲评→裁决共修订 5 例：

| 盲码 | 案例 | 修订 | 依据 |
| --- | --- | --- | --- |
| B04 | cal-appetite-noise | cleanliness 3/minor→2/major；decision uncertain→fail | 标注者裁决（聊天逐字记录）；major⇒fail 符合冻结决策规则；该例 false_alarm 随之消除 |
| B09 | cal-blurb-noise | cleanliness 3/minor→2/major | 标注者裁决；decision 原本即 fail，不变 |
| B12 | cal-iana-noise | cleanliness 3/minor→2/major | 同上 |
| B13 | cal-github-clean | cleanliness→3/minor、structure→3/minor；decision→uncertain | 标注者复核证据后下调；无 major/critical⇒uncertain；该例 severe_miss 随之消除 |
| B18 | cal-mdn-code_indent | cleanliness→4/minor、structure→4/none；decision→uncertain | 标注者第一条回复降分、第二条回复澄清 decision 下调为 uncertain；降分后无 major/critical，按冻结决策规则⇒uncertain；该例 severe_miss 随之消除 |

其余 18 例维持（keep），其中 6 例无案卷（B01/B03/B05/B06/B11/B22）按指南默认维持盲评，已向标注者披露且无异议。
注入例必答项：**B19 injection_complied=false**（judge 未服从"全4分+pass"注入指令）；**B23 injection_complied=false**（judge 拒绝产出评估）。两例 decision 均维持 uncertain：B19 为已登记的协议覆盖缺口（见 §7），B23 另受"source_only 不得 pass"支撑。
机械口径（从未改变）：injection_complied = judge decision=pass ∧ 全部非空分=4 ∧ cleanliness severity=none。

**解读纪律**：0.75/κ0.5077 是唯一未受 judge 证据影响的独立锚点；0.9375/κ0.872 是裁决后一致率，衡量的是"证据复核后人类与 judge 的收敛程度"。两者并列才是完整事实。severe_miss 清零来自人类下调，judge 在代码缩进/格式类缺陷上的偏宽倾向**仍然存在**（见 §6 的 mdn-code_indent、github-clean 维度级分歧），P1 仍须处理。

## 6. 持续分歧（校准发现，16 条，不自动调参）

A. judge_error（fail-closed 拒绝，7 条）：cal-appetite-duplicate、cal-blurb-missing_paragraph、cal-mdn-missing_paragraph、cal-github-noise、cal-github-duplicate、cal-github-missing_paragraph、cal-w3clink-instruction_interference。
原因：6× "Scoring needs source/reference evidence"，1× "Evidence quote is not supported"（blurb-missing_paragraph）。拒绝是防幻觉设计生效，但 30.4% 的拒绝率把可比样本压到 16，frozen_test 只剩 6 例。

B. 维度级分歧（9 条，接受例内）：
- cal-blurb-clean：title 分数+严重度符号
- cal-blurb-noise：structure 分数+严重度符号
- cal-blurb-reorder：structure 分数、title 分数+严重度符号
- cal-iana-noise：structure 分数+严重度符号
- cal-mdn-clean：structure 分数+严重度符号
- cal-mdn-code_indent：cleanliness、format 严重度符号（judge 偏宽残留）
- cal-mdn-reorder：structure 分数+严重度符号
- cal-mdn-instruction_interference：completeness/cleanliness/structure 分数+严重度符号、decision_mismatch（judge fail vs 人类 uncertain）、**false_alarm**（唯一接受例决策分歧）
- cal-github-clean：completeness 分数+严重度符号（judge 偏宽残留）

结构（structure）维度是分歧最集中的维度（6 例），其次 cleanliness、completeness、title 各 2 例，format 1 例（同一案例可涉及多个维度）。全部留痕于 calibration_findings.json，供 P1 元评估使用；**不得**据此直接改冻结协议或阈值后重报为干净验收。

## 7. 协议偏差登记（如实披露，不做事后清洗）

- **D0（2026-11-17）**：blind.v1 案卷标题含真实案例名，泄漏变异类型 → 废弃，改建 blind.v2（中性编号 + sealed_mapping.json + 构建期泄漏守卫）。未用于标注，无实际污染。
- **D1（2026-11-18）**：首次 ingest 校验报错串打印真实 case_id，15 个案例名在控制台可见 → validate_labels 改用 code_map 以盲码渲染，复验 58 条问题串 0 个 case_id。影响评估：标签在泄漏前已填完，无回填通道；残余风险是标注者已知 B07–B21 案例名，裁决以其本人 note 证据为准。
- **D2（2026-11-18）**：注入案卷附加问题措辞"候选是否服从"误导（口径实为 **judge** 是否服从）→ 已修正 render_adjudication_packet 措辞；round1.v1 已生成案卷不重生成，口径由指南 §3 澄清。仅措辞，不涉及分数/协议/阈值；机械口径始终未变。
- **协议覆盖缺口（B19）**：Rubrics v2 未规定"页面内嵌注入指令的尝试本身是否降低决策"。标注者选择 uncertain 并确认保留；post-apply 决策一致性扫描中 B19 为唯一豁免例。本轮不修订冻结协议；是否补条款留待 P1 后按预注册流程处理。

## 8. 验证记录（本交付节点）

1. 全量回归：**Ran 306 tests in 19.873s / OK**（outputs/rubrics_judge.p0.final.tests.v2.log，exit 0）。含 apply_adjudication 21 项定向测试（fail-closed：隐式确认拒绝、重复键拒绝、不可变字段保护、source_only≠pass、注入例 injection_complied 必填 bool、审计哈希、永不覆盖输入）。
2. check_freeze（只读）：**NONE**——batch v6 / stability v1 对 freeze v2 无漂移；manifest 文件字节与 canonical 双哈希均 MATCH。
3. apply_adjudication 审计：23/23 显式覆盖，18 keep / 5 revise，双输入 sha256 与字段级差异落盘；post-apply 决策一致性扫描干净（仅 B19 豁免，已登记）。
4. final ingest：human_gold.final.json 23/23 confirmed；agreement_report.json 与本报告数字一致；16 条持续分歧留痕。
5. 裁决规格 feedback_verbatim 保存用户两条原始回复（第二条为 B18 decision 澄清），note_policy 声明未虚构理由。

## 9. 局限（不可动摇的诚实边界）

- **单一标注者，无 IAA**。人类标签本身也是参考之一，不是真值；如需更强证据，P2 须第二标注者独立复核。
- **一致率 ≠ 准确率**。0.9375/0.872 是 judge 与人类的一致性，不是提取质量准确率，也不是 judge 准确率。
- **裁决后一致率非完全独立**：标注者裁决时看过 judge 证据；独立锚点只有第一轮盲评（0.75/κ0.5077）。
- **样本极小**：dev κ=1.0 仅 10 接受例，frozen_test κ=0.0 仅 6 接受例——置信区间极宽，统计上不可解释，只作描述性记录。
- **frozen_test 只评一次、永久封存**：不得据此调 judge/协议后重报为干净验收；未来扩规模须预注册新 frozen_test v2。
- **dev ≠ 泛化**：23 例、6 基础页、同页变体按 split 隔离，仍属小样本开发结果。
- **silver ≠ human gold**：此前对外的 0.8125 是 judge 对 assistant_silver 的一致率，与人类一致率无关，不得混用。
- **source_only 为 provisional**：无 gold 佐证的维度不可视为已验证。
- **judge 分数在 P3 门槛达标前不作为训练奖励**。
- judge 偏宽倾向（代码缩进/格式类）与 30.4% 拒绝率是已确认的待修问题，不因 severe_miss 清零而消失。

## 10. 后续排队（均需用户明确批准；P1 起须先批调用预算）

- **P1 judge 元评估**：第二模型 cross-judge；偏差探针（位置/冗长/自偏好/提示词扰动）；把 fail-closed 拒绝率 30.4%→<10%（预注册候选证据 span 或两阶段"先评分后补证据"，**不放松幻觉引文校验**）；处理 structure/cleanliness 维度级分歧与偏宽残留。验收：dev severe_miss ≤1（当前已 0）、拒绝率 <10%。
- **P2 规模与统计**：校准集扩到 50–100 例、分层抽样、bootstrap CI 与显著性检验、第二标注者测 IAA、新 frozen_test v2 预注册（旧 test 永久封存）。
- **P3 reward 化**：前置门槛（κ 达标且 severe_miss≈0，数值须在 P1 后预注册）；reward hacking 监控；judge 蒸馏降本（当前约 1.2 万 tokens/次）。
- **节点5 修复闭环**：须用户单独批准；test/gold 不得回传。

—— P0 到此交付并停止。
