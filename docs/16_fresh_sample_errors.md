# 实操16：从多页首次结果区分问题

本轮不修改提取规则。GNU、NASA、GitHub、W3C 短页均先独立审读原HTML、冻结 expected 哈希和源码快照，再运行首次预测。标注由助手使用独立 DOM 脚本辅助转录，未经用户逐项复核；不称为多人复核金标。

同版本开发汇总见 outputs/expanded_development.frozen.md。它使用当前冻结源码、W3C引用v2参考；历史首次报告仍绑定各自原答案。两种汇总不得混作同一次统一协议实验。

源码快照：baselines/rules-gate2-first-pass。首次评测记录：samples/freeze_gate2_round1.json、freeze_gate2_github.json、freeze_gate2_w3c_link.json。

| 页面 | 发现 | 错误分类 | 当前处理 |
| --- | --- | --- | --- |
| GNU | 文章 h2 未作为 title；目录形成重复列表 | 标题识别、噪声边界 | 保留失败，后续统一修复 |
| GNU | 27组dt/dd未表达；普通列表脚注类型不同 | 不支持结构 | 不从标准答案删内容 |
| NASA | 20个标准块全找到，额外15块 | 署名、记者联系、分享、推荐边界 | 文本召回1.0仍不代表正文正确 |
| GitHub | 分享、标签、作者简介、推荐、订阅混入 | 容器过宽、局部边界 | 单取post__content也仍含作者信息，需综合判断 |
| GitHub | 正文aside含损坏列表，整块被丢弃 | 正文强调框、坏HTML恢复 | 记录恢复需求，不逐词删噪声 |
| GitHub/W3C | 引用包装分别标quote与paragraph | 标注协议差异 | 不计为同一种内容丢失；基线前统一版本 |
| W3C短页 | 预测为no_candidate、0/22块 | 候选集合不覆盖该页布局 | 不是段落长度阈值导致；保留失败 |

查看 outputs/gate2_first_pass_errors.md：它列出多提、漏匹配和类型统计；精确文本块不匹配可能源于拆分方式，不能简单等同正文字符消失。

复现诊断：

    python tools/summarize_first_pass.py outputs/mdn.candidate.first_evaluation.json outputs/gnu.candidate.first_evaluation.json outputs/nasa-voyager-news.candidate.first_evaluation.json outputs/github-copilot-blog.candidate.first_evaluation.json outputs/w3c-link-text.candidate.first_evaluation.json --output outputs/gate2_first_pass_errors.md

此命令只读报告，不重新运行提取或覆盖首次结果。Python 使用 run.cmd 所选择的同一个解释器即可。

动手检查：打开NASA首次报告，定位20/20正文之外的多提内容，分别归为发布元数据、记者联系和页面推荐。这比继续调整单一“段落长度阈值”更能解释失败原因。
