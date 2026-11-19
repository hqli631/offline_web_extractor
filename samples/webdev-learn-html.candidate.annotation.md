# webdev-learn-html 人工范围笔记

状态：独立参考标注已冻结，validation_reserved，尚未预测。本页由助手审读原始 HTML 并用独立 DOM 脚本辅助转录，未经用户逐项复核。禁止根据本页修改生产规则；冻结开发规则后才首次评分。

来源：https://web.dev/learn/html/

本地文件：webdev-learn-html.candidate.html

模板标签：course-overview（来源初始标签为 web-tutorial；内容审读后发现是课程总览/索引，而非独立教程文章）。

- 标题：Learn HTML。
- 正文第一句：This HTML course for web developers provides a solid overview for developers, from novice to expert level HTML.
- 正文最后一句：Wrapping up with some further resources.
- 范围：唯一 //main//devsite-playlist 中的课程标题、开头介绍，以及 type=article 的22个章节卡片各自的 h2 和 p。
- 应保留：课程主题与每章摘要是本页主要信息，按章节顺序保存 h2/paragraph；Welcome 章节摘要和开头介绍在原文重复，均保留，不能因文字相同去重。
- 应排除：全站导航、页面外课程侧栏、面包屑、Modern Web Guidance 公告、收藏功能、语言切换、Go back、Read article、Article 类型标记、展开/折叠按钮及图标、课程完成度控件、Quiz/领徽章交互、评分组件、站点页脚。
- 一处边界判断：章节卡片虽然主要通向其他页面，仍构成本页课程总览的主体；只保留标题和摘要，不展开目标文章。Quiz 是完成课程和获取徽章的交互入口，没有教学内容，整项排除。
- 图片/代码/列表/表格/脚注：本次声明范围内没有需要转录的这些结构；不做图片 OCR。

## 类型限制

本页可以评估“课程总览正文”的保留与去噪，但不应混入普通文章后宣称文档文章泛化。最终报告应单列 course-overview；如研究范围明确限制为连续文章，可将它改为分布外诊断样本，并另取完整短教程页作为主要验证。该判断必须在查看预测前记录。

## 编码与冻结证据

- HTML SHA256：921c15fafe14485c9891ea1ad6bac7f42779fd57ed71fabd34c82b66c9664cee。
- expected SHA256：77b2e873fbfacba5538064dddd3ad0ea6117647fe4a6564cbed4de95bf3961a7。
- expected 共45个结构块：1个开头 paragraph，22个 heading，22个章节 paragraph；旧 paragraphs 视图23段。
- 独立脚本：tools/annotations/webdev_reference.py，不导入生产代码、不读取预测；UTF-8显式解码，核对23个原始section，其中22个article、1个quiz。
- 现有 expected 再运行只核对相同序列，不覆盖不一致文件；需要修订时保留旧版本并说明原因。

采用 docs/ANNOTATION_PROTOCOL.md v1.1；先冻结正文边界及标准答案，再预测。当前只完成标注，未运行生产提取器。
