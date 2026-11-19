# 离线网页正文提取学习工程：阶段交付报告

更新时间：2026-11-15（Asia/Shanghai）

这份报告记录可复现的离线学习工程。真实 Qwen 网络调用、真实 LoRA/QLoRA 训练和工业规模 Agentic RL 没有执行，不把回放或玩具结果写成模型能力结论。

## 阶段结果

| 阶段 | 证据 | 已完成内容与边界 |
| --- | --- | --- |
| Gate 1—4 规则提取 | src/webextractor/extractor.py、content_blocks.py、docs/RULE_PROJECT_REPORT.md、docs/17_semantics_and_baseline.md、docs/18_rule_drift.md | 完成 HTML/XPath、候选容器、噪声、段落、列表、标题、代码、表格、引用、脚注、基线和规则复用。复杂动态网页、OCR 和复杂表格仍有限制。 |
| Gate 5 DOM 聚簇 | src/webextractor/dom_similarity.py、docs/20_cluster_ablations.md、outputs/clustering_v2/ | 13 个真实开发页、5 个合成漂移页、阈值 0.7、五种特征。真实误聚 0、漏聚 6—11 对；合成误聚 3—7 对。只能生成共享规则候选。 |
| Gate 6 受限 Agent | src/webextractor/agent_rules.py、rule_agent.py、qwen_provider.py、docs/AGENT_INTERFACE.md、docs/QWEN_SETUP.md | 严格 JSON/XPath schema、唯一匹配、排除范围、可终止子进程、预算和轨迹。人工 replay 首轮零匹配、第二轮修复成功；DashScope/Qwen 提供者已用 mock 测试，真实 API 未调用；quality_evaluated=false。 |
| Gate 7 跨样本评测 | src/webextractor/agent_evaluation.py、samples/agent_lab/gate7_manifest.json、outputs/agent_lab.gate7.repair.json | reference 与 test/gold 隔离。保留 class drift、role drift、duplicate main、content moved 四类结果；均为合成漂移。 |
| Gate 8 Rubrics | src/webextractor/rubrics.py、docs/RUBRICS_PROTOCOL.md | 完整性、纯净度、结构 0—4 等级和连续比例；中文逐字、英文词/数字分词；有序 LCS；未标注 gold 返回 null；MAD 无重复时返回 null。 |
| Gate 9 SFT 数据 | tools/build_sft_dataset.py、docs/SFT_DATA_PROTOCOL.md、outputs/sft.agent.replay.v2.jsonl | 拒绝 gold/test/validation/held-out/凭据字段；输出 1 条样本，重复 0，SHA256=4873e4d1923770fa7eeaf615996b4a11866d3632935352a23f88f941de131273。仅一套合成模板，未训练。 |
| Gate 10 玩具 RL | src/webextractor/toy_rl.py、src/webextractor/dom_rl.py、tools/run_toy_rl.py、tools/run_dom_rl.py、docs/RL_TOY_PROTOCOL.md、docs/DOM_RL_PROTOCOL.md、outputs/rl_toy.v2.json、outputs/dom_rl.v3.json | 预设候选和实际本地 DOM 两种有限环境；实际环境通过受限 execute_rule 执行 XPath，记录状态、匹配和块数；不是工业 PPO/GRPO。 |

## 可复现命令

在 VS Code PowerShell 中：

    Set-Location 'D:\codex project\offline_web_extractor'
    .\run.cmd test
    python tools/run_cluster_ablations.py --output-dir outputs/clustering_reproduce
    python tools/run_toy_rl.py --output outputs/rl_toy.reproduce.json
    python tools/run_dom_rl.py --output outputs/dom_rl.reproduce.json
    python tools/build_sft_dataset.py --trace outputs/agent_lab.replay.v1.json --split-manifest samples/agent_lab/sft_manifest.json --output outputs/sft.reproduce.jsonl --report outputs/sft.reproduce.report.json
    .\run.cmd agent samples/agent_lab/references.json --replay samples/agent_lab/replay.json --output outputs/agent.reproduce.json

当前环境完整回归为 124 项通过。输出命令默认拒绝覆盖已有结果，请使用新文件名或目录。代理 127.0.0.1:7897 仅作为显式本机采集/模型请求选项，未写入数据、轨迹或离线结论。

## 5 分钟项目讲述

网页正文不是固定标签，导航、广告、评论、脚注、代码和列表会与正文混在 DOM 中；逐页调用模型成本高，固定规则又会受到模板漂移影响。项目先用 lxml 建立可解释的规则提取器，再以块文本 precision/recall、完整性、纯净度和结构共同评测。Trafilatura 只作为同 HTML、同参数、同版本的静态基线。

DOM 标签路径 Jaccard 只生成共享规则候选：正文长度会造成漏聚，短路径会造成漂移误聚，连通分量还会链式合并。受限 Agent 只提出 version=1 的容器/排除 XPath JSON；执行器拒绝任意 Python、零匹配、多匹配和容器外删除，并把反馈传给下一轮。reference/test 分离保证 gold 不进入提示。

Rubrics 分解完整性、纯净度和结构，并把成功轨迹整理成切分约束的 SFT JSONL。玩具 RL 显示只看长度或召回会选择 long-noise；加入 precision、结构和终止条件后才偏向 exact，说明奖励设计必须先经过失败案例审计。

## 尚未执行

