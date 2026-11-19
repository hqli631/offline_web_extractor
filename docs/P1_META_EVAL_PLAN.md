# P1 Judge 元评估 · 预注册方案（调用前冻结）

日期：2026-11-18（Asia/Shanghai）。状态：**预注册已固定，模型调用尚未发生，等待用户批准预算**。
本文件在任何 P1 模型调用之前写定；假设、设计、阈值、回退规则与预算一经批准不得事后修改。如需变更，须新增修订记录并说明理由，旧版保留。

## 0. 诚实边界（继承 P0，不可动摇）

silver ≠ human gold；一致率 ≠ 准确率；dev ≠ 泛化；**frozen_test 在 P1 全程不重跑、不调参、永久封存至 P2 新预注册测试集**；单一标注者无 IAA；judge 分数在 P3 门槛达标前不作训练奖励。P0 最终一致率 0.9375/κ0.872 是裁决后数字，独立锚点仍是盲评 0.75/κ0.5077。P1 的一切验收只在 development（12 例）上对照 **human_gold.final.json**（P0 裁决后人类标签）计算。

## 1. 零调用诊断证据（2026-11-18，离线重放 node4 batch v6 缓存）

7 例 fail-closed 拒绝的逐维定位（重放缓存响应，无新调用）：

| 案例 | split | 失败维度 | 失败规则 | 具体 |
| --- | --- | --- | --- | --- |
| cal-appetite-duplicate | dev | cleanliness | Scoring needs source/reference evidence | 仅引 p:0,p:1（重复块），无 s:/g: |
| cal-blurb-missing_paragraph | dev | structure, title | Evidence quote is not supported | s:78/s:79/s:75 引文空白转录失配 |
| cal-mdn-missing_paragraph | frozen_test | structure | Scoring needs source/reference evidence | 仅 p:1,p:9,p:12 |
| cal-github-noise | frozen_test | cleanliness | 同上 | 仅 p:1,p:11,p:23 |
| cal-github-duplicate | frozen_test | cleanliness, structure | 同上 | 仅 p:N |
| cal-github-missing_paragraph | frozen_test | cleanliness, structure | 同上 | 仅 p:N |
| cal-w3clink-instruction_interference | frozen_test | structure | 同上 | 仅 p:0,p:1 |

**模式 1（6/7）**：cleanliness/structure 评分只引候选块 p:N，缺 s:/g: 证据。与 P1 计划预判一致。
**模式 2（1/7）**：blurb 的 structure/title 引文与源节点文本空白不一致。根因实证：registry s:75 = 'What is Python?  Executive Summary'（双空格），模型引文为单空格；s:78/s:79 源文本含 \r\n，模型引文规范化为空格/截断。**属转录容差问题，非幻觉**（词序内容真实存在于被引节点）。

dev 当前拒绝 2/12 = 16.7%（appetite-duplicate、blurb-missing_paragraph）。验收目标 <10% 即 ≤1/12。

## 2. 假设（预注册）

- **H1**：为各维度提供"证据菜单"（预计算 {ref, quote} 精确子串对）可消除模式 1 拒绝——模型可直接照抄含 s:/g: 的现成证据，不再因找不到源引用而只引 p:N。
- **H2**：引文匹配改为"空白折叠后精确子串"可消除模式 2 拒绝——容忍空白转录差异，但词序与非空白字符仍须逐字存在于被引节点，幻觉防护不放松。
- **H3**：v1.1.0 在 dev 上达到拒绝率 <10% 且 severe_miss ≤1（对照 P0 最终人类标签），且决策一致率/κ 不劣于 P0 最终 dev 水平（1.0/1.0）超过 1 例。
- **H4**（描述性，无验收阈值）：第二 Qwen 模型 cross-judge 的 judge 间一致率首次测量，识别模型特异性偏差。
- **H5**（描述性，无验收阈值）：证据位置扰动与中性提示词扰动下的评分稳定性首次测量。

H1/H2 针对不相交失败模式，归因清晰：离线重放可证 H2 单独修复 blurb（模式 2），H1 针对其余 6 例（模式 1）。

## 3. 设计规格（judge v1.1.0，仅改 src/webextractor/rubrics_judge.py）

### 3.1 证据菜单（prompt 层，新增顶层键 evidence_menus）

