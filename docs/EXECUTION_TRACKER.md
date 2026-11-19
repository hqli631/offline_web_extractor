# 学习工程执行闸门

最后更新：2026-11-13（Asia/Shanghai）

每一阶段必须同时有代码或数据、可复现命令、评测结果和失败复盘；当前阶段未通过前，不进入下一阶段。

## Gate 1：规则项目 v1 冻结

- 状态：通过
- 证据：当时 49 项测试通过；开发集 3 个真实样本和 1 个合成样本全部结构匹配；W3C 新站点保留首次报告与修复后报告。
- 冻结内容：当前源码、W3C HTML/expected 哈希、初始验证清单、规则复用配置。
- 结论：规则修复后的 W3C 结果为 61/61 结构块匹配；这只证明该快照在当前标注口径下通过，不代表泛化准确率。

## Gate 2：独立样本与封存验证

- 状态：通过。这里指实验与证据完整，不指所有页面结构满分。
- 规模：6个新增可用参考页覆盖文档、新闻、博客、说明文章和课程总览；RFC/WHATWG两个完整长快照暂缓。5个开发页保留首次预测。
- 验证：web.dev在源码与答案冻结后首次评分，validation_scored、tuning_used=false；47/45块，文本P=0.9362、R=0.9778，结构不全匹配。只有单个课程总览页，不代表新闻博客泛化。
- 证据：samples/sample_registry.json、来源/答案哈希、独立转录脚本与复核、ANNOTATION_PROTOCOL_v1.2.md、baselines/rules-validation-release-v1/manifest.json、outputs/webdev-learn-html.candidate.validation_first.json。
- 所有历史expected/first报告保留；助手DOM辅助参考不等同用户逐项复核或多人金标。

## Gate 3：错误分析与成熟静态基线

- 状态：通过。64项测试通过；原开发集结构保持匹配。通用标题/容器与结构修改已在5个扩展开发页验证。
- Trafilatura 2.0.0与生产提取器在同一个隔离Python/lxml环境对比；固定参数、全块文本指标、预热串行计时、逐页原始结果。
- 证据：docs/17_semantics_and_baseline.md、BASELINE_PROTOCOL.md、outputs/expanded_development.after_review.json、outputs/baseline.development.v2.json/md。成熟基线仅跑开发组，不宣称封存验证的基线结果。
- 模板边界、复杂列表协议和小样本限制已记录。

## Gate 4：固定规则复用与模板漂移

- 状态：通过。当前版本真实Sphinx复用2页各唯一命中，迁移页32块、6代码/5子标题/1脚注，无完整金标不报准确率。受控合成5页按预期暴露0匹配、多匹配、唯一命中但2/3正文；Python子进程退出码分别0/2，JSON逐项断言通过。
- 证据：outputs/rule_reuse_gate4_final、outputs/drift_lab_gate4_final、docs/18_rule_drift.md、docs/RULE_PROJECT_REPORT.md；配置/HTML/expected与源码指纹保存，参考哈希不符和运行中源码变化拒绝评分。

- 目标：参考页冻结 XPath，在新页直接执行；覆盖 0 匹配、多个匹配和模板变化。
- 通过条件：规则版本记录、失败原因、无逐页临时修复；完成后才进入 Agent。

## Gate 5—11：长期能力链路

Gate5状态：通过（开发原型验收，不代表泛化准确率）。13个真实开发快照和5个合成漂移页在固定阈值0.7、五种预声明特征下完成对照；真实误聚均为0，但真实漏聚随模式为6—11对；合成误聚为3—7对，semantic-presence另有2对漏聚。full-counts出现IANA链式聚簇警告。证据：docs/19_dom_similarity.md、docs/20_cluster_ablations.md、outputs/clustering_v2/、samples/dom_similarity.expanded_development.json。当前输出只产生共享规则候选组，结构相似不证明XPath可复用。

Gate6状态：回放流程通过，真实模型能力未评估。受限规则执行器严格校验version=1、唯一容器、容器内排除节点，并在可终止子进程执行；authored-replay先返回零匹配，再根据两页参考反馈修复为共同role容器。DashScope/Qwen 提供者已完成端点白名单、超时、一次重试、代理和用量映射的 mock 测试，但没有真实密钥或网络调用。轨迹包含参考哈希、证据、提示、响应、执行反馈和预算，quality_evaluated=false，未读gold或held-out页面。证据：docs/AGENT_INTERFACE.md、docs/QWEN_SETUP.md、src/webextractor/agent_rules.py、src/webextractor/rule_agent.py、src/webextractor/qwen_provider.py、outputs/agent_lab.replay.v1.json；117项测试通过。

Gate7状态：受控跨样本评测通过，真实网页泛化未评估。1页reference只进入Agent，4页test及gold在生成结束后由评测层读取；固定规则、一次调用无修复和两次调用有修复均可复现。class-drift保持完整，role-drift返回rule_no_match，duplicate-main返回rule_ambiguous，content-moved保持唯一命中但召回下降。证据：src/webextractor/agent_evaluation.py、samples/agent_lab/gate7_manifest.json、outputs/agent_lab.gate7.repair.json、docs/21_agent_cross_sample_evaluation.md；94项测试通过。样本是合成漂移，不能报告真实模型效果或工业泛化。

Gate8状态：通过确定性Rubrics原型，尚无真实模型Critic。完整性、纯净度、结构三维均按0—4分级并保留连续比例；显式noise_terms才扣纯净度，网页中的“忽略指令”按数据处理；MAD和重复评分接口已测试。证据：src/webextractor/rubrics.py、docs/RUBRICS_PROTOCOL.md、samples/agent_lab/rubrics_cases.json；3项定向测试通过。

