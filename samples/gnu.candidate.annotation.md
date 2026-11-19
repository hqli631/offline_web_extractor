# gnu-free-sw 人工范围笔记

状态：独立标注已冻结，待首次预测。2026-11-13 按已记录协议审读原始 HTML，由助手使用独立 DOM 辅助转录；范围未经用户逐项复核。未调用项目提取器、未查看预测。

来源：https://www.gnu.org/philosophy/free-sw.html

本地文件：gnu.candidate.html

模板标签：organization-essay

## 原始正文边界

- 文章标题：What is Free Software?（原网页使用 h2，不是 h1）。
- 正文第一句：“Free software” means software that respects users' freedom and community.
- 正文最后一句（包含正文脚注）：Rather than renumber the others, we made it freedom 0.
- 正文候选：//div[contains(concat(' ', normalize-space(@class), ' '), ' article ') and contains(concat(' ', normalize-space(@class), ' '), ' reduced-width ')]。它位于 div#content 内，但仍含页内目录和许可咨询提示，不能直接视为完全干净的正文。
- HTML SHA256：b050aa1bcbf73c225c0bcabd377e1015a4c602556eb6d9f13f0eb2d5ba8973d6。

## 应保留的内容与结构

- 标题，以及开头 div.important 内两段定义说明。important 是正文强调框，应保留。
- 普通说明段落和正文链接文字。链接目的地不展开抓取。
- h3/h4 小标题保持源层级；主标题单独存入 title。
- The Free Software Definition；The four essential freedoms；Free software can be commercial。
- Clarifying the Boundary Between Free and Nonfree 及其各 h4 小节：run the program、study the source code、redistribute、Copyleft、packaging、Export regulations、Legal considerations、Contract-based licenses。
- The Free Software Definition in Practice 及其三个 h4 小节；Beyond Software。
- 四项基本自由列表，保留原文 freedom 0、1、2、3 的语义；不要因展示序号重新编号而改写原文。
- History 小节：保留介绍段、所有版本 dt/dd 条目、Version 1.74 下嵌套列表，以及版本号有空缺的解释段。这里描述定义的实质变更，是文章附录内容；与页面底部 Updated 元数据不同。
- Footnote 标题及 li#f1 的完整说明，保留正文中的 [1] 引用；脚注正文只出现一次。该页脚注实际用普通 ol/li 标记，不能假定一定有 role=doc-footnote 或 aside.footnote。
- 未发现正文 pre 代码块或 table 表格。图片和图标不做 OCR。

## 应排除的内容

- 顶部 Skip to main text、募捐横幅 div#fundraiser、GNU 标识、搜索/语言按钮、全站导航 div#navigation。
- div.breadcrumb 面包屑。
- div.toc 页内目录及其 Table of contents 标题；这些链接重复了后续真实小标题。
- div#fsf-licensing.edu-note 许可咨询提示（role=complementary）：推荐其他资源并提供联系地址，按咨询入口排除。正文内 Get help with free licenses 小节仍保留，不能只按 licensing 或 mailto 关键词删内容。
- 正文之后 div#language-container 的语言切换和 BACK TO TOP、div#mission-statement 机构介绍、加入/募捐/商店按钮。
- div#footer 的一般联系方式、翻译协作、版权、页面许可、侵权通知和 Updated 时间。

## 一处需要实际核对的边界

在原始 HTML 中对照 h3#History 和页脚 Updated：前者的版本记录说明自由软件定义如何改变，纳入正文；后者仅说明网页维护时间，应排除。Version 1.169 原文为“Explain more clearly why the four freedoms must apply to commercial activity. Explain why the four freedoms imply the freedom not to run the program and the freedom to delete it, so there is no need to state those as separate requirements.”，描述定义的实质调整，不能按更新时间删除。

## 冻结标准答案前的工程检查

本页冻结协议：dt 为 definition_term，dd 为 definition_description；Version 1.74 的 dd 先保留介绍句，再依原文顺序保留四个 list_item（ul、depth=0，因为没有外层列表）。普通 ol/li 脚注按 footnote 保存，footnote_label 为 [1]、source_id 为 f1；正文只出现一次。文章级 h2 只存 title，h3/h4 保持源层级。没有支持的结构也保留在标准答案中，首次报告应如实记为漏提或结构问题。

## 冻结证据

- expected 文件：gnu.candidate.expected.json。
- SHA256：a3d2e3c0d84b06a28b1e45894cc2faa37209310728c9cf0b17bad35aeef6dbd0。
- 内容：133 blocks；51 paragraphs；19 heading；8 list_item；27 definition_term；27 definition_description；1 footnote。
- 来源直接子节点逐项核对：文章容器77个元素；排除索引0（主标题，独立存title）、1/74（空装饰）、5（目录）、6（咨询入口）。保留其余节点，按源顺序转录。
- 转录脚本：tools/annotations/gnu_reference.py。只读取原始 HTML，不导入 src，不读取预测；输出采用独占创建，防止覆盖冻结标准。
- 核对：范围内非空白字符与转录块在数量及顺序上对照；脚注 source_id=f1 仅出现一次。此为独立 DOM 辅助标注，不宣称已经过用户人工逐字复核。
- 当前尚未运行首次预测；之后若修改范围或协议，应另存标注版本并保留此哈希及首次报告。

## 约定

先人工确定正文边界，再独立转录 expected.json；首次预测前不能用程序结果修改标准答案。若页面包含目录、代码、表格、图片或折叠内容，分别记录是否纳入及原因。