- 对每个维度预计算建议证据列表 [{ref, quote}]；quote = registry[ref] 的**精确前缀**（≤120 字符），构造上保证通过子串校验。
- 菜单是**建议非限制**：模型可照抄菜单项，也可自引任何 registry 内 ref 的精确子串；s:/g: 引用规则不变。
- 来源仅限 prompt 可见数据（source_nodes / registry / candidate / gold-as-silver-annotation）；**绝不读取人类标签、silver 分数、批量指标或 sealed_mapping**。
- 确定性构造（固定顺序、固定上限），无随机：
  - completeness：with_gold → g:N（≤10）+ g:title；source_only → s:N 内容节点（p/pre/li/dt/dd/td/th，≤10）。
  - cleanliness：s:N 噪声嫌疑节点（≤10）+ g:N（≤10，with_gold）。噪声嫌疑 = xpath 祖先含 nav/aside/footer/header/form，或文本（小写）命中冻结 boilerplate 关键词表。
  - structure：s:N 标题/列表节点（h1–h6/li，≤16）+ g:N（≤10，with_gold）。
  - title：p:title、g:title（非空时）+ s:N h1（≤3）。
  - format：s:N pre 节点（≤8）。
- **预算自适应（R1）**：菜单 quote 前缀长度取 {120, 60, 30} 中使 prompt ≤ max_prompt_chars(110000) 的最大者；皆不容则菜单为空（base prompt 仍须 ≤ 预算）。确定性、逐案例固定。dev 案例（appetite/blurb/iana，21–58k）全用 120；mdn（frozen_test，base ~105k）修剪至 30 以容纳——P1 不重跑 frozen_test，不影响验收。
- 冻结 boilerplate 关键词表（代码常量，小写匹配）：nav, sidebar, footer, header, menu, advertisement, subscribe, newsletter, feedback, recommend, copyright, ©, share, cookie, 反馈, 推荐, 广告, 订阅, 导航, 版权, 分享。
- 新增一条 constraint 说明菜单用法；现有 dimensions 描述字符串与其余 constraints 保持不变。

### 3.2 引文空白折叠匹配（validation 容差，幻觉防护不变）

- 匹配规则：`_ws_fold(s) = ' '.join(s.split())`（折叠所有空白 run，含 U+00A0/制表/换行/双空格）；校验 `_ws_fold(quote) in _ws_fold(registry[ref])`。
- **保留全部其他校验**：ref 必须在 registry；quote 原始非空（strip）且折叠后非空；原始长度 ≤400；scored/partial 须 ≥1 个 s:/g: 引用；score/severity/status/schema 规则一字不改。
- 不放松幻觉防护：捏造词序、跨节点拼接、paraphrase 仍拒绝（折叠只压空白，不改变非空白字符序列）。
- 同步更新 prompt 中引文规则措辞（保留 U+00A0 提及，改为"空白 run 折叠匹配，非空白字符逐字"）。
- **协议文档 docs/RUBRICS_V2_PROTOCOL.md 不改**：它约束评分语义（锚点/严重度/决策规则），均未变；引文转录容差属 judge 实现层契约，记录于本文件 + freeze v3 amendment reason + judge changelog。freeze v3 的 changed_files 见修订 R1：代码仅 [src/webextractor/rubrics_judge.py]；另 23 个 silver 标签因嵌入 prompt_chars 构建诊断而刷新（证明仅该字段变化，评分内容逐字段相同）。

### 3.3 探针扰动参数（probe-only，默认 None 时生产 prompt 逐字节不变）

- `source_order_seed: int|None`：source_nodes 列表按 random.Random(seed).shuffle 重排（ref↔文本映射不变，仅呈现顺序变）；用于证据位置扰动探针。
- `dimension_phrasing: str|None`：取值 'neutral_v1' 时替换五维描述为预注册中性改写（保留全部引用规则句）；用于提示词扰动探针。neutral_v1  exact 字符串见代码常量 PHRASING_VARIANTS，预注册如下语义：仅重述描述性措辞，不改变评分锚点、引用规则、输出 schema。
- 扰动改变 prompt 内容 → prompt_sha256 变 → 缓存键自然分离；**signature 不变**（探针不是新协议版本，report.settings 记录扰动参数）。
- 探针运行**不得**用于验收；验收只用无扰动 v1.1.0 生产 prompt。

### 3.4 版本与缓存

