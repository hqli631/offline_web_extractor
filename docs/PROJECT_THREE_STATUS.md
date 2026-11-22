# 项目三：网页正文提取与 Rubrics 自动评估

更新日期：2026-11-18。按用户指定，当前工程记为“项目三”，目录保持 offline_web_extractor。

当前为正文提取与规则生成 MVP：结构化提取、受限 XPath Agent、GPT/Qwen API、隔离评测、确定性 Rubrics 均有实现。最新全量129项测试通过。Qwen3.8-27b真实调用已验证：一个同模板开发测试页16块文本与结构匹配，章节编号被排除导致标题不全匹配；两个跨模板测试零匹配。只代表小样本开发结果。

Rubrics目标为：输入原始网页证据、候选提取结果及评分标准，输出可审计的分项分数、证据、错误位置和人工复核建议；结合程序指标完成批量评估。当前rubrics.py仍是依赖gold的确定性诊断，尚无真实LLM Critic、人类一致性校准或质量驱动Agent修复。

## 后续顺序（待实施，不表示已完成）

1. 冻结评分协议：完整性、纯净度、结构、标题/来源忠实性，定义0—4分锚点、关键错误与无法判断状态；修正现有协议与代码差异（结构签名实际含文本和source_id），分开文本对齐与结构属性评分。
2. 实现Qwen Judge：程序检测加模型语义判断，输出严格JSON和可校验block/DOM证据；完整内容未覆盖时标记部分评估，不能将缺失证据当作正确。保留有gold对照和无gold辅助判断两种模式。
3. 建校准集与冻结测试：多个模板和真实/受控错误，包含漏段、混噪、重复、乱序、标题编号、代码缩进及网页指令干扰。先做小规模20—30例的人工审阅试点，按源页面/模板拆分，避免同页变体跨split泄漏；该规模是建议，非已完成。
4. 验证与批处理：报告逐维人机误差、严重错误漏检、正常结果误报、重复评分稳定性、失败率、耗时和token成本；阈值先在校准组确定，冻结后在test验收。支持缓存、版本和哈希、断点续跑及待复核清单。
5. 可选质量修复闭环：只使用reference或专门修复开发集上的Critic反馈，限定修复次数，并与无修复对照；test/gold不得回传。未验证Judge可靠性前，不将其分数作为训练奖励。

Rubrics小项目的交付条件为评分协议、真实Qwen Judge、批量结果、人工校准/冻结test报告和可查看的错误证据。多Agent、SFT/LoRA及工业RL属于此后的可选扩展，不是Rubrics交付前置条件。

## 当前改进节点（2026-11-17）

目标模式已开启。节点1：Rubrics v2协议冻结并复验（哈希MATCH）。节点2：Qwen Judge已实现并通过工程验收——严格schema与证据校验、gold/source_only分离、缓存/断点/预算工具、真实冒烟4/4接受（累计11次调用/234,105 tokens），全量166项测试通过；详见RUBRICS_CHECKPOINTS.md。Judge未经校准，分数不作为训练奖励。节点3校准集已构建并冻结验证MATCH：23例（dev12/frozen_test11）、6基础页按split隔离、7类受控错误全覆盖、silver标签（assistant_silver，非人类gold）；rfc因候选超提示词预算排除，T6改为w3c-link-text（source_only）。全量177项测试通过。节点4批量/稳定性评测已完成：最终batch v6 23例16接受/7拒绝（拒绝全部为fail-closed模型不合规），overall决策一致0.8125（dev 0.900 / frozen_test 0.6667），severe_miss 3例（judge严重度偏宽）、误报0，稳定性5/6完全一致，注入干扰mdn例未服从；全量187项测试通过，冻结v2 verify MATCH。可复现报告见docs/RUBRICS_JUDGE_REPORT.md（含完整预算台账：累计65次调用、已计量776,210 tokens、12次usage未知）。按用户指令节点5修复闭环未进入，本轮goal已停止。人工独立审阅仍未完成，不能以助手标签替代；Judge分数仍不作为训练奖励。

## P0 人工校准启动（2026-11-17）

