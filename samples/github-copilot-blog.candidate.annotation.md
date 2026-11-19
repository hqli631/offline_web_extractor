# github-copilot-blog 人工范围笔记

状态：独立参考标注已冻结，待首次预测。2026-11-13 由助手审读原始 HTML 后采用 DOM 辅助转录，未经用户逐项复核；未运行生产提取器，未查看预测，未依据程序输出修改参考答案。

来源：https://github.blog/news-insights/product-news/github-copilot-is-generally-available-to-all-developers/

本地文件：github-copilot-blog.candidate.html

模板标签：blog

当前用途建议：development 首轮诊断；具体划分由主流程写入 registry。本页尚未参与规则修复。

- 文章标题：GitHub Copilot is generally available to all developers。
- 正文第一句（摘要，原文）：We’re making GitHub Copilot, an AI pair programmer that suggests code in your editor, generally available to all developers for $10 USD/month or $100 USD/year.
- 摘要第二句（保留）：It will also be free to use for verified students and maintainers of popular open source projects.
- 主体开头（原文）：At GitHub, it’s part of our mission to build technology that makes developers happy.
- 正文最后一段（原文）：GitHub Copilot is our first step toward empowering developers with AI. Starting today, it’s now available to all developers, and we’ll begin offering it to companies later this year. 🚀
- 保留：header 内的文章摘要；主体普通段落；三个 h2 小标题；介绍试用、价格和资格信息的 blockquote；功能框标题及三个功能列表项；正文超链接可见文字。没有正文代码块、表格、脚注。
- 排除：全站导航及移动端重复菜单；面包屑；作者姓名、用户名、发表/更新时间和阅读时长；Share 控件；封面图及正文图片（不 OCR，不把 alt 文本当正文）；文章 Tags；作者简介；More on / Related posts 推荐；订阅、营销卡片与网站页脚。
- 一处边界判断：blockquote 含免费试用入口，但同时说明学生及开源维护者资格，与本文发布内容直接相关，作为作者文章的一部分保留为 quote；正文后的通用 Copilot 推广图片和网站营销卡片排除。不能按 trial 或 Copilot 词汇一概删除。

## 原始 DOM 范围

- 标题：//main[@id='start-of-content']/header//h1。
- 摘要：//main[@id='start-of-content']/header//p，唯一一段。它不在 section.post__content 内，单取后者会遗漏摘要。
- 主体：//section[contains(concat(' ', normalize-space(@class), ' '), ' post__content ')]，绝对路径 /html/body/main/div[1]/div/section。
- 主体直接子节点 0—16 属于正文；索引 17 的 section 为 Tags，18 的 div 为 Written by 作者简介，两者排除。上述索引只用于审计固定快照，不作为生产规则。

## 结构与原文异常的标注决定

- 三个 h2：The wait is over；Free for verified students and maintainers of popular open source projects；Coming to companies later this year。标题锚点中的空 heading-hash 控件不产生文本。
- 功能 aside 是正文，保留标题 GitHub Copilot enables developers to 及三个功能项：Get AI-based coding suggestions；Use your preferred environment；Code confidently in unfamiliar territory。
- 该 aside 的原始 HTML 已损坏：两个 p 分别含字面文本 `<` 和 `ul>`，三个 li 没有有效 ul 父节点。标准答案按已审读的语义重建为 ul list_item，排除这两个伪标签碎片；原始 HTML 不修写。此处是明确的标注决定，首次预测若不一致应记录为坏 HTML 的恢复/噪声问题。
- 引语使用 kind=quote，不丢掉其原有语义。paragraphs 旧视图仍收录引语中的 p。标题和 list_item 不计入旧 p 视图；伪标签碎片与空图片 p 不计入。
- 普通文本合并空白，保留内联文本之间源中实际的空格、曲引号、破折号与 emoji；从 source 的 UTF-8 明确解码，避免 lxml 无编码声明时回退造成乱码。

## 冻结证据

- HTML SHA256：c0cb2ed0cf8a6c40e9b87a10b13d07a0f9ee3cd02356159a1ebfd0a9a756ca8c。
- expected 文件：github-copilot-blog.candidate.expected.json。
- expected SHA256：c8526595a786e3867e3cd6ae57293b66e44a2b31626cf1179d096e8df47eca92。
- 结构块：20，包含 paragraph 13、quote 1、heading 3、list_item 3；旧 paragraphs 14。
- 辅助脚本：tools/annotations/github_reference.py。按原始 DOM 审读后明确选择固定节点并检查结构，没有调用 src 提取/清理/渲染代码；不是人工逐字键入的独立多人金标。脚本以独占写入拒绝覆盖现有 expected。
- 只验证参考 JSON 可解析、源哈希、块数和边界；未运行生产提取器，未生成效果报告。首次评测前由主流程再确认协议版本与 source/registry 状态。

先人工确定正文边界，再独立转录 expected.json；首次预测前不能依据程序输出修改标准答案。快照为完整响应，未静默截断。
