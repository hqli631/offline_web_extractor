# 实操11：新站点首次验证与错误分类

这次使用 W3C《Web无障碍简介》作为新站点，先人工确定边界，再生成标准答案，最后才运行提取。原始 HTML 没有改动，标准答案和首次报告都已保存；这个样本暂时属于 initial validation，不加入开发集。

## 冻结文件

- 原始快照：samples/w3c_accessibility_intro_zh.html
- 布局预览：samples/w3c_accessibility_intro_zh.preview.html
- 范围笔记：samples/w3c_accessibility_intro_zh.annotation.md
- 人工标准答案：samples/w3c_accessibility_intro_zh.expected.json
- 首次报告：outputs/w3c_accessibility_intro_zh.first_evaluation.json
- 初始验证清单：samples/evaluation_manifest.w3c_initial.json

HTML SHA256：0de81af8fa582694076469b16b198d43e32b27a62453ec7bdbef23c7db1607dc

标准答案 SHA256：2f856d9f6805dd186bbcc9af969d62f82d1f1fba0affeab0bee2800f8ee26fd4

## 首次结果

- 标题匹配：true
- 选择容器：/html/body/div/main
- 预测块数：57；标准答案块数：61
- 内容块精确率：0.9474
- 内容块召回率：0.8852
- 旧段落视图的字符精确率：0.9763
- 旧段落视图的字符召回率：0.8515

## 错误分类

1. 容器边界：程序选择了 /html/body/div/main。这个容器包含翻译说明，所以预测多出 About this translation 和翻译者段落；页面最前面的总结位于独立的 aside.box-full，没有被选进来。
2. 正文列表：正文的 ul 列表项没有出现在预测块中，导致列表内容漏提。
3. 折叠正文：details#examples 中的更多例子和三条正文链接没有被当前块遍历逻辑提取。

这次的结论不是改一个 XPath 就结束：候选容器、噪声规则和结构遍历是三个独立问题。下一步先针对容器边界设计候选对比，再决定是否扩展 details 和列表的支持；每次修改都要保留这份首次报告。

记录纠错（2026-11-13）：HTML SHA256 转录时漏写了一个 f，已按原文件校正；HTML 和首次预测未改动。本页已用于规则修复，当前归为 development。