节点4交付后按推进计划（docs/HUMAN_CALIBRATION_PLAN.md）启动P0：盲评工具包outputs/human_review/blind.v2（23份中性编号案卷+标签模板+密封映射）与两阶段接收器tools/ingest_human_labels.py已建成，定向21项+全量208项测试通过，零模型调用。blind.v1因案例名泄漏变异类型废弃。当前等待用户独立盲评与裁决；human gold产生前，judge可信度结论仍不成立，judge分数仍不作训练奖励。P1元评估、P2扩规模、P3训练集成按门槛顺序排队，均需用户批准后推进。


## P0 第一轮回收与机械修复（2026-11-18）

用户已独立完成 23/23 盲评。ingest 校验 fail-closed 拒绝：58 个维度把 status 值 partial 误填进 severity 列，故本轮未产生 human gold，judge–human 一致率仍不存在。修复过程同时暴露并修好一处盲评泄漏：原校验报错串使用真实 case_id，首次运行使 15 个案例名在控制台可见；已改为 blind 阶段一律以盲码渲染（code_map），复验 0 泄漏。该偏差记为 D1，将在最终报告中如实披露——标签在泄漏前已填写完毕，无回填通道，但标注者已知晓 B07–B21 的案例名，裁决须以其本人 note 证据为准。新增 tools/repair_human_labels.py 与 configs/severity_keyword_map.v1.json，只从标注者本人 note 文本按冻结严重度锚点推导 severity，不读 judge/silver/密封映射，不改 score/decision/note，已合法值一律不动，原文件不覆盖并留 sha256 审计。dry-run：修复 58 条、保留 57 条、提示 17 条、一致性待确认 2 条（B18/B21）+ critical 锚点待确认 2 条（B08/B09）。新增 42 项定向测试，全量 250 项通过。等待标注者确认关键词映射与 4 项待确认点后 --apply 并重跑 ingest blind；仍为零模型调用，P1 需用户批准调用预算，节点5 未进入。


## P0 第一轮结果（2026-11-18）

标注者确认的 4 项修改与 2 项缺口保留已落盘为 configs/human_label_overrides.v1.json，由 tools/repair_human_labels.py v2.1.0 以两段式（机械修复 + 标注者确认覆盖）应用到 human_labels.blind.r2.json，原盲评文件未改动，全程只读标签与两份配置、不读 judge/silver/密封映射，输出无真实 case 名。全量 285 项测试通过。首次真实 judge–human 一致性：全量 16 接受例决策一致率 0.75、Cohen κ=0.5077、逐维 exact 0.75 / ±1 0.9688、严重度符号 0.8125；development κ=0.8246（10 接受例）、frozen_test κ=-0.2857（仅 6 接受例，统计上不可解释，仅描述性且不得据此调参）。severe_miss 2 例（judge 对代码缩进与"干净"案卷偏宽）、false_alarm 2 例（偏严）；fail-closed 拒绝率 30.4%（frozen_test 45%）是可比样本不足的主因。此前对外出现的 0.8125 属 judge 对 silver 的一致率，不能当准确率使用。已生成 17 份裁决案卷与预填 final 模板，等待标注者裁决；P0 全程零模型调用，judge 分数仍不作为训练奖励，节点5 未进入。


## P0 最终裁决与交付（2026-11-18）

