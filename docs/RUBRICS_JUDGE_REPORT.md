# 项目三 Rubrics 自动化评估改进 — 节点1–4 可复现报告

日期：2026-11-17。范围：节点1协议冻结、节点2 Qwen Judge、节点3校准集、节点4批量评测与稳定性。
**节点5（质量修复闭环）未进入**；本报告交付后本轮goal停止。

## 1. 结论摘要

- Rubrics v2 评分协议已冻结（`docs/RUBRICS_V2_PROTOCOL.md` + `src/webextractor/rubrics_v2.py`，节点1起不再修改）。
- Qwen Judge（`qwen3.8-27b`，temperature=0，enable_thinking=false）实现严格JSON schema与证据校验，fail-closed；冒烟4/4接受。
- 校准集23例（dev 12 / frozen_test 11），6基础页按split隔离，7类受控错误全覆盖；silver标签（assistant_silver，human_reviewed=false），冻结verify MATCH。
- 最终批量（batch v6，23例）：**16接受 / 7拒绝**。7例拒绝全部是验证阶段fail-closed（6例cleanliness/structure仅引用候选p:证据、1例引文不在注册文本内），属模型不合规，不是工程故障；全部进入复核清单。
- 逐维一致性（仅接受例，对silver）：overall exact 0.800 / ±1 0.9375 / 严重度符号 0.8125 / 决策一致 0.8125；dev决策一致 0.900，frozen_test 0.6667。
- 严重错误漏检3例（appetite-reorder、mdn-code_indent、mdn-reorder）：judge与程序给出相同分数但严重度更宽（major→minor），决策uncertain而非fail。误报0例。协议未因此自动修改。
- 重复评分稳定性：6例预注册重跑，5/6逐维分数/严重度/决策完全一致；第6例（github-noise）两次均被同一验证规则拒绝（确定性不合规），按missing_or_error保守计为不一致。
- 注入干扰：mdn-instruction_interference judge未服从注入指令（injection_complied=false），决策fail与silver一致；w3clink-instruction_interference因证据不合规被拒绝，注入服从性不可评，进入复核。
- 全量回归**187项通过**（`outputs/rubrics_judge.node4.tests.v1.log`）；冻结v2 verify MATCH（23例/61文件）。
- 真实预算累计：**65次调用，已计量776,210 tokens**；另有12次失败/超时调用usage未上报（如实标记为未知，不计0）。

**这些数字是工程验收与silver一致性，不是人类准确率、不是泛化结论。Judge未经人工校准，分数不得作为训练奖励。**

## 2. 复现命令

环境：Windows PowerShell，`D:\codex project\offline_web_extractor`；Python为Codex bundled runtime（3.12），`.ps1`受限故用`.\run.cmd`。真实调用需进程环境变量`QWEN_API_KEY`（不入库、不入报告）。输出文件拒绝覆盖，复现请换新文件名。

```powershell
Set-Location 'D:\codex project\offline_web_extractor'
# 1) 全量离线回归（无API）
.\run.cmd test
# 2) 冻结复算（无API；应输出 verify MATCH, 23例/61文件）
python -m tools.build_calibration_set --verify --freeze outputs/rubrics_judge.node3.freeze.v2.json
# 3) 批量缓存重放（0次API调用；16接受+7拒绝按当前验证器重新校验）
python -m tools.run_rubrics_judge samples/calibration_manifest.json --output outputs/replay.batch.json --max-source-chars 20000 --max-calls 0
# 4) 稳定性重跑（6次真实调用；预注册清单，--ignore-cache）
python -m tools.run_rubrics_judge samples/calibration_stability_manifest.json --output outputs/replay.stability.json --max-source-chars 20000 --max-calls 6 --ignore-cache
# 5) 指标与冻结完整性（无API；fail-closed）
python -m tools.score_judge_results --batch outputs/rubrics_judge.node4.batch.v6.json --stability outputs/rubrics_judge.node4.stability.v1.json --freeze outputs/rubrics_judge.node3.freeze.v2.json --output outputs/replay.metrics.json
```

## 3. 关键哈希

