# 实操05：批量评测与错误分析

版本说明：下文描述首次评测。当前已完成 [实操06](06_fix_breadcrumb_heading.md) 修复，IANA已移入development；首次失败报告为outputs/batch_report.before_iana_fix.md，最新batch_report为修复后的回归结果。

## 1. 先运行一条命令

VS Code 终端：

```powershell
.\run.cmd batch
```

打开 `outputs/batch_report.md`，按 Ctrl+Shift+V 查看。完整逐页结果及预测/标准答案位于 `outputs/batch_report.json`。本轮没有修改候选、去噪、结构提取规则，保持上轮版本来观察新布局表现。

## 2. 样本如何分组

清单为 `samples/evaluation_manifest.json`，其中路径相对于清单文件。

| 分组 | 样本 | 用途 |
| --- | --- | --- |
| development / real | Python 官网介绍、中文课前甜点 | 已用于改规则，检查回归 |
| development / synthetic | list_lab | 人工边界案例，检查结构处理 |
| validation / real | IANA Example Domains | 新布局，冻结规则后的第一次验证 |

这只有3篇真实网页，且两篇来自Python相关站点，远不足以估计岗位真实业务的准确率。不能把合成案例和开发样本的通过率混成泛化指标。IANA 已经被我们查看并分析，一旦用它改规则，就应转入开发组，再采集新的验证网页。不要在同一验证样本上反复调参后仍称其未见样本。

每条记录包含快照 SHA256。HTML 改变后，本次结果与原标注可能不再可比；工具会报错并跳过该条评分，其他样本继续运行。文件缺失同样单独记为error，不算提取正确。

## 3. 标准答案先定义口径

先看原始 HTML，确认正文范围，再标注期望结果；不要直接复制提取器的输出作为标准答案。

本轮口径：标题单独存放；正文保留段落、列表以及文章内的子标题和编辑性参考文献；排除站点导航、面包屑、侧栏、页脚和修订日期元数据。期望的 heading 块即使当前提取器不支持，也应保留在答案里，不能为了通过而删除。

中文答案来自已检查的 section，标注了16块；IANA 答案来自 article 中 help-article 内容，含2段文字、Further Reading子标题和3条参考链接。Python介绍页的原有人工段落标注补充了paragraph类型。list_lab是手写实验，不是网站泛化案例。

## 4. 读出一个真实失败

当前报告中IANA结果：

- 标题正确；
- body_exact 为True（注意它只检查旧p字段）；
- blocks_exact 为False；
- 多提：Instructions and Guides；
- 漏提：Further Reading。

打开 `samples/iana_example_domains.html`，搜索这两句话。观察前者的祖先列表class和后者的标签。然后在提取器中找出两个对应原因：哪些导航没有被噪声规则覆盖，哪些正文标签没有被结构遍历覆盖。

也可以直接输出当前正文，和源码对照：

```powershell
.\run.cmd extract samples/iana_example_domains.html --output outputs/iana.baseline.json --text-output outputs/iana.baseline.md
```

本轮先不改规则或标准答案，也不要覆盖其他网页快照。

## 5. 指标怎样解释

block_text_precision = 匹配的块文字数 / 预测块数；block_text_recall = 匹配的块文字数 / 标准块数。按文字完全相等且次数交集匹配，同一句重复预测不能重复赚取召回。当前IANA两者都是5/6：预测6块，标准6块，匹配5块。

块文本指标不检查顺序或类型，微小空白差异也会影响匹配；定位问题后需要回看HTML和JSON。blocks_exact 则严格比较整段块序列，包括文字、顺序、kind和列表元数据。子标题目前只要求heading类型，后续若要恢复h2/h3级别，需要扩展标注和输出协议。

旧 body_exact 与字符指标仍基于paragraphs，不包含无p列表或子标题，不要单独用它们评价全文。未提供blocks标注时结构指标为null，含义是未评分，不是通过。

## 6. 你这次的动手任务

1. 运行batch，打开Markdown报告。
2. 在IANA源码中定位多提/漏提两处。
3. 在JSON里找到预测的多提块，查看kind/list_type/ordinal。
4. 回复这两处源码的标签/属性，以及建议在哪个函数修改。

我们下一步据此实现小范围修复，再比较修复前后的逐页结果，而不是只追求一个汇总分数。
