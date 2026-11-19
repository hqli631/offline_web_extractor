# Qwen 可选提供者

`qwen_provider.py` 实现 DashScope 的 OpenAI 兼容 chat-completions 请求，但初始化和测试不联网。真实调用前需显式配置用户环境变量 `QWEN_API_KEY`、模型、预算和超时。为兼容已有 DashScope 配置，也接受 `DASHSCOPE_API_KEY`。密钥不写入代码、快照或 trace。

提供者只接受 HTTPS 官方 DashScope 端点（禁止用户信息、查询参数、非443端口），默认不继承系统代理环境变量，并拒绝重定向以避免把 Authorization 转发到其他主机。显式代理仅允许无认证的本机 `127.0.0.1`/`localhost`，端口限于80、443或7897；响应上限为2 MiB。请求重试最多一次且共享总时间预算；JSON、规则结构或响应过大等确定性错误不会重试。

默认端点为 DashScope 官方兼容端点，只允许两个 DashScope 主机。代理必须显式传入，例如本机 Clash 的 `http://127.0.0.1:7897`；不会自动读取系统代理，也不会把代理地址写入报告。

命令行可显式选择 Qwen provider；默认模型为用户指定的 `qwen3.8-27b`：

```powershell
Set-Location 'D:\codex project\offline_web_extractor'
python -m src.webextractor.agent_cli samples/agent_lab/references.json --provider qwen --model qwen3.8-27b --output outputs/agent.qwen3.8-27b.json --max-attempts 1 --max-output-tokens 512 --total-timeout 90
```

不指定 `--model` 时，`--provider qwen` 仍使用 `qwen3.8-27b`；`--provider replay` 保持离线默认行为，`--provider ccswitch` 仍使用 CC Switch 设置。当前是否真实成功以输出 trace 的 `status`、返回模型和 `usage` 为准。

时间边界：重试前使用单调时钟计算剩余预算，urllib 超时用于连接和阻塞读操作；这是网络软时限，持续缓慢返回数据的服务仍可能超过总时限，不能据此声称线程可被硬终止。需要严格墙钟上限时应由调用层以可终止进程隔离网络提供者。定向7项mock测试覆盖重试预算、重定向、默认代理、响应上限和错误脱敏，未发起网络请求。

## 2026-11-17 实际接入结果

当前调用源为DashScope官方兼容接口，模型qwen3.8-27b。QWEN_API_KEY已在当前进程环境读取成功（用户级变量查询未读到值），不会打印或写入trace；优先于DASHSCOPE_API_KEY。服务端模型列表包含该模型，真实生成响应返回相同模型名。

Qwen3系列规则生成请求显式关闭thinking，记录返回model与finish_reason，截断响应拒绝接受。本次默认零重试，1次生成。输入5568、输出64、总计5632 tokens，Agent约3.14秒。

证据：outputs/agent.qwen38.mvp.v1.json。同模板课前甜点16块P/R=1.0且结构匹配；标题由“1. 课前甜点”变成“课前甜点”，因为模型排除了section-number节点，title_exact=false。两个跨模板页面rule_no_match。未针对test结果追加修复或改变规则。仍是历史开发集，不能估计总体准确率。

复现完整评测（真实API费用，选择新文件名）：

```powershell
python tools/run_qwen_eval.py samples/mvp_agent_manifest.v2.json --model qwen3.8-27b --output outputs/agent.qwen38.reproduce.json
```

已保存报告可用tools/render_agent_report.py离线渲染，无需再次调用。CC Switch历史结果和显式入口保留。
