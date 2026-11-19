# 离线网页正文提取学习工程

Rubrics 改进进度见 [v2评分协议](docs/RUBRICS_V2_PROTOCOL.md) 和 [节点记录](docs/RUBRICS_CHECKPOINTS.md)。

Rubrics 节点1–4已交付：[Judge可复现报告](docs/RUBRICS_JUDGE_REPORT.md)（批量16/23接受、稳定性5/6、187项测试、完整预算台账；silver一致性非人类准确率，节点5未进入）。

本工程记为“项目三”，当前进度及 Rubrics 后续路线见[项目三状态](docs/PROJECT_THREE_STATUS.md)。

当前模型调用源（2026-11-17）：DashScope Qwen，模型 `qwen3.8-27b`，使用环境变量 `QWEN_API_KEY`。已完成真实调用与原MVP清单评测，详见[Qwen配置](docs/QWEN_SETUP.md)和[真实报告](outputs/agent.qwen38.mvp.v1.json)。CC Switch/GPT结果作为历史保留，replay仍是无网络默认入口。

```powershell
./run.cmd agent samples/agent_lab/references.json --provider qwen --model qwen3.8-27b --max-attempts 1 --output outputs/agent.qwen.current.json
```


离线学习工程已完成阶段交付整理（Gate1—11）：规则提取、聚簇消融、受限Agent回放、跨样本评测、Rubrics、SFT数据准备和玩具RL均有可复现产物。当前129项测试通过。CC Switch GPT provider 已接入，真实 API smoke 与真实网页reference生成评测均成功，效果见下方。真实Qwen调用已执行；LoRA/QLoRA训练和工业规模Agentic RL尚未执行。

- [学习计划](docs/LEARNING_PLAN.md)
- [执行状态](docs/EXECUTION_TRACKER.md)
- [规则项目完整报告](docs/RULE_PROJECT_REPORT.md)
- [实操18：固定规则复用与漂移](docs/18_rule_drift.md)
- [实操19：DOM相似度原型](docs/19_dom_similarity.md)
- [实操20：DOM特征消融](docs/20_cluster_ablations.md)
- [Agent接口与回放](docs/AGENT_INTERFACE.md)
- [Qwen可选提供者配置](docs/QWEN_SETUP.md)
- [Gate7跨样本评测](docs/21_agent_cross_sample_evaluation.md)
- [Rubrics协议](docs/RUBRICS_PROTOCOL.md)
- [SFT数据协议](docs/SFT_DATA_PROTOCOL.md)
- [玩具RL协议](docs/RL_TOY_PROTOCOL.md)
- [实际DOM奖励实验](docs/DOM_RL_PROTOCOL.md)
- [最终阶段交付报告](docs/FINAL_DELIVERY_REPORT.md)
- [静态基线与封存验证](docs/17_semantics_and_baseline.md)

## 在VS Code终端运行

使用PowerShell中的.cmd入口，不需要改变脚本执行策略。

```powershell
Set-Location 'D:\codex project\offline_web_extractor'
.\run.cmd extract --show-candidates --output outputs/python_blurb.current.json
.\run.cmd test
.\run.cmd batch --output outputs/old_dev.current.json --report outputs/old_dev.current.md
.\run.cmd batch samples/evaluation_manifest.expanded_development.json --output outputs/expanded.current.json --report outputs/expanded.current.md
.\run.cmd reuse samples/sphinx_reuse.json --output-dir outputs/reuse.current
.\run.cmd reuse samples/drift_lab/reuse.json --output-dir outputs/drift.current
.\run.cmd cluster samples/dom_similarity.real_development.json --threshold 0.7 --output outputs/cluster.current.json --report outputs/cluster.current.md
```

.\run.cmd agent samples/agent_lab/references.json --replay samples/agent_lab/replay.json --output outputs/agent.current.json

reuse和cluster拒绝覆盖已有实验目录/文件；复现请选新输出名。受控漂移集故意包含0匹配和多匹配，退出码2符合预期。status=ok及退出0均不代表正文质量全匹配。

run.cmd依次寻找项目.venv、本机Codex运行时、系统Python；新环境需Python3.10+及requirements.txt中的lxml。成熟基线另使用.baseline-venv及requirements-baseline.txt，命令见BASELINE_PROTOCOL。

## 当前结果与限制

输出blocks保留段落、列表、标题、代码、基础表格、引用、定义项和基础脚注；body为Markdown，paragraphs只是旧p视图。尚不支持任意动态网页、OCR、复杂表格和所有裸div正文。源码与数据独立于旧web_extract_demo。

开发页包括已用于修复的MDN、GNU、NASA、GitHub、W3C等；web.dev课程总览仅在源码冻结后评分一次且不用于调参。样本用途与哈希见samples/sample_registry.json。6个新可用标注页（其中1个封存验证页）的结果不足以估计工业准确率。

规则复用已证明唯一匹配仍可能漏掉容器外末段；结构相似度消融显示短路径可能降低漏聚却增加漂移误聚。受限Agent回放只证明状态机能根据执行反馈修复XPath，不证明模型生成能力或正文质量；聚簇候选仍需执行规则和正文质量核验。历史首次预测、标注版本和修改前后报告全部保留。

早期学习从[实操01](docs/01_real_page.md)开始，各课描述当时版本，当前能力以本README和执行状态为准。





## GPT MVP 当前效果（2026-11-15）

[真实 GPT 效果页](outputs/mvp_real.v2/index.html) · [真实评测原始报告](outputs/agent.ccswitch.mvp.v2.json) · [CC Switch 配置](docs/CCSWITCH_SETUP.md)

CC Switch 返回模型名 `gpt-5.6-sol`。模型读取 Python 解释器公开快照前16,000字符，1次生成共享XPath；本地以完整reference运行校验后，固定规则用于test。同模板“课前甜点”的16个内容块全部匹配，标题与结构匹配，整块文本precision/recall均为1.0；跨模板的Python官网介绍页和IANA页面均为rule_no_match。输入5,633、输出334、共5,967 tokens，Agent约8.17秒。无单价，金额未估算。

真实评测与此前合成reference的smoke、保存规则离线迁移分别保留。本轮只有一个同模板开发test，使用历史标注，无独立泛化结论；跨模板失败未用来修复规则。新清单与实现哈希见原始报告。LoRA/QLoRA与工业RL未执行。

```powershell
# 重新渲染已有真实结果，无API调用，选择未存在的目录
python tools/render_agent_report.py outputs/agent.ccswitch.mvp.v2.json --output-dir outputs/mvp_real.reproduce
# 重建此前保存规则的离线迁移效果，无API调用
python tools/build_mvp_demo.py --output-dir outputs/mvp_demo.reproduce
```