- JUDGE_VERSION 1.0.0 → **1.1.0**。缓存键绑定 judge_version + prompt_sha256 → v1.0 缓存全部失效，v1.1 全部为新调用（预算已计）。
- rubrics_version 2.0.0 不变；batch_config（model=qwen3.8-27b, max_source_chars=20000, max_output_tokens=2200, timeout=90）不变。
- 运行器新增 --split 过滤（dev-only 运行用冻结全量 manifest 过滤 development，manifest 文件字节不变 → manifest_sha256 与冻结一致，check_freeze 兼容）；新增 probe 透传（run_case/run_batch 可选 probe 字典）。config_signature 键集不变。

## 4. 验收阈值与回退规则（预注册，批准後不得改）

**主验收（dev 12 例，对照 human_gold.final.json，无扰动 v1.1.0）**：
1. 拒绝率 < 10%（即 ≤1/12 拒绝）。
2. severe_miss ≤ 1。
3. 护栏：决策一致率 ≥ 9/10 接受例（P0 最终 dev 为 10/10；允许至多 1 例回落）。false_alarm、逐维 exact/±1、严重度符号、κ 全部描述性报告。

**判定**：三条全过 → v1.1.0 接受为 P1 基线。任一不过 → v1.1.0 **不接受**，触发预注册回退：
- **回退 F1（仅当拒绝率 ≥10% 时触发）**：judge v1.2.0 = v1.1.0 + **有界单次纠正重试**。规则预注册：首次校验失败后，以"原 prompt + 本次校验错误串 + 证据规则提醒"重试**至多 1 次**；重试 prompt 不含任何人类/silver 标签、不含其他案例信息；引文与 s:/g: 校验**不放松**；重试仍失败则 fail-closed 拒绝。每案例最多 2 次调用，运行器按实际调用数计预算。实现仅在触发时进行（避免未用机器）。
- **回退 F2（仅当 severe_miss >1 或护栏破时触发）**：回滚 judge 至 v1.0.0（freeze v2 历史保留），P1 记为未达标，偏差探针结果仍描述性交付；不针对 frozen_test 或人类标签逐例调 prompt。
- 任何回退都须新增 freeze amendment 与本文件修订记录，旧版保留。

**cross-judge / 探针**：首次测量，描述性报告，无验收阈值（预注册声明，避免事后设阈值）。

## 5. 运行计划与预算（待用户批准；批准前零调用）

第二模型：qwen-max（若 API 不可用则 qwen-plus；由冒烟确认，二者均经同一 QwenJudgeProvider，QWEN_API_KEY 已在环境）。cross-judge 为**同家族不同模型**，自偏好偏差覆盖有限，如实声明；跨家族（ccswitch gpt-5.6-sol）留 P2。

| 工作包 | 运行 | 调用数 | 估算 tokens（~15k/次，菜单使输入 +~3k） |
| --- | --- | --- | --- |
| 冒烟 | 1 with_gold dev + 1 source_only dev（iana） | 2 | ~30k |
| W1 dev 重评 | --split development，v1.1.0 生产 prompt | 12 | ~180k |
| W2 cross-judge | 第二模型，--split development，同协议 | 13（含 1 冒烟） | ~195k（第二模型计价单列） |
| W3 探针 | 位置扰动 6 + 中性改写 6（子集见下） | 12 | ~180k |
| W4 稳定性 | 2 dev 例 × 1 次 ignore_cache 复跑 | 2 | ~30k |
| **基础合计** | | **41** | **~615k** |
| 回退 F1  contingency | 仅当 W1 拒绝率 ≥10%：≤12 次重试 | ≤12 | ≤~180k |
| **上限** | | **≤53** | **≤~800k** |

- 探针固定子集（6 dev 例，覆盖 clean/noise/duplicate/source_only）：cal-appetite-clean, cal-appetite-noise, cal-appetite-duplicate, cal-blurb-clean, cal-blurb-noise, cal-iana-noise。位置扰动 seed=20261118；改写 variant=neutral_v1。
- 稳定性固定例：cal-appetite-clean, cal-blurb-noise（temperature=0，期望逐字一致；描述性）。
- 每次运行 max_calls 硬上限 = 该包调用数；输出文件拒绝重名（fail-closed exit 3）；缓存按签名+prompt 哈希绑定，断点续跑零重复计费。
- 实际 usage 逐次计量入报告；估算仅供参考，**硬约束是调用数上限**。第二模型 tokens 单价未知，报告单列 usage，不合并计价。
- 密钥只在环境变量；绝不写入项目/报告/记忆。

