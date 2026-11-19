# 项目收尾计划

更新时间：2026-11-15

本文把离线网页正文提取工程从学习原型收束为可复现交付。每个阶段保留代码、数据、命令、原始结果和限制；不把小样本、回放或中转站模型结果写成工业泛化结论。

## 当前基线

- Gate 1—4 已完成：规则提取、结构化块、独立评测、静态基线、固定规则复用和模板漂移。
- Gate 5—11 的离线原型已完成：DOM 聚簇、受限 Agent 回放、跨样本评测、Rubrics、SFT 数据准备和玩具/DOM-backed RL。
- 当前完整回归为 120 项通过（原有 117 项 + OpenAI-compatible provider 定向测试 3 项）。
- CC Switch 的 OpenAI-compatible 接口已通过两次人工烟雾测试：模型列表可读，JSON 规则 schema 可解析。真实网页尚未发送给 GPT。
- `src/webextractor/qwen_provider.py` 只允许 DashScope 官方端点，不修改其白名单；CC Switch 使用独立 provider。

## 阶段 1：GPT provider 工程接入

任务：

1. 新增独立 `OpenAICompatibleProvider`，读取 `CCSWITCH_API_KEY`、`CCSWITCH_BASE_URL` 和 `CCSWITCH_MODEL`。
2. 复用 `rule_agent.generate` contract，返回 `content` 和可校验的 usage。
3. 固定 HTTPS 主机、禁止重定向和隐式系统代理；响应大小、字符数、请求超时和总预算受本地限制。
4. 默认不重试，明确配置时最多一次重试，避免重复计费。
5. 记录请求模型、响应模型、finish reason、usage 和错误类型；密钥不进入日志、trace 或输出文件。
6. 增加全离线 mock 测试，不把测试 API key 或真实网页发送到网络。

验收：provider 定向测试通过；原有 Qwen 测试不回归；非法 JSON、截断、重复键、重定向、超大响应、超时和 HTTP 错误均有明确处理。

## 阶段 2：Agent CLI 接入与离线回放

当前状态：provider 与显式 CLI provider 选择已完成；replay 默认行为保持可用。

任务：

1. CLI 增加显式 provider 选择，默认仍使用 replay，真实网络必须通过明确参数开启。
2. 接入现有 `run_agent`，保持 reference/test/gold 隔离、唯一容器校验、排除范围校验和可终止 XPath 执行。
3. 保存脱敏 trace、模型名、usage、调用次数、耗时、规则和每轮执行反馈。
4. 用 mock provider 重放成功、零匹配、多匹配、非法规则和一次修复。

验收：离线 replay 与现有结果一致；CLI 错误码稳定；没有 API key 或网络参数时不会发送请求。

## 阶段 3：小预算真实 GPT 实验

前置条件：API key 仅在本机或云服务器临时环境变量中设置；遵循用户当前服务器配置；只使用公开或已脱敏的 reference HTML。

任务：

1. 选择 2—3 个同模板 development reference 页面，先运行一次生成、最多一次修复。
2. 单独准备未参与提示和规则选择的 test 页面；生成结束后才加载 test/gold。
3. 对比手写规则、GPT 一次生成、GPT 一次修复三组。
4. 记录唯一匹配率、块 precision/recall、Rubrics、调用次数、输入/输出 token、耗时和失败原因。
5. 使用小额预算和硬性调用上限；中转站返回模型名必须原样记录，不能推断模型别名或能力。

验收：至少一份可复现真实实验报告；若请求失败或预算不足，保留失败 trace，不报告模型收益。

## 阶段 4：第二阶段数据集收束

任务：

1. 保留 `samples/dom_similarity.stage2.v1.json` 和聚簇历史结果，补充站点/模板盘点记录。
2. 明确 development、reference、test、validation 的用途和哈希；已用于调参的页面不得重新标为 validation。
3. 需要扩展时，每个模板至少三个页面，覆盖同站不同模板和全新 validation 模板；完整响应先验收再入清单。
4. 人工冻结正文边界后才生成 gold；来源、状态、字节数、编码和 SHA256 一并保存。

验收：数据清单可以回答页面来源、模板、切分、历史使用和哈希；没有把聚簇分数当作正文质量。

