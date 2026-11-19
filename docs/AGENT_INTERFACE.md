# 单 Agent 受限规则接口与回放

这是 Gate 6 的工程原型。模型或回放提供者只输出 XPath 配置，不输出可执行 Python。当前 authored-replay 的响应由开发者写入，验证的是生成、执行、反馈、修复状态机，不能作为真实模型效果或调用成本报告。

## 输入和输出

rule_agent.run_agent(reference_pages, provider, ...) 的 reference_pages 只接受 id 和 source 两个字段。source 是完整 HTML 字符串或字节；最多 8 页，每页遵守执行器字节上限。expected、测试页字段不被接受。调用者负责保证这些页面确实属于参考组，不能靠重命名绕过数据切分。

模型证据为每页 HTML 前 evidence_chars 个字符、截断标记和完整输入 SHA256。字节输入按 UTF-8 替换解码仅供提示展示；实际执行保留原字节。较长或其他编码网页可能缺失关键证据，这属于当前证据构造限制。网页内容在指令中标为不可信数据；该提示不保证消除提示注入。

严格规则对象包含且仅包含 version（整数 1）、container_xpath（非空字符串）、exclude_xpaths（XPath 字符串列表）。执行器要求容器恰好一个元素，所有排除节点为容器后代；0 匹配、多匹配、标量 XPath、越界排除均返回明确失败。XPath 及抽取在可终止子进程执行。

每轮在所有参考页执行同一规则。反馈含执行状态、错误、匹配数、预测块数、标题及正文预览，不读标准答案。所有参考页均运行成功且有块时返回 runtime_accepted；这只证明规则可执行，内容完整性和纯净度须后续单独评测。

## 提供者协议和预算

provider.generate(prompt, timeout_seconds=remaining, max_output_tokens=limit) 返回 content 和可选 usage。content 为规则字典或严格 JSON 字符串；usage 只接受非负整数 input_tokens/output_tokens/total_tokens。未知费用保持 null，回放 token 也保持 null。

max_attempts 最多 10；默认 3。默认执行超时 5 秒、总计 60 秒、输出上限 1024 token、每页证据 16000 字符、响应 20000 字符。提供者须自身实现请求超时及 token 限制；主循环在响应后复查时间和已报告 token，不能强行终止不遵守协议的同步 provider。当前只有即时回放提供者；真实 Qwen 客户端尚未接入，不能声称网络硬超时已经实现。执行器子进程仍有独立硬超时。

max_attempts 表示总调用次数，修复次数最多为 max_attempts - 1。达到轮次、总时限或输出 token 上限时明确失败；非法响应和运行错误作为下一轮反馈。成本未配置价表时不记零。

## 轨迹与复现

轨迹保留设置、参考哈希与模型所见证据、每步完整提示、响应、规则、执行结果、反馈、耗时及可选 token。超出响应字符上限的响应仅保存省略原因和字符数。save_trace 使用独占创建，不覆盖历史实验。此模块不接收密钥或客户端配置；调用者也不得把凭据混入网页或 provider 返回内容。

samples/agent_lab/replay.json 首轮选择不存在的 article，第二轮改用 div 的 main role。用于 drift_lab/reference.html 和 class-drift.html 两个参考页。二者均为已知合成开发样本；不能报告为未见网页泛化。

定向验证：通过项目 Python 执行 -m unittest tests.test_rule_agent -v。真实 API、参考/测试冻结、手写/无修复/有修复对照，以及正文 Rubrics 均是后续工作。