## 6. 明确推迟到 P2（不在 P1 范围）

- 冗长偏好探针、偏宽类型探针（需新建带人类标签的变异案例）→ P2 扩规模时做。
- 跨家族 cross-judge（ccswitch OpenAI-compatible 接入 judge 接口）→ P2。
- 第二标注者 IAA、bootstrap CI、新 frozen_test v2 预注册 → P2。
- judge 蒸馏降本、reward 化 → P3（门槛前置）。

## 7. 可复现交付物（P1 完成时）

- freeze v3 amendment（代码 changed_files=[rubrics_judge.py]；23 silver 标签仅刷新 prompt_chars 诊断并证明评分内容不变；候选/gold/manifest/源页/协议文档/rubrics_v2/构建器哈希不变；旧版保留）。见 R1。
- 命令链：amend_freeze_v3 → run_rubrics_judge --split development（v1.1.0）→ cross-judge --model 第二模型 → run_p1_probes（位置/改写/稳定性）→ score_p1_results（验收+描述性指标）。
- 哈希：freeze v3 files、各 batch/probe 报告 manifest_sha256 与 prompt 签名、人类标签输入 sha256。
- 测试日志：定向新增测试 + 全量回归（306+新增）OK；check_freeze NONE。
- 离线归因证据：v1.0 缓存响应在 v1.1 校验器下的重放结果（证明 H2 修复模式 2）。
- docs/P1_DELIVERY_REPORT.md：验收判定 + 指标 + 偏差探针 + 如实局限 + 预算实际台账。

## 8. 批准记录

- 用户批准预算：**已批准**。用户 2026-11-18 聊天回复「批准全部 41 次」，批准基础 41 次调用（上限 ≤53，含回退 F1 contingency ≤12）；第二模型 qwen-max（不可用则 qwen-plus，冒烟确认）。批准前零调用；批准后按 §5 运行计划执行。
- 预注册固定时间：2026-11-18；固定后变更须走修订记录。

## 9. 预注册修订记录

### R1（2026-11-18，零调用阶段发现，调用前固定）

实现 v1.1.0 时发现两处工程耦合，修订设计如下（评分语义、验收阈值、运行计划、预算均不变）：

1. **菜单预算自适应**：mdn 案例 base prompt ~105k 字符，加 6k 菜单后超 110k 预算守卫，导致校准构建器失败。解决：菜单 quote 前缀按 {120,60,30} 取最大可容纳者，皆不容则空菜单（确定性）。dev 案例不受影响（全 120）；mdn 属 frozen_test，P1 不重跑。
2. **silver 标签 prompt_chars 诊断耦合**：每个 silver 标签嵌入构建期 prompt_chars（prompt JSON 长度），freeze 对重建标签哈希。菜单改变 prompt 大小 → 23 标签 prompt_chars 漂移。解决：freeze 快照构建器输出，且 --verify 要求 disk==builder==freeze。amendment 逐标签证明重建标签与磁盘冻结版本**仅 prompt_chars 不同**（expected/mutation/decision/candidate_sha256/gold_sha256/source_sha256/noise_terms/batch_config/source_truncated/program_reference/notes/derivation 全部逐字段相同），随后**仅刷新磁盘 silver 标签的 prompt_chars 诊断字段**并同步 v3 cases 的 label_sha256/prompt_chars，使 disk==builder==freeze v3。**评分内容零变化**（证明在刷新前完成）；候选/gold/manifest/源页/协议文档/rubrics_v2/构建器/batch_config 哈希不变。ingest 读 silver 仅用 mutation/expected（不变）；check_freeze 比对 candidate/source/gold/manifest（均不变）；人类 gold 与 P0 审计哈希不受影响（P0 审计哈希的是人类标签，非 silver）。工具幂等，刷新后重跑证明为空、不报错。
3. freeze v3 changed_files = [rubrics_judge.py] + 23 silver 标签（诊断刷新）；代码变更仅 rubrics_judge.py。协议文档 docs/RUBRICS_V2_PROTOCOL.md、rubrics_v2.py、build_calibration_set.py、候选、gold、manifest、源页、batch_config 哈希不变。

R1 不改变 H1–H5、验收阈值（dev 拒绝 <10%、severe_miss ≤1、决策分歧 ≤1 例）、回退规则 F1/F2、运行计划与预算上限。修订在任何模型调用之前固定。