## 阶段 5：SFT/LoRA 与 RL 的可选扩展

只有阶段 3、4 具备足够真实轨迹和独立验证后才进入。先做离线评测和数据审计，再决定是否使用云 GPU；没有资源则保留配置和未执行状态。不得用一条合成样本宣称训练收益，也不得把 toy GRPO-like 结果写成工业 Agentic RL。

## 阶段 6：最终交付

交付内容：

- README、项目收尾计划、执行跟踪和最终报告；
- 可复现 `run.cmd test`、Agent replay、聚簇和评测命令；
- provider mock 测试与真实实验（若执行）；
- 代表性成功/失败案例、数据切分、版本和哈希；
- 五分钟项目讲述和限制清单。

最终报告必须区分：离线确定性结果、合成漂移结果、真实网页开发结果、真实 GPT 结果、训练未执行项。所有收益绑定样本数、来源、切分、模型、预算和原始输出。

## 暂不做的事项

- 不在聊天中保存服务器密码或 API key。
- 不把中转站 API 当作官方 OpenAI 服务或模型能力证明。
- 不直接修改 Qwen provider 以接受任意 endpoint。
- 不在没有独立 test/validation 的情况下调参、训练或发布准确率。
- 不重复运行已经回答问题的 DOM 特征消融。

## 当前执行记录

- 失败复盘：`outputs/agent.ccswitch.smoke.v1.json` 的 `ValueError: Provider must return content and optional usage only` 来自 provider 返回的 `model/finish_reason` 未被旧 Agent contract 接受；已扩展 contract 并通过全量回归。
- 新增 `tools/run_ccswitch_eval.py`，在 Agent 生成结束后才加载 test/gold，并保存质量报告。

- 2026-11-15：完成 CC Switch GPT 连通性与 JSON schema 人工烟雾测试。
- 2026-11-15：新增 `src/webextractor/openai_provider.py` 及 3 项离线 mock 测试；全量回归 120 项通过。
- 真实 GPT smoke 已发送合成 reference，但首次 trace 因 provider metadata contract 不兼容而失败；该失败已修复，需重跑验证。真实网页尚未发送给 GPT；云端部署尚未验收。




## 2026-11-15 本轮验收更新（以本节为准）

- 阶段1—2完成：CC Switch provider、metadata contract、显式 CLI、离线回归均通过。最新全量124项测试通过。
- 阶段3完成最小范围：真实网页生成评测见最终记录；此前outputs/agent.ccswitch.smoke.v2.json 为真实API成功证据（合成reference，489/23/512 tokens，2.282秒整体、2.032秒provider）。outputs/mvp_demo.v1/report.json 为其规则的真实网页离线迁移质量结果，新增API调用0。
- 阶段4最小清单完成：保留旧清单，新建mvp_agent_manifest.v2.json，明确1个同模板test和2个跨模板压力案例；均为development，HTML/gold固定SHA256。
- 评测审计已修复：test/gold生成后读取；跨split路径或哈希重叠拒绝；结构比较包含标题层级和脚注字段。
- 阶段5不进入：此次MVP不需要LoRA或工业RL。
- 阶段6已整理现有证据和效果页。真实网页reference驱动生成已完成，详见下节最终记录。

不重复聚簇消融，不扩展新功能，不因IANA跨模板失败修改冻结规则。此次记录展示失败边界。API Key由用户指定的本机env.local仅在评测进程读取；无需将Key发送到聊天。

## 最终执行记录

- 用户指定env.local后完成一次真实请求，输出outputs/agent.ccswitch.mvp.v2.json。gpt-5.6-sol，5967 tokens，8.172秒；同模板test 16块完全匹配，两个跨模板压力案例零匹配。
- 阶段3以最小预算范围验收：1个reference/1个同模板test/2个跨模板压力案例；仅一次真实生成，不强行触发修复。2—3 reference和三组真实消融保留为后续研究，非本次基本交付条件。
- 阶段4数据用途和哈希已冻结；阶段5不进入；阶段6报告、效果页与复现入口已完成。
- 最新状态以最终报告末节与验收记录为准；早期执行记录作为历史保留。达到MVP后停止扩展。