- 没有真实 Qwen API 调用，因此没有真实 token、费用、网络耗时或模型生成能力结果。
- configs/ms_swift_lora.example.json 是 NOT_RUN_EXAMPLE 审阅计划；没有安装训练依赖、下载模型或训练。
- RL 是无外部依赖的一步 bandit，GRPO-like 只展示组相对优势。
- 真实标注规模仍小，部分数据为助手独立转录或受控合成页面，不能据此估计工业准确率或成本收益。



## CC Switch GPT MVP 本轮交付

最新结果以本节为准。真实Qwen依旧未调用；CC Switch返回模型名gpt-5.6-sol已完成真实调用，不将中转站名称作为官方模型身份验证。

真实smoke证据：outputs/agent.ccswitch.smoke.v2.json。两页合成reference，1次生成，规则 `//*[@role='main']`，两页均唯一命中且非空。输入489、输出23、合计512 tokens；provider约2.032秒，完整Agent约2.282秒；finish_reason=stop。无可验证单价，货币成本为null。该次quality_evaluated=false，只表示reference运行通过。

保存规则的后续真实网页迁移：outputs/mvp_demo.v1/report.json 与 index.html。本次新增API调用0，保留来源trace哈希、HTML/gold清单哈希、实现哈希与逐页执行结果。

| 开发快照 | 与Sphinx模板关系 | GPT保存规则状态 | 块文本P/R | 结构匹配 | 手写规则对照 |
| --- | --- | --- | --- | --- | --- |
| Python课前甜点 | 同模板案例 | ok | 1.0 / 1.0 | true | P/R=1.0，结构true |
| Python Executive Summary | 跨模板压力案例 | ok | 1.0 / 1.0 | true | P/R=1.0，结构true |
| IANA Example Domains | 跨模板压力案例 | rule_no_match | 0 / 0 | 未评分 | P/R=1.0，结构true |

P/R按整块文本完全匹配并处理重复次数，非字符或token级指标。结构比较保留顺序、kind、列表属性、标题层级与脚注属性。IANA失败因为该页缺少对应role，未用test反馈修复规则。不能从3个历史开发快照推出工业泛化能力或降本百分比。

上述离线迁移属于先行证据。随后已完成下节记录的真实网页reference驱动端到端实验；两类结果分别保留，不混用。

本轮修复的评测缺陷：旧load_manifest在生成前读取test/gold（未传模型）；现改为生成后读取并有顺序测试。结构比较统一双方字段；reference/test重复路径或哈希拒绝。最新全量回归124项通过。

## 真实网页 reference 驱动的 GPT 实验（最终验收）

证据：outputs/agent.ccswitch.mvp.v2.json；展示：outputs/mvp_real.v2/index.html。凭据由用户指定的本机env.local在进程内读取，未写入报告。

- 模型请求名/返回名：gpt-5.6-sol / gpt-5.6-sol；finish_reason=stop。
- Reference：python_interpreter_zh.html，完整30,262字节；模型证据窗口前16,000字符，truncated=true；执行器使用完整HTML。
- 生成调用：1次，默认零网络重试，未触发修复；runtime_accepted=true，quality_evaluated=true。
- 用量：input=5,633，output=334，total=5,967 tokens。provider约7.985秒，Agent约8.172秒。无验证单价，cost=null。
- 规则：`//div[@role='main' and contains(concat(' ', normalize-space(@class), ' '), ' body ')]/section[1]`；排除其内部headerlink锚点。

| test | 类型 | 执行状态 | 块文本P/R | 标题/结构 |
| --- | --- | --- | --- | --- |
| python_appetite_zh | Sphinx同模板 | ok | 1.0 / 1.0 | 均匹配；16块 |
| python_blurb | 跨模板压力案例 | rule_no_match | 0 / 0 | 未评分 |
| iana_example_domains | 跨模板压力案例 | rule_no_match | 0 / 0 | 未评分 |

该结果展示按模板生成和复用规则的MVP。先前手写规则对照在这三页均P/R=1.0且结构匹配。没有同模板运行失败，因此未强行追加修复调用；修复状态机由离线测试和合成回放覆盖，不宣称本次真实模型修复收益。未按跨模板test反馈选择新规则。

范围调整：为小预算MVP使用1个reference与1个同模板test，另加2个跨模板压力案例；没有执行原扩展计划中的2—3个reference或三组真实调用消融。历史开发gold、有限证据窗口和单个同模板test限制了结论；不报告总体泛化率。SFT/LoRA和工业RL留在可选扩展范围，本轮在基本交付处停止。

## 2026-11-17 调用源切换：Qwen

当前模型源为DashScope官方兼容接口，模型qwen3.8-27b。当前进程读取到QWEN_API_KEY；用户级查询未读到值。已验证官方模型列表及一次真实生成。新结果outputs/agent.qwen38.mvp.v1.json，展示outputs/mvp_qwen38.v1/index.html。GPT历史报告保留。

1次请求，输入5568/输出64/总计5632 tokens，Agent约3.14秒，返回model=qwen3.8-27b、finish_reason=stop。同模板16块文本与结构完全匹配；title_exact=false，因为生成规则排除section-number，将“1. 课前甜点”变成“课前甜点”。两页跨模板rule_no_match。未利用test结果修复规则。

CLI新增--provider qwen及--model，默认Qwen模型qwen3.8-27b；replay默认与ccswitch显式入口保留。QWEN_API_KEY优先于DASHSCOPE_API_KEY；Qwen3规则生成关闭thinking，保存返回模型/finish_reason，拒绝截断响应。全量129项测试通过，日志outputs/qwen38_tests.v2.log。源代码末次修复为空choices响应的错误处理，真实调用时的实现哈希仍按原报告保留。