标注者以聊天回复完成全部 23 例裁决（18 keep / 5 revise：B04/B09/B12/B13/B18；B19/B23 injection_complied=false；B18 decision 经第二条回复澄清为 uncertain——降分后无 major/critical，按冻结决策规则⇒uncertain）。逐字规格 configs/adjudication_decisions.v1.json；tools/apply_adjudication.py v1.0.0 落盘 → outputs/human_review/final.prep.v1/（sha256 审计 + 字段级差异，post-apply 一致性扫描干净、仅 B19 豁免）；ingest --stage final → outputs/human_review/final.v1/。最终（裁决后）一致性：决策 0.9375 / κ 0.872（dev 1.0/1.0；frozen_test 0.8333/0.0，仅 6 接受例、只作描述），逐维 exact 0.8281 / ±1 0.9688，严重度符号 0.8281，severe_miss 0，false_alarm 1（cal-mdn-instruction_interference）；独立锚点仍是第一轮盲评 0.75/κ0.5077，两轮必须并列呈现。指标变化全部来自人类侧裁决修订，judge 零模型调用、零变化；severe_miss 清零是标注者复核证据后下调 B13/B18，judge 偏宽倾向（代码缩进/格式类）与 30.4% fail-closed 拒绝率仍是 P1 目标。16 条持续分歧留痕（7 judge_error + 9 维度级，structure 最集中），不自动调参。验证：全量回归 306 项 OK（outputs/rubrics_judge.p0.final.tests.v2.log，19.873s）、check_freeze NONE。偏差 D0/D1/D2 与 B19 协议覆盖缺口如实披露，不做事后清洗。可复现交付报告：docs/P0_DELIVERY_REPORT.md。**P0 已交付并停止**；P1 元评估 / P2 扩规模 / P3 reward 化 / 节点5 修复闭环均需用户明确批准（P1 起须先批调用预算）；judge 分数仍不作训练奖励。


## P1 工程就绪（2026-11-18，零调用，待预算批准）

P0 交付后启动 P1 judge 元评估。预注册方案 docs/P1_META_EVAL_PLAN.md（含 R1 修订）已在调用前固定。工程实现完成并验证：judge v1.1.0（证据菜单 + 引文空白折叠匹配 + 探针扰动参数，仅改 rubrics_judge.py，幻觉防护不放松）；运行器 --split dev-only 过滤 + probe 透传；新工具 amend_freeze_v3 / run_p1_probes / score_p1_results。freeze v3 修正完成（代码仅 rubrics_judge.py 变更，23 silver 标签仅刷新 prompt_chars 诊断且证明评分内容逐字段不变，候选/gold/manifest/协议文档/rubrics_v2/构建器/batch_config 不变），build_calibration_set --verify v3 = MATCH，check_freeze 历史 batch v6 对 v3 = NONE。离线归因（零调用）证明空白折叠修复 blurb 模式2 拒绝；6 例模式1 需菜单 prompt 变更待 dev 重评验证。定向 45 项 + 全量回归 351 项测试 OK（outputs/rubrics_judge.p1.engineering.tests.v2.log）；验收评分管线 score_p1_results.main() 已端到端验证。**当前等待用户批准模型调用预算**（基础 41 次、上限 ≤53 次，~615k–800k tokens）；批准后执行 dev 重评 / 第二模型 cross-judge / 偏差探针 / 稳定性，验收 dev 拒绝率 <10% 且 severe_miss ≤1。frozen_test 全程不重跑、不调参、永久封存至 P2；judge 分数仍不作训练奖励。


## P1 实验结果（2026-11-18，有条件达标，F2 待用户决策）

用户批准 41 次预算后执行 P1 实验（密钥 401 阻塞经用户更新 env.local 解除）。实际成功调用 40 次（≤41），tokens 541,303；第二模型 qwen-plus（qwen-max 403 不可用）。W1 dev 验收：拒绝率 8.3%<10% ✓、severe_miss 1≤1 ✓（目标硬指标达标），但接受例决策分歧 3>护栏 1 ✗，dev 决策一致率从 P0 最终 1.0/κ1.0 回归到 0.7273/κ0.5286（false_alarm 2）→ 预注册 verdict REJECT（护栏破）。拒绝率修复有效（16.7%→8.3%）但菜单/折叠扰动使部分接受例评分漂移。W2 cross-judge qwen-plus 拒绝 50%、双接受 6 例一致 0.8333/κ0.6667（模型特异性偏差显著）；W3 位置扰动翻转 1/6、中性改写 2 拒绝；W4 temp0 复跑稳定。freeze NONE。交付 docs/P1_DELIVERY_REPORT.md。**F2 决策点待用户**：(a) 接受 v1.1 带告警 / (b) 回滚 v1.0（拒绝率反不达）/ (c) P1.5 迭代恢复一致率（需新预算）；助手建议 c>a>b。frozen_test 全程未重跑未调参、永久封存至 P2；judge 分数仍不作训练奖励。


## GitHub 同步 + P1.5 启动（2026-11-19）

