# CC Switch GPT 运行说明

当前真实评测已完成，结果在 `outputs/agent.ccswitch.mvp.v2.json`，可视化在 `outputs/mvp_real.v2/index.html`。不需要重复调用来查看结果。

需要重新实验时，在项目目录创建仅本机使用的 `env.local`（已加入忽略列表），每行一个设置：

```text
CCSWITCH_API_KEY=在本机填写你的Key
CCSWITCH_BASE_URL=https://tbnx.plus7.plus/v1
CCSWITCH_MODEL=gpt-5.6-sol
```

在 VS Code PowerShell 中运行，输出必须使用新文件名：

```powershell
Set-Location 'D:\codex project\offline_web_extractor'
& "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" tools/run_ccswitch_eval.py samples/mvp_agent_manifest.v2.json --env-file env.local --output outputs/agent.ccswitch.reproduce.json --max-attempts 1 --max-output-tokens 512 --total-timeout 90
```

该命令会产生真实API费用；默认最多一次生成、零provider重试、输出token上限512。模型默认gpt-5.6-sol，也可用 `--model` 显式指定。只发送清单reference，证据窗口默认16,000字符；完整reference由本地执行器校验。test/gold在Agent结束后读取。退出码0表示reference运行通过，质量须查看逐页指标。

仅渲染已保存的结果无需Key或网络：

```powershell
python tools/render_agent_report.py outputs/agent.ccswitch.mvp.v2.json --output-dir outputs/mvp_real.reproduce
```

每次实验保存请求与返回模型名、用量、耗时、规则、执行反馈、清单及实现哈希。没有中转站单价，因此金额为null。报告不会保存Key。此链路使用API，无需云GPU；没有进行服务器部署或训练验收。
