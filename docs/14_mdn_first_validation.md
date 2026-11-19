# 实操14：MDN 首轮结果与剩余问题

用户已确认保留前提与学习目标、参见链接文字、代码结构。范围见 samples/mdn.candidate.annotation.md；本次确认没有改动原 expected。

expected SHA256：a2e13751b3bf4657cf0995bef9f78fe160328df885e7a90c1550269528eadd89。141 个 blocks、97 个旧 p 段落。标题、开头内容和主体跨两个布局区域，不能只用主体区域代替全文。

| 结果 | 预测块 / 标准块 | 块文本 precision | 块文本 recall |
| --- | --- | --- | --- |
| first_evaluation | 156 / 141 | 0.8782 | 0.9716 |
| after_boundary_evaluation | 145 / 141 | 0.9586 | 0.9858 |

报告保存在 outputs/mdn.candidate.first_evaluation.json 和 outputs/mdn.candidate.after_boundary_evaluation.json，均保留原文件。后续表格渲染修复的结果另存 current，不能覆盖首次结果。

本轮修复了翻译横幅、目录、上下页导航、文章页脚等语义噪声，并加入基础 table 块。table 在 Markdown 中按文本围栏呈现行列；尚不支持合并单元格或复杂嵌套结构。

剩余主要差异：两个复杂列表项包含说明、嵌套代码和后续说明；标准答案把一部分内容合为一项，而程序拆成 list_item、code、list_item_continuation。blocks_exact 仍为 false。应先统一结构协议并记录标注修订版本，再评测；不能只改答案让结果过关，也不能把这些差异一概算成正文丢失。

旧 p 字符召回没有同步提升，因此不能仅用块文本指标宣布整体效果改善。块文本匹配不检查顺序和结构属性，结构需查看 blocks_exact；正文字符粗指标仍基于旧 p 视图。

MDN 已用于修改规则，当前为开发回归样本。首次报告是历史初始验证证据，修复后结果不具有未调参验证含义。停止逐页补规则，先扩充新闻、博客和其他真实页面，再统一错误分类。

复现当前结果：

    .\run.cmd evaluate samples/mdn.candidate.html --expected samples/mdn.candidate.expected.json --output outputs/mdn.candidate.current_evaluation.json
    .\run.cmd extract samples/mdn.candidate.html --output outputs/mdn.candidate.current.json --text-output outputs/mdn.candidate.current.md
