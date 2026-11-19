# W3C QA Tip：链接文字独立范围记录

状态：助手独立审读并冻结 expected；尚未首次预测，未经用户逐项复核。遵循 docs/ANNOTATION_PROTOCOL.md v1.1。2026-11-13。

来源：https://www.w3.org/QA/Tips/noClickHere

## 正文范围

- 标题：Don't use "click here" as link text。位于 div#main 的第一个 h2；banner 中的 h1 “Tips for Webmasters”是栏目名，不是文章标题。
- 第一段原文：When calling the user to action, use brief but meaningful link text that:
- 最后一个正文块原文：Mail thread on the www-qa list, suggesting this tip.
- 最后一个普通 p 原文：Tell me more about Amaya: W3C's free editor/browser that lets you create HTML, SVG, and MathML documents.
- 人工候选范围：//div[@id='main'] 中标题之后、h2#abouttips 之前的兄弟节点。包含 What a link means、An example、Further Reading 三节。

## 保留与排除

- 保留三处 h3（源层级3）、11个实际 p、两组各4项的无序列表。五个 blockquote 中的示例文字是文章论证的一部分，全部保留。
- Further Reading 是本篇建议的出处和延伸资料，保留4条参考文字；不抓取链接目标。
- 协议 v1.1 未定义 quote 包装块，因此 blockquote 内实际 p 保存为 paragraph；引语样式不在本轮结构比较范围，不能宣称完整保留引用视觉样式。
- 排除 W3C/QA 标识与栏目 h1、顶部导航、搜索框。
- 排除 h2#abouttips 起的通用栏目介绍：介绍 QA Tips 生产组织、非规范说明、投稿与 Tips Index 入口。这是系列级说明及推广，不属于链接文字建议的三节正文。
- 排除 address 中的创建者、投稿者、更新时间，以及版权、隐私、许可页脚。
- 无正文图片、pre代码块、table表格、脚注或description-list；不做OCR。行内示例词汇按普通文字保留。

## 独立转录与冻结

工具：tools/annotations/w3c_link_reference.py。该脚本只使用原始 HTML 的明确子节点范围，独立规范化文字；不导入生产 src、块遍历或 renderer，不读取任何预测。逐一审读了 div#main 的21个直接子元素：0为文章标题，1—16为三节正文，17—20为通用栏目说明。

- HTML SHA256：455f237d8b95ab058c974a660c10027fe65b79747beee872d4b6d987884527b5
- expected：22 blocks（3 heading、11 paragraph、8 list_item），11个旧 paragraphs。
- expected SHA256：ebaae88d7af06eeabd4bef5ef752c42ef45eae01e3b12a5716e6f26c19b40d16
- 冻结文件：samples/w3c-link-text.candidate.expected.json；脚本独占创建，已有答案只校验不覆盖。

边界判断：保留 Further Reading，排除 About the QA Tips。前者列本篇的链接文字写作资料；后者适用于整个 QA Tips 栏目，含投稿与索引推广。此判断先于程序预测确定。