- **GitHub 同步完成**：项目三首次推送至 https://github.com/hqli631/offline_web_extractor （main 分支，commit d2ad75c0be1da40b312bccdb64f5f100180eca19，687 文件）。git init→密钥扫描（687 文件零泄露，env.local 经 .gitignore 排除）→commit→push。schannel TLS 握手失败改用 **openssl SSL 后端**（已固化 git config http.sslBackend openssl）；GCM 认证通过；远程 refs/heads/main 与本地 HEAD 一致。
- **P1.5 启动（路径 c）**：零调用漂移诊断 outputs/p1_drift_diagnostic.v1.json 揭示一般性**菜单锚定效应**（v1.1 菜单把严重度拉向中间档：轻缺陷抬高→false_alarm，重缺陷压低→severe_miss）。预注册 docs/P1_5_META_EVAL_PLAN.md：judge v1.2.0 一般性解耦评分与证据菜单（菜单降级为引文附录+严重度锚点强化），目标恢复 dev 护栏（分歧≤1）同时保持拒绝<10%、severe_miss≤1；严禁逐例拟合人类标签；frozen_test 仍封存。预算基础 16 次/上限≤40，待批准。下一步：零调用工程实现+测试→freeze v4→报预算→批准→dev 重评→验收→报告。


## P1.5 工程就绪（2026-11-19，零调用，待预算批准）

- judge **v1.2.0**（仅改 rubrics_judge.py，新 sha256 edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891）：证据菜单移至 prompt 末位（引文附录）+ 新增 SCORING INDEPENDENCE 强约束（评分/严重度仅依实际缺陷幅度按锚点判定，菜单不得抬高/压低任何分数或严重度）+ 严重度锚点强化。一般性原则，无案例特异分支（测试断言 prompt 不含 cal-/盲码）。菜单内容/空白折叠/s:/g: 规则/探针参数不变。
- 新工具 tools/amend_freeze_v4.py（幂等，证明 silver 标签仅 prompt_chars 漂移）；freeze **v4** 修正完成：代码仅 rubrics_judge.py，23 标签诊断刷新（评分内容证明不变），候选/gold/manifest/源页/协议文档/rubrics_v2/构建器/batch_config 不变。build_calibration_set --verify v4 = **MATCH**；check_freeze 历史 batch v6 对 v4 = **NONE**；协议文档哈希 ab0887b5… 不变。
- 测试：P1.5 定向 10 项（tests/test_p1_5_judge_v12.py）+ P1/judge 定向共 82 项 OK；全量回归 **361 项 OK**（outputs/rubrics_judge.p1_5.engineering.tests.v1.log，21.140s）。
- 预注册 docs/P1_5_META_EVAL_PLAN.md（H1 解耦消除菜单锚定；验收 dev 分歧≤1 且拒绝<10% 且 severe_miss≤1；回退 F1/F2 两阶段）。
- 状态：**工程就绪，零调用，等待用户批准 P1.5 预算**（基础 16 次：冒烟 2+dev 重评 12+稳定性 2，~240k tokens；回退两阶段上限≤40 次/~600k）。批准后 dev 重评→验收（恢复护栏）→交付 P1.5 报告→同步 GitHub→停止。frozen_test 仍封存；judge 分数仍不作训练奖励。


## P1.5 验收 ACCEPT（2026-11-19，批准后执行）