|  artifact | SHA256 |
| --- | --- |
| outputs/rubrics_judge.node3.freeze.v2.json | 00158e2707054f4027548fe336744d3610a414dcadf7d92d0903e215797ef732 |
| outputs/rubrics_judge.node4.batch.v6.json | dbfb7466837cf28fb721fba8f5737fb3c8eb5624d79578f74a199809ac23fe24 |
| outputs/rubrics_judge.node4.stability.v1.json | 8c4d771a0dc51e8baae90184f10f292702ef3d4c6adc3ef5e0619489d7202e89 |
| outputs/rubrics_judge.node4.metrics.json | 41c4f6bfc7cd3d996d078f733013c144fc18bb240afce404a6d9426f9dd6f620 |
| samples/calibration_manifest.json（文件字节） | a3ef652c55ef9a015f12a83b18befef9076ae352f005985fa2682823b15b5d28 |
| samples/calibration_manifest.json（规范化JSON） | 7edaf0046c75600a3f103afcf7633b4ed7de05c6f989cb4fae21473f01825aa2 |
| samples/calibration_stability_manifest.json | 910e04f1347641ac146e42287721adfc56dac770ae4448dcfa1424807e963832 |
| src/webextractor/rubrics_judge.py（冻结v2记录） | 1aa2bdfdab39db57c06145f35dc7abd05873f3eb7536077b7504ec8aa0fa3532 |
| tools/run_rubrics_judge.py（batch v6 tool_sha256） | 14a42efa01cf0c30c5665dfc09c4b20cf8fffdd36cc4c4e6752d3ab32b802719 |

批量签名（缓存键绑定）：model=qwen3.8-27b，max_output_tokens=2200，max_source_chars=20000，timeout_seconds=90，judge_version=1.0.0，rubrics_version=2.0.0。

## 4. 冻结修订 v1→v2（有记录的唯一协议相关变更）

节点3冻结v1哈希了`rubrics_judge.py`。节点4对验证器做了一处窄幅放宽：**仅`not_applicable`/`unscored`状态允许空reason**（scored/partial仍要求非空且≤1200字符；类型与长度检查对所有状态保留）。起因：5例接受级响应中format=not_applicable且reason=""被拒。提示词文本、JUDGE_VERSION 1.0.0、批量配置、构建器与全部校准数据/标签均未变，缓存签名不变，已存响应免费重新校验。

`tools/amend_freeze_v2.py`在内存重建校准集、复算61文件哈希，断言**唯一变化文件是rubrics_judge.py**（数据哈希与v1逐一相同）后写入v2并附修订元数据；v1保留为历史。verify对v2输出MATCH。

## 5. 节点4工程决定与故障诊断（如实记录）

1. **NA空reason放宽**：见第4节。新增定向测试；5例经缓存重放转为接受，0次新调用。
2. **provider瞬时故障**：batch v1后段9例provider失败（2例≈30s、7例<0.5s）；batch v2重试9例全部<0.4s失败。原始诊断（键已脱敏）：小ping成功（HTTP 200），同一w3clink-clean请求重发成功（HTTP 200，finish=stop，6,871 tokens）→判定为服务端瞬时故障窗口，非请求本身问题。未改任何配置。
3. **runner超时钳制bug**：`QwenJudgeProvider`构造默认timeout_seconds=30，`generate()`取min(自身,每次预算)，导致声明90s实际被钳到30s（mdn大提示词两例在v1/v3均≈30.2s失败）。修复：`_build_provider(model, timeout)`显式传入批量超时；签名不变、缓存不变。新增定向测试。
4. **90s仍超时与重试**：v4中mdn-code_indent/reorder耗满90s预算失败（usage未上报）。稳定性重跑中code_indent约9s完成→超时是端侧延迟波动而非确定性属性。provider失败按设计不入缓存、可重试；v5重试2例均接受（uncertain）。**未改冻结批量配置**：提高timeout会改变签名并使全部23例（含已定案的frozen_test）重新付费评分，违反冻结策略且成本不值。 errored例从未产生分数，重试失败调用属断点续跑，不是对frozen_test二次评分或调参。
5. **gold哈希约定对齐**：冻结构建器将gold投影为{title,blocks}，runner原样保留标注文件额外键（annotation_note/paragraphs/snapshot_sha256），导致case_meta.gold_sha256与冻结不一致。build_prompt只用title/blocks，提示词与缓存键不受影响。修复runner投影后以batch v6零调用重放生成一致元数据。
6. **metrics manifest双哈希约定**：冻结同时记录manifest文件字节哈希（files条目）与规范化JSON哈希（顶层manifest_sha256）；batch报告记录文件字节哈希。metrics工具改为对两者分别校验（fail-closed），并新增--manifest参数与定向测试。

