# 实操12：修复容器边界并回归验证

首次 W3C 验证暴露了一个容易误判的问题：预测选择了正确的 main#main，但清理规则把所有 aside 都删除了。这个页面的“总结”是正文主内容框 aside.box-full，侧栏推荐是 aside.box-aside，反馈框是 aside#helpimprove，它们不能使用同一条删除规则。

本次修正：

- 删除翻译说明 section.doc-note-translation；
- 保留正文 aside.box-full；
- 继续删除侧栏推荐和反馈框；
- 保留 details#examples，包括它的标题和“更多例子”列表。

使用同一份冻结标准答案重新评测，结果从首次的 57/61 块提升到 61/61 块：内容块精确率和召回率均为 1。首次报告仍保留在 outputs/w3c_accessibility_intro_zh.first_evaluation.json，修正后报告在 outputs/w3c_accessibility_intro_zh.after_boundary_evaluation.json。

paragraphs 仍是兼容字段，只收集普通 p 文本，因此数量少于结构化 blocks 是预期行为；列表项、标题和折叠内容应查看 blocks 或 Markdown 输出。

这次修正增加了 W3C 结构回归测试。测试的重点是：正文“总结”和“更多例子”必须保留，翻译说明和反馈框必须排除。