Gate9状态：通过SFT/LoRA数据准备，不代表已训练。轨迹生成器输出脱敏JSONL，按模板和split分组、去重并拒绝gold/expected/test/validation/held-out及凭据字段；2条回放样本、0重复，输出SHA256为d8deff4adf4c026330697944fc0b01967a863b35c07a6b52f4cd526f6d307f84。证据：tools/build_sft_dataset.py、docs/SFT_DATA_PROTOCOL.md、samples/agent_lab/sft_manifest.json；3项定向测试通过。LoRA/QLoRA训练尚未执行。

Gate10状态：通过玩具奖励实验，不代表完成工业PPO/GRPO。固定种子有限XPath bandit同时运行稀疏奖励、故意错误的长度/召回代理奖励和precision/recall/结构修正奖励；REINFORCE与GRPO-like组内相对更新均可复现。代理奖励选择含导航、推荐、评论的long-noise，修正奖励选择exact，形成明确奖励投机案例。证据：src/webextractor/toy_rl.py、docs/RL_TOY_PROTOCOL.md、outputs/rl_toy.v1.json；4项定向测试通过。没有深度模型训练或真实网页奖励实验。

Gate8状态：Rubrics确定性评估原型完成。完整性、纯净度、结构正确性分别给出0—4等级和连续比例；网页中出现的“忽略指令”只作为数据，只有评测者明确提供的noise_terms才扣纯净度分；MAD与重复评分工具已测试。证据：src/webextractor/rubrics.py、docs/RUBRICS_PROTOCOL.md、samples/agent_lab/rubrics_cases.json；定向3项测试通过。尚无多人标注或真实模型Critic校准。

Gate9状态：SFT/LoRA数据准备通过，训练未执行。未评分Agent回放轨迹生成2条JSONL样本，去重0条，输出SHA256=d8deff4adf4c026330697944fc0b01967a863b35c07a6b52f4cd526f6d307f84；生成器拒绝gold、test、validation、held-out和凭据字段，并按模板/split冻结。证据：tools/build_sft_dataset.py、docs/SFT_DATA_PROTOCOL.md、samples/agent_lab/sft_manifest.json、outputs/sft.agent.replay.jsonl；定向3项测试通过。没有LoRA/QLoRA训练收益可报告。

Gate10状态：玩具RL实验通过。有限一步规则搜索环境比较sparse、proxy、corrected奖励，并运行REINFORCE和GRPO-like组相对更新；固定种子7可复现。proxy奖励选择包含导航/推荐/评论的long-noise，corrected奖励选择exact，奖励投机反例和轨迹已保存。证据：src/webextractor/toy_rl.py、tools/run_toy_rl.py、docs/RL_TOY_PROTOCOL.md、outputs/rl_toy.v2.json；定向4项测试通过。不是完整PPO/GRPO训练。

Gate11状态：离线学习工程交付整理完成。实际DOM-backed奖励实验与Qwen提供者mock审计已加入；阶段报告、复现命令、5分钟讲述和限制见docs/FINAL_DELIVERY_REPORT.md；全套回归117项通过。用户选择先完成离线工程，真实Qwen调用暂缓；LoRA/QLoRA训练和工业规模Agentic RL仍未执行。

1. 结构特征与聚簇：标签路径、节点统计、结构相似度、误聚/漏聚。
2. 单 Agent 规则生成：受限 XPath/JSON 配置，执行反馈和有上限的修复。
3. 跨样本泛化：手写规则、无修复 Agent、有修复 Agent 的效果和调用成本对比。
4. Rubrics/Critic：完整性、纯净度、结构正确性，人工校准和评分一致性。
5. 数据与 SFT/LoRA：轨迹数据、数据划分、离线评测；资源不足时不强行训练。
6. PPO/GRPO 玩具实验：稀疏奖励、奖励投机和有限步搜索环境。
7. 可选深化：多 Agent、Agentic RL、蒸馏或 CPU 批量执行；以单 Agent 失败证据决定是否进入。

具体阶段任务、产出和进入条件见 LEARNING_PLAN.md。学习日与周数是估计，以闸门为准。不能用已经参与修复的页面替代未见验证，也不以所有样本满分作为过关条件；已解释和量化的失败允许记录为能力边界。

## 下一次执行顺序

1. 若继续深化，先获取真实多模板标注和合法模型/API资源，再进行Qwen调用或LoRA训练；没有独立测试不得报告收益。
2. 可选扩展Agentic RL、多Agent或CPU批量执行，但必须由失败证据驱动并保留消融。

## 每周固定复盘

记录任务规模、基线、设计、失败案例、验证方式、成本和限制。任何“提升”必须绑定样本数、来源、切分和报告文件。


## 2026-11-15 GPT MVP 补充验收

当前124项全量测试通过。CC Switch真实smoke已成功（outputs/agent.ccswitch.smoke.v2.json）；保存GPT规则的三页公开开发快照迁移结果见outputs/mvp_demo.v1/report.json，两个页面精确匹配、IANA零匹配，未发起新API调用。评测读取时序、切分重叠、结构字段比较已修复。随后用户指定env.local，真实reference生成评测已完成，详见最终记录；不再扩展训练或重复消融。

最终记录：outputs/agent.ccswitch.mvp.v2.json保存真实公开reference→模型生成→本地执行→隔离test/gold评测。1次请求，5967 tokens；同模板16块完全匹配，跨模板两页零匹配。展示页outputs/mvp_real.v2/index.html。MVP交付收束，云端训练未执行。
