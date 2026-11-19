# Gate 9：SFT/LoRA 数据准备协议

本阶段只整理轨迹数据，不训练模型。输入是 quality_evaluated=false 的 Agent trace；Gate 7 测试页、expected、Rubrics 分数和 held-out 页面都禁止进入。每页先按模板和 split 冻结，再生成 JSONL。

`tools/build_sft_dataset.py` 拒绝 gold、expected、test、validation、secret、API key 等字段和值，检测重复样本，保存源 trace、split manifest 和输出 SHA256。每条记录含 reference evidence、attempt、rule、feedback、outcome、template_id 与 split；一个 trace 的所有参考页必须属于同一模板和 split。

运行：

    python tools/build_sft_dataset.py --trace outputs/agent_lab.replay.v1.json --split-manifest samples/agent_lab/sft_manifest.json --output outputs/sft.agent.replay.jsonl --report outputs/sft.agent.replay.report.json

当前回放是 train development fixture，没有真实 token、费用或训练收益。

## v2 审计与消息格式

v1原始输出保留不变。v2默认只导出所有参考页运行ok的尝试；失败尝试只有显式使用--include-failed时才进入诊断输出，不应直接当正向SFT标签。v2的messages为标准user/assistant对：user只含参考证据和先前尝试反馈，assistant只含当前规则。当前规则执行之后才产生的feedback保存在诊断字段，不进入user消息，避免使用未来观察预测当前动作。

    python tools/build_sft_dataset.py --trace outputs/agent_lab.replay.v1.json --split-manifest samples/agent_lab/sft_manifest.json --output outputs/sft.agent.replay.v2.jsonl --report outputs/sft.agent.replay.v2.report.json

v2输出1条训练格式样本，SHA256为4873e4d1923770fa7eeaf615996b4a11866d3632935352a23f88f941de131273。当前只有一个模板、两页已知合成参考及人工回放，没有独立SFT验证组；模板分割检查不等于真实数据独立性已获证明。输出中的accepted仅指运行成功，不能等价于质量合格。凭据检测是字段/模式检查，不能保证识别任意秘密，真实轨迹仍需人工审阅和来源许可检查。

configs/ms_swift_lora.example.json提供可审阅的LoRA参数计划，明确标记NOT_RUN_EXAMPLE；它不是可直接加载的ms-swift配置。具体参数须按安装版本文档核验后转换为CLI；未安装训练依赖、下载模型或运行训练。一个人工回放样本不足以训练正文提取能力，因此本阶段只验收数据导出与接口，不宣称Gate9的真实训练目标已经完成。