- 用户批准 P1.5 预算后执行：冒烟 2 + W1 dev 重评 10（前 2 缓存）+ W2 稳定性 2 = **14 次新调用 ≤16**，tokens **201,975**（低于估算）。回退 F1/F2 未触发。
- **验收 ACCEPT，护栏恢复**：dev 拒绝率 **0%**（0/12）、severe_miss **0**、接受例决策分歧 **1**（≤1）——三项预注册阈值全达标。freeze_check NONE。
- dev 决策一致率 **0.9167 / κ0.8554**（v1.1 0.7273/0.5286 大幅恢复）；逐维 exact 0.8333、±1 1.0、严重度符号 0.875。一般性解耦假设 **H1 得证**（菜单锚定消除）。
- 修复案例：appetite-missing_paragraph、appetite-duplicate（v1.1 fail→uncertain 匹配）、blurb-reorder（v1.1 severe_miss→fail 匹配）、blurb-missing_paragraph（v1.1 被拒→接受且匹配）。残留 1 处 false_alarm：appetite-reorder（judge fail vs 人类 uncertain，护栏内，留 P2 检验）。
- 稳定性 temp=0 复跑 2 例完全一致（翻转 0、exact 1.0）。
- 交付 **docs/P1_5_DELIVERY_REPORT.md**（命令+哈希+台账+三版对比+如实局限）。frozen_test 未重跑未调参、永久封存至 P2；judge 分数仍不作训练奖励。
- P1 系列完成：v1.0（拒绝 16.7%）→ v1.1（8.3% 护栏破）→ **v1.2（0% 护栏恢复 ACCEPT）**。后续 P2 扩规模/IAA/新 frozen_test v2 检验泛化（需批准）。


## P2 启动 + WP1 统计强化（2026-11-19，零调用）

- 预注册 docs/P2_META_EVAL_PLAN.md（drafted）：扩样 ~45–55 例（新模板 python_interpreter_zh/nasa-voyager-news/w3c_accessibility_intro_zh，预算检验可行；webdev-learn-html 封存禁用）、分层、新 frozen_test v2 预注册封存（v1 永久封存）、第二标注者 IAA ≥12 例、跨家族 cross-judge（gpt-5.6-sol）、bootstrap CI、泛化验收阈值。需用户配合：第二标注者、新案例人类 gold、源页确认、预算批准。
- **WP1 完成**：tools/bootstrap_stats.py（案例级 bootstrap 95% CI，B=10000 种子 20261119 + 配对 McNemar）；tests/test_bootstrap_stats.py 8 项；全量回归 **369 项 OK**（outputs/rubrics_judge.p2.wp1.tests.v1.log；本次耗时 637s 异常偏慢，疑系统负载，测试全绿）。
- 现有 dev 三版 bootstrap（outputs/p2.bootstrap.dev.v1.json、P2_BOOTSTRAP_DEV.md）：v1.2 决策一致 0.9167 CI[0.75,1.0]、κ0.8554 CI[0.5,1.0]、拒绝 0；**关键洞察：n=12 小样本 CI 极宽，v1.2 vs v1.1 改善统计不显著（McNemar p=0.625，差值 CI[-0.55,0.18] 含 0），v1.1 κ CI 含 0** → 量化了 P2 扩样必要性。v1.0 一致率 CI[1,1] 为边界退化（全匹配），如实注明。
- 下一步：WP2 扩样工程（零调用构建新 silver 案例）→ WP3 frozen_test v2 封存 → WP4 人类 gold/IAA（需用户）→ WP5 跨家族（需预算）→ WP6 泛化验收+报告。


## P2 WP2 扩样 + WP3 封存（2026-11-19，零调用）

- **WP2 扩样工程完成**：tools/build_p2_calibration.py 从已有本地源页构建 **18 新 with_gold silver 案例**（无新网络采集）：python_interpreter_zh（dev 扩展 6）、nasa-voyager-news.candidate + w3c_accessibility_intro_zh（frozen_test v2 各 6）；各 6 变异（clean/missing_paragraph/noise/duplicate/reorder/instruction_interference）。expected.json 参考=清洁提取（assistant_silver，待 WP4 人类核验）；interpreter 新建参考，nasa/w3ca11y 用已有参考。
- 产出 samples/p2_manifest.json + outputs/p2.freeze.v5.json（freeze_version 5，48 文件，**重建零漂移**，manifest canonical 匹配）；原 23 例 manifest/freeze v1–v4 **未动**，frozen_test v1 永久封存。新案例 prompt 最大 75904<110000 全 fit。
- **WP3 frozen_test v2 预注册封存**：docs/P2_FROZEN_TEST_V2_SEAL.md（12 例清单+哈希+纪律：一次性评估、不调参、与 dev 整页隔离）。
- 测试：P2 构建器 7 项 + bootstrap 8 项定向 OK；全量回归 **376 项 OK，23.9s**（上次 637s 确认为瞬态负载，已恢复正常）。
- GitHub 同步至 097c3d5。
- **剩余需用户配合/批准**：WP4 新案例人类 gold 盲评（用户）+ 第二标注者 IAA ≥12 例（用户安排）；WP5 跨家族 cross-judge（gpt-5.6-sol，需预算+ccswitch 确认）；WP6 frozen_test v2 泛化验收（需预算）+ P2 报告。零调用工程（WP1/2/3）已全部就绪。