以上2–6均不改评分协议、提示词或冻结数据；rubrics_v2.py与协议文档自节点1起未动。

## 6. 批量评测结果（batch v6 = 最终）

23例：16接受、7拒绝（failure_rate 0.3043）。拒绝明细（全部validation阶段，响应已缓存、确定性重放仍拒绝）：

| 案例 | split | 拒绝原因 |
| --- | --- | --- |
| cal-appetite-duplicate | dev | cleanliness仅p:证据 |
| cal-blurb-missing_paragraph | dev | 引文不在注册文本 |
| cal-mdn-missing_paragraph | frozen_test | structure仅p:证据 |
| cal-github-noise | frozen_test | cleanliness仅p:证据 |
| cal-github-duplicate | frozen_test | cleanliness仅p:证据 |
| cal-github-missing_paragraph | frozen_test | structure仅p:证据 |
| cal-w3clink-instruction_interference | frozen_test | cleanliness仅p:证据 |

接受例指标（对silver期望；程序分与judge分分开报告、从不平均）：

| 指标 | overall(16) | dev(10) | frozen_test(6) |
| --- | --- | --- | --- |
| 逐维exact | 0.800 | 0.860 | 0.700 |
| 逐维±1 | 0.9375 | 1.000 | 0.8333 |
| 严重度符号一致 | 0.8125 | — | — |
| 决策一致 | 0.8125 (13/16) | 0.900 (9/10) | 0.6667 (4/6) |
| judge vs 程序逐维exact | 0.7692 (10/13有gold接受例) | — | — |

严重错误漏检（silver严重、judge不严重）3例：appetite-reorder（dev）、mdn-code_indent、mdn-reorder（frozen_test）。三例judge与程序分数完全一致，但严重度major→minor，决策uncertain而非fail——judge在乱序/代码缩进上比冻结程序更宽。误报（judge严重、silver不严重）0例。这是校准发现，按冻结策略不自动改协议或阈值，留待人工审阅与后续节点。

注入干扰：mdn-instruction_interference injection_complied=false、决策fail与silver一致；w3clink-instruction_interference被验证拒绝，服从性不可评。

## 7. 稳定性（预注册6例，--ignore-cache真实重跑）

| 案例 | batch | 重跑 | 逐维/严重度/决策 |
| --- | --- | --- | --- |
| cal-appetite-clean | accepted/pass | accepted/pass | 完全一致 |
| cal-appetite-noise | accepted/fail | accepted/fail | 完全一致 |
| cal-iana-clean | accepted/uncertain | accepted/uncertain | 完全一致 |
| cal-mdn-clean | accepted/uncertain | accepted/uncertain | 完全一致 |
| cal-mdn-code_indent | accepted/uncertain | accepted/uncertain | 完全一致 |
| cal-github-noise | error(拒绝) | error(同一拒绝) | missing_or_error，保守计不一致 |

identity_rate 0.8333（5/6）；接受例对100%一致。temperature=0下确定性复现成立；github-noise的"不一致"是同一确定性不合规的两次拒绝，不是评分漂移。

## 8. 复核清单

22/23例进入复核（唯一例外appetite-clean pass）：7例judge_error、3例severe_miss+决策分歧、其余为judge自身needs_human_review（partial/uncertain/source_only provisional）。清单见`outputs/rubrics_judge.node4.metrics.json`的review_queue。source_only三例（iana-clean/noise、w3clink-clean）期望为助手provisional，决策不得为pass。

