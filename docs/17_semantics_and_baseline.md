# 实操17：通用结构修复、静态基线和封存验证

本轮按多页首轮证据修复生产代码，标准答案与首次报告没有覆盖。生产版本完成后才打开web.dev封存验证结果；不据该页调整规则。

## 改动与验证

- 正文候选增加class精确token article、entry-content、post__content，以及id=main；显式正文容器有少量评分优先，仍是启发式。
- 标题优先当前或附近article/main的h1，再考虑正文开头h2，最后回退全站h1。对清理后的上下文定位标题，避免广告删除后位置变化导致删错节点。
- 窄正文容器与语义header关联时保留实际摘要p，并检查包含关系，避免重复。
- 保留正文孤立列表旁注；清除role=complementary、navigation、toc和author-bio。仍不保证所有aside都能正确分类。
- 新增quote、definition_term/description、被数字引用链接指向的普通列表footnote和孤立li恢复；引用与定义文字不再渲染成普通列表。
- 64项测试通过；旧开发集3真实+1合成保持结构全匹配；扩展5页标题全部正确，GNU133/133结构匹配。其余错误没有隐藏。

代码审查发现并修复了三处真实回归：局部h2覆盖祖先h1、header内部摘要重复、清理前后位置XPath删错节点；各有最小回归用例。修复前快照/报告保留，最终源码见 baselines/rules-validation-release-v1。

## 成熟静态基线

Trafilatura 2.0.0隔离安装，生产与基线在同一个Python/lxml环境收到相同HTML bytes；固定参数、全文块文本投影、标题单列、预热后5次串行计时。协议与完整命令见 BASELINE_PROTOCOL.md；正式结果见 outputs/baseline.development.v2.md 和同名JSON。v1是审查修复前版本，不覆盖。

| 开发页 | 本项目字符P/R | Trafilatura字符P/R | 当前解释 |
| --- | --- | --- | --- |
| MDN | 0.9999 / 1.0000 | 0.9946 / 0.9588 | 文本接近，复杂列表块协议仍不同，不能说结构正确 |
| GNU | 1.0000 / 1.0000 | 0.9908 / 1.0000 | 本项目按本参考结构匹配；基线标题不同 |
| NASA | 0.9413 / 1.0000 | 0.9528 / 0.9982 | 本项目记者联系尾部仍混入 |
| GitHub | 0.9910 / 1.0000 | 0.9856 / 0.9443 | 本项目仍有标签/作者提示及伪标签碎片 |
| W3C短页 | 0.7089 / 1.0000 | 0.6951 / 1.0000 | 两者都带入系列介绍，边界仍差 |

这是已参与调参的5页开发比较，不能据此宣布优于成熟工具或估计工业准确率。有序token相似度、逐次耗时与正文投影在JSON中。计时依赖本机负载且工作量不同，本项目并非所有页面都更快。Trafilatura没有同构块schema，结构全匹配为null，不伪造比较。

## 封存验证：web.dev课程总览

先冻结源码、HTML与expected哈希：baselines/rules-validation-release-v1/manifest.json，再保存 outputs/webdev-learn-html.candidate.validation_first.json。

- status=ok，标题Learn HTML正确。
- 预测47块，参考45块；块文本precision=0.9362，recall=0.9778；blocks_exact=false。
- 开头段落混入Go back，额外带入Quiz标题及领徽章说明；真实开头因附加按钮文字而不再精确匹配，不是完全漏掉开头。
- 本轮不据此改规则。样本角色为validation_scored、tuning_used=false；来源、registry与冻结证据同步。
- 只有一个课程总览页，不能代表新闻/博客文章的未见站点表现。成熟基线仅跑开发组，此验证不包含基线对比，不能扩大报告范围。

## 学习动作与下一步

在VS Code打开 outputs/expanded_development.after_review.md，对照NASA剩余3块，解释为什么不能把所有含邮箱的段落都删掉（正文RSVP同样含邮箱）。再比较W3C两种方法的正文投影，观察共同边界错误。

样本、错误分析与成熟开发基线证据已齐；下一阶段完成固定XPath复用、0/多匹配和模板漂移报告，再整理规则项目交付。保留未支持结构和失败，不以逐页满分替代泛化实验。