## P2 WP4 工具链就绪（2026-11-19，零调用）

- **compute_iaa.py**：双标注者决策 Cohen κ + 一致率 + 逐维 exact/严重度符号 + bootstrap 95% CI（B=10000），按 case_id/blind_code 对齐；量化人类 gold 噪声（低 IAA 限制 judge–human 一致率上限）。
- **build_p2_review_kit.py**：用 build_prompt 离线构造盲评案卷（**无需先跑 judge**），复用 render_blind_packet/build_template；中性编号 P01–P18 + 密封映射，案卷零 case_id 泄露、不含 judge/silver/程序分数。
- **P2 盲评包已生成**：outputs/human_review/p2.blind.v1（18 案卷 dev6/test12 + human_labels.blind.json 模板 + sealed_mapping.json + INDEX.md + kit_manifest.json）。**供用户独立盲评标注新案例人类 gold；第二标注者用相同案卷独立填另一份标签做 IAA。**
- 测试：compute_iaa 5 项 + kit 3 项定向 OK；全量回归 **384 项 OK，24.6s**。
- GitHub：本地提交 11dead3（WP4 工具+盲评包），推送遇 github.com TLS 瞬断（3 次），**待网络恢复重试**；此前 WP1–WP3 已同步至 097c3d5。
- **P2 零调用工程（WP1/2/3/4 工具）全部就绪**。剩余依赖用户：WP4 人类 gold 盲评（18 例）+ 第二标注者 IAA ≥12 例；WP5 跨家族 cross-judge + WP6 frozen_test v2 泛化验收需预算批准。


## P2 WP5 跨家族接线就绪（2026-11-19，零调用）

- **src/webextractor/judge_openai_provider.py**：JudgeOpenAIProvider（CC Switch OpenAI 兼容，默认 gpt-5.6-sol），用 judge 系统消息 + _parse_content（**不校验 rule**），接口兼容 run_judge；独立于生产 rule-agent provider 与 Qwen judge，零生产改动。
- **tools/run_p2_cross_judge.py**：复用 run_batch（缓存/签名绑定 model，跨家族条目与 Qwen 分离），--split development 默认，--dry-run 免密钥。
- 测试 4 项（mock opener：judge 系统消息、run_judge 接受 judge JSON 非 rule、需密钥、dry-run）；全量回归 **388 项 OK，23.8s**。
- **P2 全部零调用工程就绪**（WP1 统计/WP2 扩样/WP3 封存/WP4 IAA+盲评包/WP5 跨家族接线）。剩余依赖用户：WP4 人类 gold 盲评 18 例 + 第二标注者 IAA ≥12 例；WP5/WP6 模型调用需预算批准 + ccswitch 可用确认。


## P3 收尾（2026-11-22）

- 校准复审 10 案 verdict 封存（judge_correct×5 / human_correct×4 / both_partially×1）。
- 预注册修订 judge v1.3.0 实施后 **dev 回归护栏 FAIL**（severe_miss 3>1）→ 按预注册后果**回滚 v1.2.0**（freeze v8，字节级恢复 sha edd841ef==v4）。
- v1.2 dev 预览 false_alarm 0.1667>0.15 亦 FAIL（2/3 为已裁决 gold 漏检 C01/C02）→ **gate FAIL 最终判定**；judge 分数禁止奖励化。
- v3 已构建封存（freeze v7，12/12 不截断）；前 4 案属失败修订排除；剩余不消耗（用户选 A）。
- 预算：22 次调用 / 379,457 tokens（≤460k）；479 tests OK；交付 docs/P3_GATE_REPORT.md（复现命令已验证）。
- 下一步：节点 5 修复闭环（docs/NODE5_REPAIR_LOOP_PLAN.md，DRAFT 待单独批准+预算）。