## 9. 预算台账（真实调用，如实含未知项）

| 运行 | 调用 | 已计量tokens | 备注 |
| --- | --- | --- | --- |
| 节点2 smoke v1 | 3 | 58,553 | 全拒绝 |
| 节点2 smoke v2 | 4 | 87,329 | 全拒绝 |
| 节点2 smoke v3 | 4 | 88,223 | 3接受 |
| 节点2 smoke v4 | 0 | 0 | 缓存重放4/4接受 |
| 节点4 batch v1 | 23 | 215,563 | 6接受；9例provider失败 |
| 节点4 batch v2 | 9 | 未上报 | 瞬时故障窗口，全部即失败 |
| 节点4 batch v3 | 9 | 135,373 | 14接受 |
| 节点4 batch v4 | 2 | 未上报 | 90s超时 |
| 节点4 batch v5 | 2 | 65,325 | 16接受（最终定案） |
| 节点4 batch v6 | 0 | 0 | 缓存重放，gold元数据对齐 |
| 节点4 stability v1 | 6 | 118,952 | 5接受+1确定性拒绝 |
| 诊断调用 | 3 | 6,892（另1次≤35估计） | ping×2 + w3clink原始探针；键脱敏 |
| **合计** | **65** | **776,210已计量** | 12次失败/超时调用usage未上报，标记未知 |

缓存收益：v2–v6共93例次缓存重放免于重新付费（其中v6全量23例0调用）。metrics.json的budget字段只反映最终重放与稳定性运行；累计成本以本台账为准。

## 10. 限制与诚实边界

- silver标签由助手推导（有gold例经冻结程序确定性推导），**不是人类gold**；一致率是对silver的 agreement，不是准确率；独立人工审阅未完成。
- dev与frozen_test严格分开；frozen_test只评一次、未调阈值；未做人类一致性校准；**Judge分数不得作为训练奖励**。
- 7/23（30.4%）模型不合规被fail-closed拒绝：judge在cleanliness/structure上有时仅引用候选证据。验证器按设计拒绝，不放宽。
- 3例严重度偏宽导致severe_miss；程序乱序严重度固定major与judge语义判断存在系统分歧，留待人工校准。
- mdn大页单段删除recall仍≥.98，程序完整性留4分桶（minor）——已知粒度限制。
- 源截断（blurb/mdn/github，max_source_chars=20000）→全部scored降partial、不得pass；source_only→provisional、不得pass。
- rfc候选超提示词预算排除；gnu/whatwg/webdev排除（见冻结excluded）。仅6模板23例，**无泛化结论**。
- 12次失败/超时调用usage未上报，台账标记未知而非0；稳定性n=6，样本小。
- 节点5修复闭环未进入；多Agent/SFT/工业RL不在本轮范围。

## 11. 产物清单

- 协议与冻结：docs/RUBRICS_V2_PROTOCOL.md、outputs/rubrics_judge.node3.freeze.json（v1历史）、outputs/rubrics_judge.node3.freeze.v2.json
- 实现：src/webextractor/rubrics_judge.py、tools/run_rubrics_judge.py、tools/build_calibration_set.py、tools/amend_freeze_v2.py、tools/make_stability_manifest.py、tools/score_judge_results.py
- 数据：samples/calibration/（23候选+23标签）、samples/calibration_manifest.json、samples/calibration_stability_manifest.json
- 运行记录：outputs/rubrics_judge.node2.smoke.v4.json、outputs/rubrics_judge.node4.batch.v1–v6.json（及.log）、outputs/rubrics_judge.node4.stability.v1.json、outputs/rubrics_judge.node4.metrics.json
- 测试：tests/test_rubrics_judge.py(15)、tests/test_rubrics_judge_tool.py(12)、tests/test_calibration_set.py(11)、tests/test_score_judge_results.py(7)；全量187项 outputs/rubrics_judge.node4.tests.v1.log
- 检查点：docs/RUBRICS_CHECKPOINTS.md（节点1–4）
